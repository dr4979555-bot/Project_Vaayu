from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ml.prediction_service import prediction_service
from app.services.multi_city_temperature_predictor import (
    predict_multi_city_next_hour_temperature,
)

router = APIRouter()


# ============================================================
# LOW-LEVEL ML PREDICTION
# ============================================================

class TemperaturePredictionRequest(BaseModel):
    temperature_2m: float
    relative_humidity_2m: float
    precipitation: float
    rain: float
    surface_pressure: float
    wind_speed_10m: float
    wind_direction_10m: float
    weather_code: int

    hour: int
    day_of_week: int
    month: int

    temperature_lag_1: float
    temperature_lag_3: float
    temperature_lag_6: float
    temperature_lag_24: float

    humidity_lag_1: float
    pressure_lag_1: float
    wind_speed_lag_1: float

    temperature_rolling_3h: float
    temperature_rolling_6h: float
    temperature_rolling_24h: float


class TemperaturePredictionResponse(BaseModel):
    status: str
    predicted_temperature: float
    unit: str
    forecast_horizon: str


@router.post(
    "/predict-temperature",
    response_model=TemperaturePredictionResponse,
)
async def predict_temperature(
    request: TemperaturePredictionRequest,
):
    try:
        weather_data = request.model_dump()

        prediction = prediction_service.predict(weather_data)

        return {
            "status": "success",
            "predicted_temperature": prediction,
            "unit": "°C",
            "forecast_horizon": "next hour",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ML prediction failed: {str(e)}",
        )


# ============================================================
# HIGH-LEVEL AUTOMATIC LOCATION-BASED ML PREDICTION
# ============================================================

class LocationTemperaturePredictionRequest(BaseModel):
    location: str


class LocationTemperaturePredictionResponse(BaseModel):
    location: str
    current_time: str
    current_temperature_c: float
    predicted_temperature_c: float
    prediction_for: str
    model: str


@router.post(
    "/predict-location-temperature",
    response_model=LocationTemperaturePredictionResponse,
)
async def predict_location_temperature(
    request: LocationTemperaturePredictionRequest,
):
    try:
        location = request.location.strip()

        if not location:
            raise HTTPException(
                status_code=400,
                detail="Location cannot be empty.",
            )

        result = await predict_multi_city_next_hour_temperature(
            location
        )

        return {
            "location": result["location"],
            "current_time": result["current_time"],
            "current_temperature_c": result["current_temperature_c"],
            "predicted_temperature_c": result[
                "predicted_temperature_c"
            ],
            "prediction_for": result["prediction_for"],
            "model": result["model"],
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Location-based ML prediction failed: {str(e)}",
        )