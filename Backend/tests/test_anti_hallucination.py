import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.schemas import NowcastResponse
from app.services.agent_service import WeatherAgent


@pytest.fixture
def sample_observation():
    return NowcastResponse(
        latitude=25.5941,
        longitude=85.1376,
        station_name="PATNA_AIRPORT",
        distance_km=0.0,
        temperature_c=25.0,
        apparent_temperature_c=26.0,
        humidity_pct=60.0,
        rainfall_mm=0.0,
        wind_speed_kmh=10.0,
        weather_condition="Clear sky",
        source="IMD_AWS",
        timestamp="2026-09-20T12:00:00Z",
    )


@pytest.mark.asyncio
async def test_hallucination_triggers_deterministic_fallback(sample_observation):
    """
    Verify that when the LLM hallucinates an unverified temperature (e.g. 45°C instead of 25°C),
    the anti-hallucination guardrail REJECTS the output and returns a deterministic,
    100% verified ground-truth template.
    """
    mock_db = AsyncMock()

    # Mock Groq to return a hallucinated temperature
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="The current temperature in Patna is 45°C with severe heat."))
    ]

    with patch("app.services.weather_engine.WeatherEngine.get_nearest_station_observation", return_value=sample_observation), \
         patch("app.services.cache_service.CacheService.get", return_value=None), \
         patch("app.services.agent_service.groq_client.chat.completions.create", new_callable=AsyncMock, return_value=mock_completion):

        response = await WeatherAgent.process_query(
            db=mock_db,
            query="What is the temperature?",
            latitude=25.5941,
            longitude=85.1376,
        )

        # Audit must have failed
        assert response.hallucination_audit_passed is False

        # Response must NOT contain the hallucinated 45°C!
        assert "45°C" not in response.response

        # Response must contain the verified ground truth: 25.0°C
        assert "25.0°C" in response.response or "25°C" in response.response
        assert "PATNA_AIRPORT" in response.response
        assert "Verified Ground Truth" in response.response


@pytest.mark.asyncio
async def test_hallucinated_rainfall_triggers_fallback(sample_observation):
    """
    Verify that claiming rainfall when ground truth is 0.0 mm triggers fallback.
    """
    mock_db = AsyncMock()

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="It is raining heavily with 35.0 mm of rainfall in Patna right now at 25°C."))
    ]

    with patch("app.services.weather_engine.WeatherEngine.get_nearest_station_observation", return_value=sample_observation), \
         patch("app.services.cache_service.CacheService.get", return_value=None), \
         patch("app.services.agent_service.groq_client.chat.completions.create", new_callable=AsyncMock, return_value=mock_completion):

        response = await WeatherAgent.process_query(
            db=mock_db,
            query="Is it raining?",
            latitude=25.5941,
            longitude=85.1376,
        )

        assert response.hallucination_audit_passed is False
        assert "35.0 mm" not in response.response
        assert "0.0 mm" in response.response


@pytest.mark.asyncio
async def test_verified_response_passes_audit(sample_observation):
    """
    Verify that an accurate response preserving ground-truth values passes the audit.
    """
    mock_db = AsyncMock()

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="The current temperature at Patna Airport is 25°C with 60% humidity and no rain."))
    ]

    with patch("app.services.weather_engine.WeatherEngine.get_nearest_station_observation", return_value=sample_observation), \
         patch("app.services.cache_service.CacheService.get", return_value=None), \
         patch("app.services.agent_service.groq_client.chat.completions.create", new_callable=AsyncMock, return_value=mock_completion):

        response = await WeatherAgent.process_query(
            db=mock_db,
            query="What is the weather?",
            latitude=25.5941,
            longitude=85.1376,
        )

        assert response.hallucination_audit_passed is True
        assert "25°C" in response.response
