from pathlib import Path
import qrcode


def generate_qr(batch_id: str, base_url: str) -> str:
    """Generate QR code image for /trace/{batch_id}; return web path."""
    qr_dir = Path("app/static/qr")
    qr_dir.mkdir(parents=True, exist_ok=True)

    trace_url = f"{base_url.rstrip('/')}/trace/{batch_id}"
    img = qrcode.make(trace_url)
    file_name = f"{batch_id}.png"
    file_path = qr_dir / file_name
    img.save(file_path)

    return f"/static/qr/{file_name}"
