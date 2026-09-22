import re
import math
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import HTTPException, status
import logging

logger = logging.getLogger("WeatherGPT.SecurityService")

# Signatures for prompt injection, jailbreak attempts, and system override attacks
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"(system\s+prompt|system\s+directive|developer\s+mode)", re.IGNORECASE),
    re.compile(r"(dan\s+mode|jailbreak|unfiltered\s+mode)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|in)\s+", re.IGNORECASE),
    re.compile(r"(declare|issue|broadcast)\s+(an?\s+)?(red\s+alert|emergency|evacuation|warning)", re.IGNORECASE),
    re.compile(r"(override|bypass)\s+(safety|security|rules|guardrails?)", re.IGNORECASE),
    re.compile(r"(<\|im_start\|>|<\|im_end\|>|\[SYSTEM\]|\[INST\])", re.IGNORECASE),
]

# Max allowed length for user queries
MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 2

# CAP polygon limits
MIN_POLYGON_VERTICES = 3
MAX_POLYGON_VERTICES = 1000

# Alert freshness window
MAX_ALERT_AGE_DAYS = 7
MAX_ALERT_FUTURE_MINUTES = 60


class SecurityService:
    """
    Zero-Trust Security & Guardrail Service:
    1. Prompt-Injection & Adversarial Defense
    2. Input Sanitization & Control-Character Stripping
    3. CAP Alert Boundary Validation (WGS-84 bounds & vertex caps)
    4. Anti-Replay & Timestamp Freshness Verification
    """

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """
        Validates and sanitizes a user query:
        - Rejects queries exceeding length bounds
        - Strips control characters and non-printable bytes
        - Detects and rejects prompt injection and emergency spoofing attempts
        """
        if not query or len(query.strip()) < MIN_QUERY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must contain at least 2 characters.",
            )

        if len(query) > MAX_QUERY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query exceeds maximum permitted length of {MAX_QUERY_LENGTH} characters.",
            )

        # Strip non-printable/control characters except standard whitespace
        cleaned = "".join(ch for ch in query if ch.isprintable() or ch in "\n\r\t").strip()

        # Check for prompt injection signatures
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(cleaned):
                logger.warning(f"Security Alert: Blocked suspicious query matching pattern '{pattern.pattern}': {cleaned[:100]}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Suspicious instruction pattern or prompt injection detected.",
                )

        return cleaned

    @classmethod
    def validate_polygon_coordinates(cls, coords: List[List[float]]) -> List[List[float]]:
        """
        Validates polygon coordinate vertices for CAP v1.2 alerts:
        - Enforces minimum 3 vertices and maximum 1000 vertices (DoS defense)
        - Validates that each coordinate is [longitude, latitude] within WGS-84 bounds
        - Ensures coordinate ring is properly closed
        """
        if not coords or len(coords) < MIN_POLYGON_VERTICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Valid polygon requires at least {MIN_POLYGON_VERTICES} coordinate vertices.",
            )

        if len(coords) > MAX_POLYGON_VERTICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Polygon complexity exceeds maximum limit of {MAX_POLYGON_VERTICES} vertices.",
            )

        validated_coords: List[List[float]] = []
        for idx, pt in enumerate(coords):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid coordinate format at vertex {idx}: expected [longitude, latitude].",
                )

            lon, lat = pt[0], pt[1]

            # Validate numerical types and non-NaN/Inf
            if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Non-numeric coordinates at vertex {idx}.",
                )

            if math.isnan(lon) or math.isinf(lon) or math.isnan(lat) or math.isinf(lat):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"NaN or Infinite coordinate value at vertex {idx}.",
                )

            # WGS-84 bounds
            if not (-180.0 <= lon <= 180.0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Longitude {lon} at vertex {idx} out of range [-180.0, 180.0].",
                )

            if not (-90.0 <= lat <= 90.0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Latitude {lat} at vertex {idx} out of range [-90.0, 90.0].",
                )

            validated_coords.append([float(lon), float(lat)])

        # Ensure ring is closed
        if validated_coords[0] != validated_coords[-1]:
            validated_coords.append(validated_coords[0])

        return validated_coords

    @classmethod
    def validate_alert_timestamp(cls, sent_at_str: str) -> datetime:
        """
        Validates CAP alert sent_at timestamp to prevent replay attacks and clock skew:
        - Must be valid ISO 8601 string
        - Must not be older than MAX_ALERT_AGE_DAYS
        - Must not be further than MAX_ALERT_FUTURE_MINUTES in the future
        """
        try:
            # Parse ISO-8601 (supports trailing 'Z')
            clean_str = sent_at_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sent_at timestamp format '{sent_at_str}'. Must be ISO-8601.",
            ) from err

        now = datetime.now(timezone.utc)

        # Check for expired/ancient alert (replay attack defense)
        max_age = timedelta(days=MAX_ALERT_AGE_DAYS)
        if (now - dt) > max_age:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Alert sent_at timestamp is older than {MAX_ALERT_AGE_DAYS} days. Rejected to prevent replay.",
            )

        # Check for futuristic alert (clock spoofing defense)
        max_future = timedelta(minutes=MAX_ALERT_FUTURE_MINUTES)
        if (dt - now) > max_future:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Alert sent_at timestamp is more than {MAX_ALERT_FUTURE_MINUTES} minutes in the future.",
            )

        return dt
