"""
Alert signing script — standalone CLI tool.
Run directly: python -m app.services.alerts

This module MUST NOT be imported as a package at runtime — it contains
top-level code that loads a private key and fires an HTTP request.
Guard with __main__ prevents execution on accidental import.
"""

if __name__ == "__main__":
    import base64
    import requests
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from app.services.alert_verifier import AlertVerifier

    # 1. Load private key
    with open("keys/alert_private.pem", "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)

    # 2. Define Patna alert bounding polygon [lon, lat]
    coords = [
        [85.10, 25.55],
        [85.20, 25.55],
        [85.20, 25.65],
        [85.10, 25.65],
        [85.10, 25.55],
    ]
    wkt_points = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    polygon_wkt = f"POLYGON(({wkt_points}))"

    sender = "IMD_HQ_NEW_DELHI"
    sent_at = "2026-09-20T11:00:00Z"
    severity = "Severe"
    event_category = "Urban Flood"
    headline = "Urban Waterlogging & Flash Flood Advisory for Patna Central"

    # 3. Canonicalize & Sign
    canonical_bytes = AlertVerifier.canonicalize_alert(
        sender=sender,
        sent_at=sent_at,
        severity=severity,
        event_category=event_category,
        headline=headline,
        polygon_wkt=polygon_wkt,
    )

    signature = private_key.sign(canonical_bytes, ec.ECDSA(hashes.SHA256()))
    signature_b64 = base64.b64encode(signature).decode("utf-8")

    payload = {
        "sender": sender,
        "sent_at": sent_at,
        "status": "Actual",
        "severity": severity,
        "event_category": event_category,
        "headline": headline,
        "description": "Intense convection leading to localized waterlogging exceeding 50mm/hr.",
        "instruction": "Avoid underpasses and low-lying road networks.",
        "polygon_coordinates": coords,
        "signature_ecdsa": signature_b64,
    }

    print("Transmitting Signed CAP Alert to http://127.0.0.1:8000/api/v1/alerts/ingest...")
    resp = requests.post("http://127.0.0.1:8000/api/v1/alerts/ingest", json=payload)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")