import os
from datetime import datetime
from typing import List

# pyrefly: ignore [missing-import]
from fastapi import Depends, FastAPI, Form, HTTPException, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import HTMLResponse, RedirectResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi.templating import Jinja2Templates
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.database import (
    get_db,
    init_db,
    get_active_node,
    replicate_item,
    load_node_status,
    save_node_status,
    NODES_INFO,
    SessionLocals,
    sync_node_data,
    mine_block,
)
from app.models import Block, Batch, SensorReading, TraceEvent
from app.schemas import SensorDataIn
from app.services.hash_service import (
    make_event_hash,
    make_sensor_hash,
    verify_sensor_reading,
    verify_trace_event,
)
from app.services.qr_service import generate_qr
from app.services.sensor_service import calculate_status, status_label

app = FastAPI(title="Vegetable Traceability IoT API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def get_base_url(request: Request) -> str:
    configured = os.getenv("APP_BASE_URL")
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def add_trace_event(
    db: Session,
    batch_id: str,
    event_type: str,
    description: str,
    actor: str,
    location: str,
    event_time: str | None = None,
) -> TraceEvent:
    event_time = event_time or now_iso()
    
    # Get previous event to link them in a hash chain
    last_event = (
        db.query(TraceEvent)
        .filter(TraceEvent.batch_id == batch_id)
        .order_by(TraceEvent.id.desc())
        .first()
    )
    previous_hash = last_event.event_hash if last_event else "0" * 64

    payload = {
        "batch_id": batch_id,
        "event_type": event_type,
        "description": description,
        "actor": actor,
        "location": location,
        "event_time": event_time,
        "previous_hash": previous_hash,
    }
    event = TraceEvent(**payload, event_hash=make_event_hash(payload))
    db.add(event)
    db.commit()
    db.refresh(event)

    # Đào khối (Proof of Work) cho sự kiện mới này
    import json
    block = mine_block(
        db_session=db,
        data_type="event",
        data_id=str(event.id),
        data_content=json.dumps({
            "batch_id": event.batch_id,
            "event_type": event.event_type,
            "description": event.description,
            "actor": event.actor,
            "location": event.location,
            "event_time": event.event_time,
            "previous_hash": event.previous_hash,
            "event_hash": event.event_hash
        })
    )
    event.block_index = block.index
    db.commit()
    db.refresh(event)
    replicate_item(event)  # Sao chép bản ghi đã có block_index sang các node online khác
    return event



@app.on_event("startup")
def on_startup():
    os.makedirs("app/static/qr", exist_ok=True)
    init_db()


def get_network_status():
    status = load_node_status()
    active = get_active_node()
    
    result = []
    max_batches = 0
    max_events = 0
    max_readings = 0
    max_blocks = 0
    
    node_counts = {}
    for node in NODES_INFO.keys():
        session = SessionLocals[node]()
        try:
            from app.models import Block, Batch, TraceEvent, SensorReading
            b_cnt = session.query(Batch).count()
            e_cnt = session.query(TraceEvent).count()
            r_cnt = session.query(SensorReading).count()
            bl_cnt = session.query(Block).count()
            
            node_counts[node] = (b_cnt, e_cnt, r_cnt, bl_cnt)
            
            max_batches = max(max_batches, b_cnt)
            max_events = max(max_events, e_cnt)
            max_readings = max(max_readings, r_cnt)
            max_blocks = max(max_blocks, bl_cnt)
        except Exception:
            node_counts[node] = (0, 0, 0, 0)
        finally:
            session.close()

    for node, info in NODES_INFO.items():
        is_online = status.get(node, True)
        b_cnt, e_cnt, r_cnt, bl_cnt = node_counts[node]
        
        # Xác định trạng thái đồng bộ
        if not is_online:
            sync_text = "Ngoại tuyến"
            can_sync = False
        else:
            if b_cnt == max_batches and e_cnt == max_events and r_cnt == max_readings and bl_cnt == max_blocks:
                sync_text = "Đã đồng bộ"
                can_sync = False
            else:
                sync_text = "Cần đồng bộ"
                can_sync = True
                
        result.append({
            "node_id": node,
            "name": info["name"],
            "online": is_online,
            "batches_count": b_cnt,
            "events_count": e_cnt,
            "readings_count": r_cnt,
            "blocks_count": bl_cnt,
            "sync_status": sync_text,
            "can_sync": can_sync,
            "is_active_reader": (node == active)
        })
        
    return {
        "active_reader": active,
        "nodes": result
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    active = get_active_node()
    net_status = get_network_status()
    
    if not active:
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "batches": [],
                "all_offline": True,
                "network_status": net_status,
                "active_node_info": None,
            },
        )
        
    batches: List[Batch] = db.query(Batch).order_by(Batch.id.desc()).all()
    active_node_info = NODES_INFO.get(active)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "batches": batches,
            "all_offline": False,
            "network_status": net_status,
            "active_node_info": active_node_info,
        },
    )


@app.get("/batches/new", response_class=HTMLResponse)
def new_batch_page(request: Request):
    active = get_active_node()
    active_node_info = NODES_INFO.get(active) if active else None
    return templates.TemplateResponse(
        "new_batch.html",
        {"request": request, "active_node_info": active_node_info}
    )


@app.post("/batches")
def create_batch(
    request: Request,
    batch_id: str = Form(...),
    product_name: str = Form(...),
    farm_name: str = Form(...),
    farm_location: str = Form(...),
    planting_date: str = Form(...),
    harvest_date: str = Form(...),
    db: Session = Depends(get_db),
):
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Mạng lưới ngoại tuyến, không thể ghi dữ liệu.")

    existing = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mã lô sản phẩm đã tồn tại")

    qr_path = generate_qr(batch_id=batch_id, base_url=get_base_url(request))
    batch = Batch(
        batch_id=batch_id,
        product_name=product_name,
        farm_name=farm_name,
        farm_location=farm_location,
        planting_date=planting_date,
        harvest_date=harvest_date,
        qr_path=qr_path,
        created_at=now_iso(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Đào khối (Proof of Work) cho lô sản phẩm mới này
    import json
    block = mine_block(
        db_session=db,
        data_type="batch",
        data_id=batch.batch_id,
        data_content=json.dumps({
            "batch_id": batch.batch_id,
            "product_name": batch.product_name,
            "farm_name": batch.farm_name,
            "farm_location": batch.farm_location,
            "planting_date": batch.planting_date,
            "harvest_date": batch.harvest_date
        })
    )
    batch.block_index = block.index
    db.commit()
    db.refresh(batch)
    replicate_item(batch)  # Sao chép dữ liệu lô đã có block_index sang các node online khác

    add_trace_event(
        db=db,
        batch_id=batch_id,
        event_type="CREATE_BATCH",
        description=f"Tạo lô {product_name} với mã {batch_id}",
        actor="Farm/Admin",
        location=farm_location,
    )

    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


@app.post("/api/network/toggle-node")
def toggle_node(node_id: str = Form(...)):
    if node_id not in NODES_INFO:
        raise HTTPException(status_code=400, detail="Mã node không hợp lệ")
    status = load_node_status()
    status[node_id] = not status.get(node_id, True)
    save_node_status(status)
    return RedirectResponse(url="/", status_code=303)


@app.post("/api/network/sync-node")
def sync_node(node_id: str = Form(...)):
    if node_id not in NODES_INFO:
        raise HTTPException(status_code=400, detail="Mã node không hợp lệ")
    res = sync_node_data(node_id)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return RedirectResponse(url="/", status_code=303)


@app.get("/batches/{batch_id}", response_class=HTMLResponse)
def batch_detail(batch_id: str, request: Request, db: Session = Depends(get_db)):
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Tất cả các node trong mạng đều ngoại tuyến (offline)!")

    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Không tìm thấy lô hàng")

    readings = (
        db.query(SensorReading)
        .filter(SensorReading.batch_id == batch_id)
        .order_by(SensorReading.id.desc())
        .limit(50)
        .all()
    )
    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.batch_id == batch_id)
        .order_by(TraceEvent.id.asc())
        .all()
    )
    active_node_info = NODES_INFO.get(active)
    return templates.TemplateResponse(
        "batch_detail.html",
        {
            "request": request,
            "batch": batch,
            "readings": readings,
            "events": events,
            "base_url": get_base_url(request),
            "status_label": status_label,
            "verify_sensor": verify_sensor_reading,
            "verify_event": verify_trace_event,
            "active_node_info": active_node_info,
        },
    )


@app.post("/api/iot/sensor-data")
def receive_sensor_data(data: SensorDataIn, db: Session = Depends(get_db)):
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Tất cả các node trong mạng đều ngoại tuyến (offline)!")

    batch = db.query(Batch).filter(Batch.batch_id == data.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Unknown batch_id")

    created_at = now_iso()
    status = calculate_status(
        temperature=data.temperature,
        air_humidity=data.air_humidity,
        soil_moisture=data.soil_moisture,
    )
    payload = {
        "batch_id": data.batch_id,
        "device_id": data.device_id,
        "temperature": data.temperature,
        "air_humidity": data.air_humidity,
        "soil_moisture": data.soil_moisture,
        "light": data.light,
        "status": status,
        "created_at": created_at,
    }
    reading = SensorReading(**payload, data_hash=make_sensor_hash(payload))
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Đào khối (Proof of Work) cho dữ liệu cảm biến mới
    import json
    block = mine_block(
        db_session=db,
        data_type="sensor",
        data_id=str(reading.id),
        data_content=json.dumps({
            "batch_id": reading.batch_id,
            "device_id": reading.device_id,
            "temperature": reading.temperature,
            "air_humidity": reading.air_humidity,
            "soil_moisture": reading.soil_moisture,
            "light": reading.light,
            "status": reading.status,
            "created_at": reading.created_at,
            "data_hash": reading.data_hash
        })
    )
    reading.block_index = block.index
    db.commit()
    db.refresh(reading)
    replicate_item(reading)  # Sao chép dữ liệu cảm biến đã có block_index sang các node online khác

    return {
        "message": "Sensor data received successfully",
        "reading_id": reading.id,
        "batch_id": reading.batch_id,
        "status": reading.status,
        "status_label": status_label(reading.status),
        "hash": reading.data_hash,
        "created_at": reading.created_at,
    }


@app.get("/api/batches/{batch_id}/sensor-data")
def get_sensor_data(batch_id: str, db: Session = Depends(get_db)):
    readings = (
        db.query(SensorReading)
        .filter(SensorReading.batch_id == batch_id)
        .order_by(SensorReading.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "batch_id": r.batch_id,
            "device_id": r.device_id,
            "temperature": r.temperature,
            "air_humidity": r.air_humidity,
            "soil_moisture": r.soil_moisture,
            "light": r.light,
            "status": r.status,
            "status_label": status_label(r.status),
            "created_at": r.created_at,
            "is_valid": verify_sensor_reading(r),
        }
        for r in readings
    ]


@app.post("/batches/{batch_id}/events")
def create_event(
    batch_id: str,
    event_type: str = Form(...),
    description: str = Form(...),
    actor: str = Form(...),
    location: str = Form(...),
    event_time: str = Form(""),
    db: Session = Depends(get_db),
):
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Tất cả các node trong mạng đều ngoại tuyến (offline)!")

    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    add_trace_event(
        db=db,
        batch_id=batch_id,
        event_type=event_type,
        description=description,
        actor=actor,
        location=location,
        event_time=event_time or None,
    )
    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


@app.get("/trace/{batch_id}", response_class=HTMLResponse)
def public_trace_page(batch_id: str, request: Request, db: Session = Depends(get_db)):
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Hệ thống lưu trữ phân tán đang ngoại tuyến!")

    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    readings = (
        db.query(SensorReading)
        .filter(SensorReading.batch_id == batch_id)
        .order_by(SensorReading.id.asc())
        .all()
    )
    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.batch_id == batch_id)
        .order_by(TraceEvent.id.asc())
        .all()
    )

    all_sensor_valid = all(verify_sensor_reading(r) for r in readings) if readings else True
    all_event_valid = all(verify_trace_event(e) for e in events) if events else True

    avg_temperature = round(sum(r.temperature for r in readings) / len(readings), 2) if readings else None
    avg_air_humidity = round(sum(r.air_humidity for r in readings) / len(readings), 2) if readings else None
    avg_soil_moisture = round(sum(r.soil_moisture for r in readings) / len(readings), 2) if readings else None

    active_node_info = NODES_INFO.get(active)

    return templates.TemplateResponse(
        "trace.html",
        {
            "request": request,
            "batch": batch,
            "events": events,
            "readings": readings[-20:],
            "avg_temperature": avg_temperature,
            "avg_air_humidity": avg_air_humidity,
            "avg_soil_moisture": avg_soil_moisture,
            "is_verified": all_sensor_valid and all_event_valid,
            "status_label": status_label,
            "verify_sensor": verify_sensor_reading,
            "verify_event": verify_trace_event,
            "active_node_info": active_node_info,
        },
    )


@app.post("/demo/tamper-reading/{reading_id}")
def tamper_reading(reading_id: int, db: Session = Depends(get_db)):
    """Demo only: change data without updating hash to prove tamper detection."""
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Hệ thống ngoại tuyến")
    reading = db.query(SensorReading).filter(SensorReading.id == reading_id).first()
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    reading.temperature = reading.temperature + 10
    db.commit()
    return RedirectResponse(url=f"/batches/{reading.batch_id}", status_code=303)


@app.post("/demo/seed")
def run_demo_seed():
    from app.seed_data import seed_all
    try:
        seed_all()
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi seeding: {str(e)}")


@app.get("/blockchain", response_class=HTMLResponse)
def blockchain_explorer_page(request: Request, db: Session = Depends(get_db)):
    active = get_active_node()
    if not active:
        return templates.TemplateResponse(
            "blockchain.html",
            {
                "request": request,
                "blocks": [],
                "all_offline": True,
                "active_node_info": None,
            },
        )
    
    blocks = db.query(Block).order_by(Block.index.desc()).all()
    active_node_info = NODES_INFO.get(active)
    
    # Parse transaction content JSON to display nicely on UI
    import json
    parsed_blocks = []
    for b in blocks:
        try:
            parsed_content = json.loads(b.data_content)
        except Exception:
            parsed_content = b.data_content
        parsed_blocks.append({
            "index": b.index,
            "timestamp": b.timestamp,
            "previous_hash": b.previous_hash,
            "nonce": b.nonce,
            "hash": b.hash,
            "difficulty": b.difficulty,
            "data_type": b.data_type,
            "data_id": b.data_id,
            "data_content": parsed_content
        })
        
    return templates.TemplateResponse(
        "blockchain.html",
        {
            "request": request,
            "blocks": parsed_blocks,
            "all_offline": False,
            "active_node_info": active_node_info,
        },
    )


@app.get("/api/blockchain/blocks")
def get_raw_blocks(db: Session = Depends(get_db)):
    active = get_active_node()
    if not active:
        raise HTTPException(status_code=503, detail="Offline")
    blocks = db.query(Block).order_by(Block.index.asc()).all()
    return [
        {
            "index": b.index,
            "timestamp": b.timestamp,
            "previous_hash": b.previous_hash,
            "nonce": b.nonce,
            "hash": b.hash,
            "difficulty": b.difficulty,
            "data_type": b.data_type,
            "data_id": b.data_id,
            "data_content": b.data_content
        }
        for b in blocks
    ]


