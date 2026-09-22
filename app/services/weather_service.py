import requests
import pandas as pd


# Patna coordinates
PATNA_LATITUDE = 25.5941
PATNA_LONGITUDE = 85.1376


def get_hourly_weather(
    latitude: float,
    longitude: float,
    past_hours: int = 48,
) -> pd.DataFrame:
    """
    Fetch recent hourly weather data.

    We fetch enough history because the ML model requires:
    - 1 hour lag
    - 3 hour lag
    - 6 hour lag
    - 24 hour lag
    - 3h rolling temperature
    - 6h rolling temperature
    - 24h rolling temperature
    """

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "weather_code",
        ]),
        "past_hours": past_hours,
        "forecast_hours": 1,
        "timezone": "auto",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        raise ValueError(
            "Hourly weather data not found in API response."
        )

    hourly = data["hourly"]

    df = pd.DataFrame(hourly)

    df["time"] = pd.to_datetime(df["time"])

    return df


def get_patna_weather(
    past_hours: int = 48,
) -> pd.DataFrame:
    """
    Fetch recent weather data for Patna.
    """

    return get_hourly_weather(
        latitude=PATNA_LATITUDE,
        longitude=PATNA_LONGITUDE,
        past_hours=past_hours,
    )