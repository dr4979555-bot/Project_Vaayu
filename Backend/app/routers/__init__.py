"""
WeatherGPT Routers Module
Exports modular API routers for chat interfaces, CAP disaster warnings,
voice pipeline, and machine learning predictions.
"""

from app.routers.chat import router as chat_router
from app.routers.alerts import router as alert_router
from app.routers.voice import router as voice_router
from app.routers.ml_prediction import router as ml_prediction_router


__all__ = [
    "chat_router",
    "alert_router",
    "voice_router",
    "ml_prediction_router",
]