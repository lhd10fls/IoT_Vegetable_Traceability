"""
regen_qr.py
===========
Tái tạo QR code cho tất cả lô sản phẩm với base URL mới.
Không xóa dữ liệu sensor/events, chỉ cập nhật file QR + qr_path trong DB.

Cách dùng:
    python regen_qr.py                        # dùng APP_BASE_URL hoặc localhost
    python regen_qr.py http://192.168.2.60:8000
    python regen_qr.py https://abc123.ngrok.io
"""

import os
import sys

# Phải chạy trước khi import app để DB path đúng
os.makedirs("app/static/qr", exist_ok=True)

from app.database import SessionLocals, init_db, get_active_node, replicate_item
from app.models import Batch
from app.services.qr_service import generate_qr


def main():
    # Ưu tiên: argument > env var > localhost
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip("/")
    else:
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")

    print(f"\n{'='*55}")
    print(f"  QR REGENERATOR")
    print(f"  Base URL: {base_url}")
    print(f"{'='*55}\n")

    init_db()
    active_node = get_active_node()
    if not active_node:
        print("  Loi: Khong co node database nao online de cap nhat QR!")
        return

    db = SessionLocals[active_node]()
    try:
        batches = db.query(Batch).order_by(Batch.id).all()
        if not batches:
            print("  Khong co batch nao trong DB. Hay chay seed_data.py truoc.")
            return

        for batch in batches:
            qr_path = generate_qr(batch_id=batch.batch_id, base_url=base_url)
            batch.qr_path = qr_path
            db.commit()
            replicate_item(batch) # Replicate updated qr_path to other online nodes
            trace_url = f"{base_url}/trace/{batch.batch_id}"
            print(f"  [{batch.batch_id}] {batch.product_name}")
            print(f"     QR path : {qr_path}")
            print(f"     QR link : {trace_url}")

        print(f"\n  Done! {len(batches)} QR da duoc cap nhat.")
        print(f"  Mo trinh duyet: {base_url}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
