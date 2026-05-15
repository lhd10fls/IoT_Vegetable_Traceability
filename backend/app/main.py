import os
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import Batch, SensorReading, TraceEvent
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
    payload = {
        "batch_id": batch_id,
        "event_type": event_type,
        "description": description,
        "actor": actor,
        "location": location,
        "event_time": event_time,
    }
    event = TraceEvent(**payload, event_hash=make_event_hash(payload))
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.on_event("startup")
def on_startup():
    os.makedirs("app/static/qr", exist_ok=True)
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    batches: List[Batch] = db.query(Batch).order_by(Batch.id.desc()).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "batches": batches},
    )


@app.get("/batches/new", response_class=HTMLResponse)
def new_batch_page(request: Request):
    return templates.TemplateResponse("new_batch.html", {"request": request})


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
    existing = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Batch ID already exists")

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

    add_trace_event(
        db=db,
        batch_id=batch_id,
        event_type="CREATE_BATCH",
        description=f"Tạo lô {product_name} với mã {batch_id}",
        actor="Farm/Admin",
        location=farm_location,
    )

    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)


@app.get("/batches/{batch_id}", response_class=HTMLResponse)
def batch_detail(batch_id: str, request: Request, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

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
        },
    )


@app.post("/api/iot/sensor-data")
def receive_sensor_data(data: SensorDataIn, db: Session = Depends(get_db)):
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
        },
    )


@app.post("/demo/tamper-reading/{reading_id}")
def tamper_reading(reading_id: int, db: Session = Depends(get_db)):
    """Demo only: change data without updating hash to prove tamper detection."""
    reading = db.query(SensorReading).filter(SensorReading.id == reading_id).first()
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    reading.temperature = reading.temperature + 10
    db.commit()
    return RedirectResponse(url=f"/batches/{reading.batch_id}", status_code=303)


@app.post("/demo/seed")
def seed_demo(request: Request, db: Session = Depends(get_db)):
    batch_id = "VEG-001"
    batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not batch:
        qr_path = generate_qr(batch_id=batch_id, base_url=get_base_url(request))
        batch = Batch(
            batch_id=batch_id,
            product_name="Rau cải xanh",
            farm_name="HUST Smart Farm",
            farm_location="Hà Nội",
            planting_date="2026-05-01",
            harvest_date="2026-05-15",
            qr_path=qr_path,
            created_at=now_iso(),
        )
        db.add(batch)
        db.commit()
        add_trace_event(db, batch_id, "GIEO_TRONG", "Gieo trồng rau cải xanh", "Nông trại", "Hà Nội")
        add_trace_event(db, batch_id, "THU_HOACH", "Thu hoạch và phân loại rau", "Nông trại", "Hà Nội")
        add_trace_event(db, batch_id, "DONG_GOI", "Đóng gói lô rau", "Nhân viên đóng gói", "Hà Nội")
    return RedirectResponse(url=f"/batches/{batch_id}", status_code=303)
