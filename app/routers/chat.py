import base64
import logging
import re
from app.services.multi_city_temperature_predictor import (
    TRAINED_LOCATIONS,
    predict_multi_city_next_hour_temperature,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.schemas import (
    ChatRequest,
    ChatResponse,
    NowcastResponse,
    RainImpactRequest,
    RainImpactResponse,
    SafeRouteRequest,
    SafeRouteResponse,
)
from app.services.weather_engine import WeatherEngine
from app.services.agent_service import WeatherAgent
from app.services.realtime_weather import RealtimeWeatherService
from app.services.voice_service import VoiceService
from fastapi import HTTPException
from app.services.analytics_service import get_monthly_analytics

logger = logging.getLogger("WeatherGPT.ChatRouter")
router = APIRouter()

_NEXT_HOUR_PATTERN = re.compile(
    r"\bnext\s*(?:1\s*)?hour\b"
    r"|\bnext\s*hr\b"
    r"|\bagle\s*(?:1\s*)?ghante\b",
    re.IGNORECASE,
)

_TEMPERATURE_PATTERN = re.compile(
    r"\btemperature\b"
    r"|\btemp\b"
    r"|\btapman\b",
    re.IGNORECASE,
)


def _extract_temperature_prediction_location(
    query: str,
) -> str | None:
    """
    Detect a trained model location from a natural-language query.
    Longer aliases are checked first, so 'New Delhi' is detected
    before 'Delhi'.
    """

    normalized_query = query.strip().lower()

    for alias in sorted(
        TRAINED_LOCATIONS.keys(),
        key=len,
        reverse=True,
    ):
        pattern = rf"\b{re.escape(alias)}\b"

        if re.search(pattern, normalized_query):
            return TRAINED_LOCATIONS[alias]

    return None


def _is_next_hour_temperature_query(
    query: str,
) -> bool:
    return bool(
        _NEXT_HOUR_PATTERN.search(query)
        and _TEMPERATURE_PATTERN.search(query)
    )

# ---------------------------------------------------------------------------
# GET /nowcast — Nearest station or real-time grid observation
# ---------------------------------------------------------------------------
@router.get(
    "/nowcast",
    response_model=NowcastResponse,
    summary="Real-time meteorological observation (>90% accuracy)",
)
@limiter.limit("60/minute")
async def get_nowcast(
    request: Request,
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Observer latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Observer longitude"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns verified real-time meteorological observation:
    1. Nearest operational IMD AWS station within radius (if available)
    2. Real-time ECMWF/GFS assimilated observation via Open-Meteo (>90-95% accuracy)
    """
    obs = await WeatherEngine.get_nearest_station_observation(
        db=db,
        latitude=latitude,
        longitude=longitude,
        enable_realtime_fallback=True,
    )
    if not obs:
        raise HTTPException(
            status_code=404,
            detail="No operational weather observation station or real-time data available for coordinates.",
        )
    return obs

# ---------------------------------------------------------------------------
# GET /rain-prediction — Hourly rain probability and rainfall outlook
# ---------------------------------------------------------------------------
@router.get(
    "/rain-prediction",
    summary="Hourly rain prediction and rainfall outlook",
)
@limiter.limit("30/minute")
async def get_rain_prediction(
    request: Request,
    latitude: float = Query(
        ...,
        ge=-90.0,
        le=90.0,
        description="Observer latitude",
    ),
    longitude: float = Query(
        ...,
        ge=-180.0,
        le=180.0,
        description="Observer longitude",
    ),
):
    """
    Returns current rain conditions and the next several
    hourly precipitation probabilities.
    """

    from app.services.rain_prediction_service import (
        get_rain_prediction,
    )

    try:
        return await get_rain_prediction(
            latitude=latitude,
            longitude=longitude,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"Rain prediction failed: {e}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch rain prediction.",
        )

# ---------------------------------------------------------------------------
# GET /forecast — 7-day weather forecast
# ---------------------------------------------------------------------------
@router.get(
    "/forecast",
    summary="7-day weather forecast",
)
@limiter.limit("30/minute")
async def get_forecast(
    request: Request,
    latitude: float = Query(
        ...,
        ge=-90.0,
        le=90.0,
        description="Observer latitude",
    ),
    longitude: float = Query(
        ...,
        ge=-180.0,
        le=180.0,
        description="Observer longitude",
    ),
):
    """
    Returns a 7-day weather forecast for the supplied coordinates.
    """

    from app.services.forecast_service import (
        get_7_day_forecast,
    )

    try:
        return await get_7_day_forecast(
            latitude=latitude,
            longitude=longitude,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"7-day forecast failed: {e}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch 7-day forecast.",
        )

# ---------------------------------------------------------------------------
# GET /climate — Historical climate summary
# ---------------------------------------------------------------------------
@router.get(
    "/climate",
    summary="Historical climate information",
)
@limiter.limit("30/minute")
async def get_climate(
    request: Request,
    city: str = Query(
        default="Patna",
        description="Supported city name",
    ),
):
    from app.services.climate_service import (
        get_climate_summary,
    )

    try:
        return get_climate_summary(city)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"Climate summary failed: {e}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch climate information.",
        )

# ---------------------------------------------------------------------------
# POST /message — Conversational weather query (hardened & zero-hallucination)
# ---------------------------------------------------------------------------
@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Natural language weather query with zero-hallucination guarantee",
)
@limiter.limit("30/minute")
async def chat_message(
    request: Request,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Processes a natural language weather question grounded in real IMD/ECMWF
    station data. Anti-hallucination audit strictly validates LLM output
    and replaces hallucinated figures with deterministic ground truth.
    """
    lat = payload.latitude
    lon = payload.longitude

    # Intelligent entity recognition: If query explicitly names a major city,
    # and coordinates were default or user asks about that city, resolve city coords
    words = re.findall(r"\b[A-Za-z]+\b", payload.query)
    for word in words:
        city_coords = RealtimeWeatherService.resolve_city_coordinates(word)
        if city_coords:
            lat, lon, _ = city_coords
            break

    # ---------------------------------------------------------------
    # AI/ML temperature prediction intent
    # Example:
    # "Mumbai ka next hour temperature kya hoga?"
    # ---------------------------------------------------------------
    if _is_next_hour_temperature_query(payload.query):

        prediction_location = (
            _extract_temperature_prediction_location(
                payload.query
            )
        )

        if prediction_location:

            try:
                prediction = (
                    await predict_multi_city_next_hour_temperature(
                        prediction_location
                    )
                )

                current_temp = prediction[
                    "current_temperature_c"
                ]

                predicted_temp = prediction[
                    "predicted_temperature_c"
                ]

                answer_text = (
                    f"For {prediction['location']}, the "
                    f"current temperature is "
                    f"{current_temp:.2f}°C and the predicted "
                    f"temperature for the next hour is "
                    f"approximately {predicted_temp:.2f}°C."
                )

                prediction_response = ChatResponse(
                    response=answer_text,
                    ground_truth={
                        "type": "temperature_prediction",
                        "location": prediction["location"],
                        "resolved_location": prediction[
                            "resolved_location"
                        ],
                        "current_temperature_c": current_temp,
                        "predicted_temperature_c": predicted_temp,
                        "prediction_for": "next_hour",
                        "model": prediction["model"],
                        "current_time": prediction[
                            "current_time"
                        ],
                    },
                    source_authority=prediction["model"],
                    cached=False,
                    hallucination_audit_passed=True,
                )

                # Optional voice response
                if payload.include_voice:
                    try:
                        audio_bytes = (
                            await VoiceService.synthesize_speech(
                                text=prediction_response.response,
                                language=payload.language or "en",
                                gender="female",
                            )
                        )

                        prediction_response.audio_base64 = (
                            base64.b64encode(
                                audio_bytes
                            ).decode("utf-8")
                        )

                    except Exception as e:
                        logger.warning(
                            "Voice synthesis for temperature "
                            f"prediction skipped: {e}"
                        )

                return prediction_response

            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=str(e),
                )

            except Exception as e:
                logger.error(
                    "Temperature prediction failed: "
                    f"{e}",
                    exc_info=True,
                )

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Temperature prediction failed."
                    ),
                )

    chat_resp = await WeatherAgent.process_query(
        db=db,
        query=payload.query,
        latitude=lat,
        longitude=lon,
        language=payload.language or "en",
    )

    # Automatic voice synthesis if requested
    if payload.include_voice and chat_resp.response:
        try:
            audio_bytes = await VoiceService.synthesize_speech(
                text=chat_resp.response,
                language=payload.language or "en",
                gender="female",
            )
            chat_resp.audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            logger.warning(f"Voice synthesis for chat message skipped due to error: {e}")

    return chat_resp


# ---------------------------------------------------------------------------
# POST /voice/transcribe — Voice to text
# ---------------------------------------------------------------------------
@router.post(
    "/voice/transcribe",
    summary="Transcribe voice audio to text",
)
@limiter.limit("10/minute")
async def transcribe_voice(
    request: Request,
    language: str = Query(
        default="en",
        description="Voice language: en, hi, bn, mr",
    ),
):
    try:
        audio_bytes = await request.body()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="Audio data is empty.",
            )

        selected_language = (
            language
            if language in ("en", "hi", "bn", "mr")
            else None
        )

        result = await VoiceService.transcribe_audio(
            audio_bytes=audio_bytes,
            filename="recording.webm",
            language=selected_language,
        )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            f"Voice transcription failed: {exc}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to transcribe audio.",
        )


# ---------------------------------------------------------------------------
# POST /rain-impact — Rain impact zone analysis
# ---------------------------------------------------------------------------
@router.post(
    "/rain-impact",
    response_model=RainImpactResponse,
    summary="Post-rain area impact analysis",
)
@limiter.limit("30/minute")
async def analyze_rain_impact(
    request: Request,
    payload: RainImpactRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Given coordinates and current/expected rainfall (mm/hr), returns:
    - IMD-classified rainfall intensity (Light -> Extremely Heavy)
    - Risk-scored list of area types likely to be affected
    - Active CAP v1.2 alerts intersecting the search radius
    - LLM-generated advisory narrative grounded in ground-truth data
    """
    return await WeatherAgent.analyze_rain_impact(db=db, request=payload)


# ---------------------------------------------------------------------------
# POST /safe-route — Route safety advisory
# ---------------------------------------------------------------------------
@router.post(
    "/safe-route",
    response_model=SafeRouteResponse,
    summary="Safe route advisory during rain/flood events",
)
@limiter.limit("30/minute")
async def safe_route_advisory(
    request: Request,
    payload: SafeRouteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Given an origin and destination (lat/lon), checks whether the route
    intersects any active CAP disaster alert zones using PostGIS spatial
    geometry (ST_MakeLine + ST_Intersects).
    """
    return await WeatherAgent.advise_safe_route(db=db, request=payload)



@router.get("/analytics")
def analytics(
    city: str = "Patna",
    year: int | None = None,
    month: int | None = None,
):
    try:
        return get_monthly_analytics(
            city=city,
            year=year,
            month=month,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analytics generation failed: {exc}",
        )