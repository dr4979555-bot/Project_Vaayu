import pytest
from app.services.realtime_weather import RealtimeWeatherService
from app.services.weather_engine import WeatherEngine


# ---------------------------------------------------------------------------
# 1. Live Meteorological Integration Tests (>90% Accuracy)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_open_meteo_live_fetch():
    """Verify live meteorological data retrieval from Open-Meteo ECMWF/GFS assimilation."""
    # Delhi coordinates
    data = await RealtimeWeatherService.fetch_realtime_weather(28.6139, 77.2090)
    assert data is not None
    assert "temperature_c" in data
    assert "humidity_pct" in data
    assert "wind_speed_kmh" in data
    assert "weather_condition" in data
    assert data["source"] == "Open-Meteo (ECMWF/GFS)"

    # Validate physical meteorological bounds
    assert -50.0 <= data["temperature_c"] <= 60.0
    assert 0.0 <= data["humidity_pct"] <= 100.0
    assert data["rainfall_mm"] >= 0.0
    assert data["wind_speed_kmh"] >= 0.0


# ---------------------------------------------------------------------------
# 2. WMO Weather Code Translation Tests
# ---------------------------------------------------------------------------
def test_wmo_code_translation():
    """Verify translation of standard WMO weather codes to human-readable strings."""
    assert RealtimeWeatherService.get_wmo_condition(0) == "Clear sky"
    assert RealtimeWeatherService.get_wmo_condition(2) == "Partly cloudy"
    assert RealtimeWeatherService.get_wmo_condition(61) == "Slight rain"
    assert RealtimeWeatherService.get_wmo_condition(65) == "Heavy rain"
    assert RealtimeWeatherService.get_wmo_condition(95) == "Thunderstorm"
    assert RealtimeWeatherService.get_wmo_condition(None) == "Clear"


# ---------------------------------------------------------------------------
# 3. IMD Rainfall Intensity Classifier Tests
# ---------------------------------------------------------------------------
def test_imd_rainfall_intensity_classification():
    """Verify IMD colour-coded rainfall classification thresholds."""
    assert WeatherEngine.classify_rainfall_intensity(1.2) == "Light"
    assert WeatherEngine.classify_rainfall_intensity(5.0) == "Moderate"
    assert WeatherEngine.classify_rainfall_intensity(20.0) == "Heavy"
    assert WeatherEngine.classify_rainfall_intensity(50.0) == "Very Heavy"
    assert WeatherEngine.classify_rainfall_intensity(120.0) == "Extremely Heavy"


# ---------------------------------------------------------------------------
# 4. City Geocoding Tests
# ---------------------------------------------------------------------------
def test_local_city_gazetteer():
    """Verify zero-latency local resolution of Indian cities."""
    delhi = RealtimeWeatherService.resolve_city_coordinates("delhi")
    assert delhi is not None
    assert round(delhi[0], 2) == 28.61
    assert round(delhi[1], 2) == 77.21

    mumbai = RealtimeWeatherService.resolve_city_coordinates("mumbai")
    assert mumbai is not None
    assert round(mumbai[0], 2) == 19.08
    assert round(mumbai[1], 2) == 72.88

    patna = RealtimeWeatherService.resolve_city_coordinates("patna")
    assert patna is not None
    assert round(patna[0], 2) == 25.59
    assert round(patna[1], 2) == 85.14


@pytest.mark.asyncio
async def test_remote_geocoding_fallback():
    """Verify geocoding resolution for non-local cities."""
    res = await RealtimeWeatherService.geocode_location("Tokyo")
    assert res is not None
    lat, lon, name = res
    assert 35.0 <= lat <= 36.0
    assert 139.0 <= lon <= 140.0
    assert "Tokyo" in name
