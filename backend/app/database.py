import os
import json
import hashlib
import time
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Network Node Metadata
NODES_INFO = {
    "node_a": {"name": "Node A (Farm - Đông Anh)", "db_url": "sqlite:///./node_a.db"},
    "node_b": {"name": "Node B (Logistics - Long Biên)", "db_url": "sqlite:///./node_b.db"},
    "node_c": {"name": "Node C (Retailer - Cầu Giấy)", "db_url": "sqlite:///./node_c.db"},
}

STATUS_FILE = "node_status.json"

def load_node_status() -> dict:
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default: all nodes are online
    return {"node_a": True, "node_b": True, "node_c": True}

def save_node_status(status: dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f)

# Create engines & sessionmakers for all 3 nodes
engines = {
    node: create_engine(info["db_url"], connect_args={"check_same_thread": False})
    for node, info in NODES_INFO.items()
}

SessionLocals = {
    node: sessionmaker(autocommit=False, autoflush=False, bind=engines[node])
    for node in NODES_INFO.keys()
}

def init_db():
    from app import models  # noqa: F401
    for engine in engines.values():
        Base.metadata.create_all(bind=engine)

def get_active_node() -> str | None:
    """Returns the first online node. Returns None if all offline."""
    status = load_node_status()
    for node in ["node_a", "node_b", "node_c"]:
        if status.get(node, True):
            return node
    return None

def get_db():
    active_node = get_active_node()
    # Fallback to node_a if all offline (routes will handle actual offline errors)
    db_node = active_node or "node_a"
    db = SessionLocals[db_node]()
    try:
        yield db
    finally:
        db.close()

def proof_of_work(block_data: dict, difficulty: int = 4) -> tuple[int, str, float]:
    """
    Proof of Work algorithm.
    Finds a nonce such that the SHA-256 hash of the block starts with `difficulty` zeros.
    """
    nonce = 0
    target = "0" * difficulty
    start_time = time.time()
    
    # Stable serialization
    serialized_data = {k: str(v) for k, v in block_data.items()}
    base_str = json.dumps(serialized_data, sort_keys=True)
    
    while True:
        raw = f"{base_str}|{nonce}"
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if h.startswith(target):
            duration = time.time() - start_time
            return nonce, h, duration
        nonce += 1

def mine_block(db_session, data_type: str, data_id: str, data_content: str, difficulty: int = 4):
    """
    Creates and mines a new Block, saving it to the active node DB
    and replicating it to other online nodes.
    """
    from app.models import Block
    
    # Get latest block to link the chain
    last_block = db_session.query(Block).order_by(Block.index.desc()).first()
    
    index = last_block.index + 1 if last_block else 0
    previous_hash = last_block.hash if last_block else "0" * 64
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    
    block_payload = {
        "index": index,
        "timestamp": timestamp,
        "previous_hash": previous_hash,
        "difficulty": difficulty,
        "data_type": data_type,
        "data_id": data_id,
        "data_content": data_content
    }
    
    nonce, block_hash, duration = proof_of_work(block_payload, difficulty)
    
    # Print mining log
    print(f"⛏️ [BLOCK MINED] Block #{index} ({data_type}:{data_id}) in {duration:.4f}s | Nonce: {nonce} | Hash: {block_hash}")
    
    block = Block(
        index=index,
        timestamp=timestamp,
        previous_hash=previous_hash,
        nonce=nonce,
        hash=block_hash,
        difficulty=difficulty,
        data_type=data_type,
        data_id=data_id,
        data_content=data_content
    )
    
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)
    
    # Replicate Block to other online nodes
    replicate_item(block)
    
    return block

def replicate_item(item):
    """
    Replicates a model instance to all other ONLINE nodes.
    `item` is an already committed instance from the active node.
    """
    active_node = get_active_node()
    if not active_node:
        return
        
    model_class = type(item)
    data = {c.name: getattr(item, c.name) for c in item.__table__.columns}
    
    status = load_node_status()
    
    for node, is_online in status.items():
        if node == active_node:
            continue
        if is_online:
            session = SessionLocals[node]()
            try:
                # Check if it already exists (Batch has batch_id, Block has index, others have id)
                if model_class.__name__ == "Batch":
                    existing = session.query(model_class).filter(model_class.batch_id == item.batch_id).first()
                elif model_class.__name__ == "Block":
                    existing = session.query(model_class).filter(model_class.index == item.index).first()
                else:
                    existing = session.query(model_class).filter(model_class.id == item.id).first()
                
                if not existing:
                    new_item = model_class(**data)
                    session.add(new_item)
                    session.commit()
            except Exception as e:
                print(f"Error replicating to {node}: {e}")
                session.rollback()
            finally:
                session.close()

def sync_node_data(target_node: str) -> dict:
    """
    Synchronizes target_node with the current active online node.
    """
    active_node = get_active_node()
    if not active_node or active_node == target_node:
        return {"status": "error", "message": "Không tìm thấy node nguồn hoạt động hoặc trùng node đích"}
        
    source_session = SessionLocals[active_node]()
    target_session = SessionLocals[target_node]()
    
    try:
        from app.models import Block, Batch, SensorReading, TraceEvent
        
        # 1. Sync Blocks first to preserve the cryptographic chain sequence
        source_blocks = source_session.query(Block).order_by(Block.index.asc()).all()
        for b in source_blocks:
            existing = target_session.query(Block).filter(Block.index == b.index).first()
            if not existing:
                b_data = {c.name: getattr(b, c.name) for c in b.__table__.columns}
                target_session.add(Block(**b_data))
        target_session.commit()
        
        # 2. Sync Batches
        source_batches = source_session.query(Batch).all()
        for b in source_batches:
            existing = target_session.query(Batch).filter(Batch.batch_id == b.batch_id).first()
            if not existing:
                b_data = {c.name: getattr(b, c.name) for c in b.__table__.columns}
                target_session.add(Batch(**b_data))
        target_session.commit()
        
        # 3. Sync TraceEvents
        source_events = source_session.query(TraceEvent).order_by(TraceEvent.id.asc()).all()
        for e in source_events:
            existing = target_session.query(TraceEvent).filter(TraceEvent.id == e.id).first()
            if not existing:
                e_data = {c.name: getattr(e, c.name) for c in e.__table__.columns}
                target_session.add(TraceEvent(**e_data))
        target_session.commit()
        
        # 4. Sync SensorReadings
        source_readings = source_session.query(SensorReading).order_by(SensorReading.id.asc()).all()
        for r in source_readings:
            existing = target_session.query(SensorReading).filter(SensorReading.id == r.id).first()
            if not existing:
                r_data = {c.name: getattr(r, c.name) for c in r.__table__.columns}
                target_session.add(SensorReading(**r_data))
        target_session.commit()
        
        return {"status": "success", "message": f"Node {target_node} đã đồng bộ thành công từ {active_node}"}
    except Exception as e:
        target_session.rollback()
        return {"status": "error", "message": f"Lỗi đồng bộ: {str(e)}"}
    finally:
        source_session.close()
        target_session.close()
