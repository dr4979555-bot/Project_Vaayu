import httpx

from app.services.realtime_weather import RealtimeWeatherService


OPEN_METEO_FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


async def get_7_day_forecast(
    latitude: float,
    longitude: float,
):
    """
    Fetch 7-day forecast data for the requested coordinates.
    """

    params = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "precipitation_sum",
            "sunrise",
            "sunset",
        ]),
        "forecast_days": 7,
        "timezone": "auto",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                OPEN_METEO_FORECAST_URL,
                params=params,
            )

            response.raise_for_status()

        data = response.json()

        if "daily" not in data:
            raise ValueError(
                "Daily forecast data not found."
            )

        daily = data["daily"]

        required_fields = [
            "time",
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "precipitation_sum",
            "sunrise",
            "sunset",
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in daily
        ]

        if missing_fields:
            raise ValueError(
                f"Missing forecast fields: {missing_fields}"
            )

        forecast = []

        for i, date in enumerate(daily["time"]):

            weather_code = daily["weather_code"][i]

            forecast.append({
                "date": date,
                "weather_code": weather_code,
                "condition": (
                    RealtimeWeatherService.get_wmo_condition(
                        weather_code
                    )
                ),
                "temperature_max_c": round(
                    float(
                        daily["temperature_2m_max"][i]
                    ),
                    1,
                ),
                "temperature_min_c": round(
                    float(
                        daily["temperature_2m_min"][i]
                    ),
                    1,
                ),
                "precipitation_probability_pct": (
                    daily[
                        "precipitation_probability_max"
                    ][i]
                ),
                "precipitation_sum_mm": round(
                    float(
                        daily["precipitation_sum"][i]
                    ),
                    1,
                ),
                "sunrise": daily["sunrise"][i],
                "sunset": daily["sunset"][i],
            })

        return {
            "latitude": round(float(latitude), 4),
            "longitude": round(float(longitude), 4),
            "timezone": data.get("timezone"),
            "forecast_days": forecast,
        }

    except httpx.HTTPError as e:
        raise RuntimeError(
            f"Forecast API request failed: {e}"
        ) from e

    except Exception:
        raise