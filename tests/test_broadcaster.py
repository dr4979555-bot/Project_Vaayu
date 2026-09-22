import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.alert_broadcaster import (
    AlertBroadcaster,
    _ray_casting_point_in_polygon,
    _haversine_km,
)


def test_haversine_distance():
    """Verify great-circle distance calculation."""
    # Distance between Delhi (28.6139, 77.2090) and Patna (25.5941, 85.1376) ~850 km
    dist = _haversine_km(28.6139, 77.2090, 25.5941, 85.1376)
    assert 800 <= dist <= 900


def test_point_in_polygon_ray_casting():
    """Verify point-in-polygon ray casting algorithm."""
    # Bounding box around Patna: [lon, lat]
    polygon = [
        [85.10, 25.55],
        [85.25, 25.55],
        [85.25, 25.65],
        [85.10, 25.65],
        [85.10, 25.55],
    ]

    # Point inside: Patna Airport (25.5941, 85.1376)
    assert _ray_casting_point_in_polygon(25.5941, 85.1376, polygon) is True

    # Point far outside: Delhi (28.6139, 77.2090)
    assert _ray_casting_point_in_polygon(28.6139, 77.2090, polygon) is False


def test_is_location_affected_with_buffer():
    """Verify hazard area evaluation with proximity buffer."""
    polygon = [
        [85.10, 25.55],
        [85.20, 25.55],
        [85.20, 25.65],
        [85.10, 25.65],
        [85.10, 25.55],
    ]

    # Inside polygon
    assert AlertBroadcaster.is_location_affected(25.60, 85.15, polygon) is True

    # Just outside polygon within 10km buffer
    assert AlertBroadcaster.is_location_affected(25.66, 85.21, polygon, buffer_km=10.0) is True

    # Far away (e.g. Mumbai)
    assert AlertBroadcaster.is_location_affected(19.0760, 72.8777, polygon, buffer_km=10.0) is False


@pytest.mark.asyncio
async def test_websocket_registration_and_broadcast():
    """Verify WebSocket client registration and targeted alert push."""
    mock_ws_affected = AsyncMock()
    mock_ws_unaffected = AsyncMock()

    # Register affected client in Patna
    await AlertBroadcaster.register_ws(mock_ws_affected, 25.5941, 85.1376)

    # Register unaffected client in Delhi
    await AlertBroadcaster.register_ws(mock_ws_unaffected, 28.6139, 77.2090)

    patna_polygon = [
        [85.10, 25.55],
        [85.25, 25.55],
        [85.25, 25.65],
        [85.10, 25.65],
        [85.10, 25.55],
    ]

    sample_alert = {
        "alert_id": "test-alert-123",
        "sender": "IMD_HQ",
        "severity": "Extreme",
        "event_category": "Urban Flood",
        "headline": "Flash Flood Warning for Patna",
        "description": "Torrential rainfall.",
        "instruction": "Evacuate low areas.",
        "sent_at": "2026-09-20T12:00:00Z",
    }

    # Broadcast alert
    notified = await AlertBroadcaster.broadcast_alert(sample_alert, patna_polygon)

    # Only affected client should be notified
    assert notified == 1
    mock_ws_affected.send_text.assert_called()
    # Unaffected client should NOT receive the alert
    # mock_ws_unaffected received connection_ack on register, but not the emergency alert
    call_args = [call.args[0] for call in mock_ws_unaffected.send_text.call_args_list]
    assert not any("EMERGENCY_ALERT" in str(arg) for arg in call_args)

    # Cleanup
    AlertBroadcaster.unregister_ws(mock_ws_affected)
    AlertBroadcaster.unregister_ws(mock_ws_unaffected)
