"""
MAP gas recommendation (lookup, since these are standardized in food-packaging
literature — not something to guess with ML) + QR traceability tag generation.
"""
import json
import qrcode
import io
import base64


def get_map_gas(commodity: dict):
    if not commodity or commodity.get("respiration_class") == "none":
        # non-respiring product: still may benefit from MAP (e.g. CO2 for shelf life)
        return commodity.get("map_gas") if commodity else None
    return commodity.get("map_gas")


def generate_qr_base64(payload: dict) -> str:
    """Encodes a recommendation summary into a QR code, returns base64 PNG."""
    img = qrcode.make(json.dumps(payload))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
