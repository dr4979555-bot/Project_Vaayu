import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_alert_ingest_signature_rejected(async_client):
    """Test POST /api/v1/alerts/ingest rejects alerts with forged signatures."""
    payload = {
        "sender": "FORGED_SENDER",
        "sent_at": "2026-09-20T12:00:00Z",
        "status": "Actual",
        "severity": "Severe",
        "event_category": "Flood",
        "headline": "Fake Flood Alert",
        "description": "Fake panic creation.",
        "instruction": "Evacuate.",
        "polygon_coordinates": [
            [85.10, 25.55],
            [85.20, 25.55],
            [85.20, 25.65],
            [85.10, 25.65],
            [85.10, 25.55],
        ],
        "signature_ecdsa": "dGhpcyBpcyBhIGZha2Ugc2lnbmF0dXJl==",
    }

    resp = await async_client.post("/api/v1/alerts/ingest", json=payload)
    assert resp.status_code == 403
    assert "Cryptographic verification failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_alert_ingest_out_of_bounds_coords(async_client):
    """Test POST /api/v1/alerts/ingest rejects out-of-bounds coordinates."""
    payload = {
        "sender": "IMD_HQ_NEW_DELHI",
        "sent_at": "2026-09-20T12:00:00Z",
        "status": "Actual",
        "severity": "Severe",
        "event_category": "Flood",
        "headline": "Flood Alert",
        "description": "Waterlogging.",
        "instruction": "Avoid low-lying areas.",
        "polygon_coordinates": [
            [85.10, 125.55],  # Invalid latitude > 90
            [85.20, 25.55],
            [85.20, 25.65],
            [85.10, 25.65],
            [85.10, 125.55],
        ],
        "signature_ecdsa": "c2lnbmF0dXJl",
    }

    resp = await async_client.post("/api/v1/alerts/ingest", json=payload)
    assert resp.status_code == 400
    assert "Latitude" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_active_alerts(async_client):
    """Test GET /api/v1/alerts/active returns alert list within radius."""
    resp = await async_client.get(
        "/api/v1/alerts/active",
        params={"latitude": 25.5941, "longitude": 85.1376, "radius_km": 50.0},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
