from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat & Telemetry Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str = Field(..., description="Natural language user question")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    language: Optional[str] = Field("en", description="ISO 639-1 language code")
    include_voice: Optional[bool] = Field(False, description="Automatically synthesize and return assistant voice audio")


class ChatResponse(BaseModel):
    response: str
    ground_truth: Dict[str, Any] = Field(default_factory=dict)
    source_authority: str = "IMD_AWS"
    cached: bool = False
    hallucination_audit_passed: bool = True
    audio_base64: Optional[str] = None


class NowcastResponse(BaseModel):
    latitude: float
    longitude: float
    station_name: str
    distance_km: float
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    rainfall_mm: Optional[float] = 0.0
    wind_speed_kmh: Optional[float] = None
    weather_condition: Optional[str] = None
    precipitation_probability_pct: Optional[int] = None
    surface_pressure_hpa: Optional[float] = None
    source: str
    # Stored as ISO-8601 string — avoids pydantic datetime coercion
    timestamp: Optional[str] = None
    active_alert: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# CAP v1.2 Disaster Alert Schemas
# ---------------------------------------------------------------------------

class CAPAlertIngestRequest(BaseModel):
    sender: str = Field(..., examples=["IMD_HQ_NEW_DELHI"])
    sent_at: str = Field(..., examples=["2026-09-20T11:00:00Z"])
    status: str = Field(default="Actual", examples=["Actual"])
    severity: str = Field(..., examples=["Severe"])
    event_category: str = Field(..., examples=["Urban Flood"])
    headline: str = Field(..., examples=["Urban Waterlogging & Flash Flood Advisory"])
    description: str = Field(..., examples=["Heavy localized rainfall exceeding 50mm/hr."])
    instruction: Optional[str] = Field(None, examples=["Avoid underpasses and low-lying roads."])
    polygon_coordinates: List[List[float]] = Field(
        ...,
        description="List of [longitude, latitude] pairs forming a closed ring",
    )
    signature_ecdsa: str = Field(
        ...,
        description="Base64-encoded NIST P-256 ECDSA signature over canonical alert string",
    )


class CAPAlertResponse(BaseModel):
    alert_id: str
    status: str
    verified: bool
    message: str


class ActiveAlertSummary(BaseModel):
    alert_id: str
    sender: str
    severity: str
    event_category: str
    headline: str
    sent_at: str
    instruction: Optional[str] = None


# ---------------------------------------------------------------------------
# Rain Impact Analysis Schemas
# ---------------------------------------------------------------------------

class RainImpactRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    rainfall_mm: float = Field(
        ..., ge=0.0, description="Current or expected rainfall in mm/hr"
    )
    radius_km: float = Field(
        default=10.0, ge=0.5, le=100.0,
        description="Radius to search for active alert zones (km)"
    )
    language: Optional[str] = Field("en", description="ISO 639-1 language code")


class ImpactZone(BaseModel):
    zone_type: str = Field(..., description="Type of affected area")
    risk_level: str = Field(..., description="HIGH | MEDIUM | LOW")
    description: str = Field(..., description="Detailed description of impact")
    recommended_action: str = Field(..., description="Action to take for this zone")


class RainImpactResponse(BaseModel):
    location_summary: str
    rainfall_intensity: str = Field(
        ..., description="IMD classification: Light | Moderate | Heavy | Very Heavy | Extremely Heavy"
    )
    impact_zones: List[ImpactZone]
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    advisory: str = Field(..., description="Overall LLM-generated advisory narrative")
    source_authority: str = "IMD_AWS"
    cached: bool = False


# ---------------------------------------------------------------------------
# Safe Route Advisory Schemas
# ---------------------------------------------------------------------------

class RoutePoint(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    label: Optional[str] = Field(None, description="Human-readable location name")


class SafeRouteRequest(BaseModel):
    origin: RoutePoint
    destination: RoutePoint
    rainfall_mm: Optional[float] = Field(
        None, ge=0.0, description="Current rainfall mm/hr for context"
    )
    travel_mode: str = Field(
        default="road",
        description="Travel mode: road | foot | emergency"
    )
    language: Optional[str] = Field("en", description="ISO 639-1 language code")


class RouteSegmentRisk(BaseModel):
    segment: str = Field(..., description="Description of the route segment")
    risk_level: str = Field(..., description="HIGH | MEDIUM | LOW | CLEAR")
    reason: str = Field(..., description="Why this segment is at risk")


class SafeRouteResponse(BaseModel):
    route_status: str = Field(
        ..., description="Overall status: SAFE | CAUTION | AVOID"
    )
    overall_risk: str = Field(..., description="Risk summary")
    affected_segments: List[RouteSegmentRisk] = Field(default_factory=list)
    safe_route_advisory: str = Field(
        ..., description="LLM-generated step-by-step advisory"
    )
    alternative_suggestion: str = Field(
        ..., description="Suggested alternative approach or route"
    )
    active_alerts_on_path: List[Dict[str, Any]] = Field(default_factory=list)
    source_authority: str = "IMD_AWS"
    cached: bool = False