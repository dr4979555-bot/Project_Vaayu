import pytest
from unittest.mock import AsyncMock, patch
from app.services.ingestion_worker import MeteorologicalIngestionWorker, PRIMARY_MET_STATIONS


def test_primary_stations_registry():
    """Verify primary Indian meteorological stations are registered with valid coordinates."""
    assert len(PRIMARY_MET_STATIONS) >= 15
    for st in PRIMARY_MET_STATIONS:
        assert "id" in st
        assert "name" in st
        assert -90.0 <= st["lat"] <= 90.0
        assert -180.0 <= st["lon"] <= 180.0


@pytest.mark.asyncio
async def test_ingest_single_station():
    """Verify ingestion of a single station into database session."""
    mock_session = AsyncMock()
    station = {"id": "TEST_001", "name": "TEST_STATION", "lat": 28.61, "lon": 77.21}

    mock_live_weather = {
        "temperature_c": 28.5,
        "humidity_pct": 65.0,
        "rainfall_mm": 0.0,
        "wind_speed_kmh": 12.0,
        "source": "Open-Meteo (ECMWF/GFS)",
    }

    with patch("app.services.realtime_weather.RealtimeWeatherService.fetch_realtime_weather", return_value=mock_live_weather):
        success = await MeteorologicalIngestionWorker.ingest_single_station(mock_session, station)
        assert success is True
        mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_admin_ingest_endpoint(async_client):
    """Verify POST /api/v1/admin/ingest-now triggers manual ingestion cycle."""
    mock_cycle_result = {
        "status": "completed",
        "stations_attempted": 18,
        "succeeded": 18,
        "failed": 0,
        "timestamp": "2026-09-20T12:00:00Z",
    }

    with patch("app.services.ingestion_worker.MeteorologicalIngestionWorker.run_ingestion_cycle", return_value=mock_cycle_result):
        resp = await async_client.post("/api/v1/admin/ingest-now")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["succeeded"] == 18
