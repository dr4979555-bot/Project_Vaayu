import json
import asyncio
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.limiter import limiter
from app.schemas import CAPAlertIngestRequest, CAPAlertResponse, ActiveAlertSummary
from app.services.alert_verifier import AlertVerifier
from app.services.security_service import SecurityService
from app.services.alert_broadcaster import AlertBroadcaster

logger = logging.getLogger("WeatherGPT.AlertRouter")
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /ingest — Ingest a signed CAP v1.2 alert & broadcast to affected users
# ---------------------------------------------------------------------------
@router.post(
    "/ingest",
    response_model=CAPAlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a signed CAP v1.2 disaster alert & broadcast via WebSockets/SSE",
)
@limiter.limit("20/minute")
async def ingest_cap_alert(
    request: Request,
    payload: CAPAlertIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a Common Alerting Protocol (CAP v1.2) alert signed with
    ECDSA (NIST P-256 / SHA-256). Verifies the cryptographic signature,
    persists the alert polygon in PostGIS, and broadcasts real-time emergency
    warnings to all connected users within the hazard polygon.
    """
    # 1. Security & DoS Validation on polygon coordinates
    coords = SecurityService.validate_polygon_coordinates(payload.polygon_coordinates)

    # 2. Anti-Replay & Freshness validation on sent_at
    SecurityService.validate_alert_timestamp(payload.sent_at)

    wkt_points = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    polygon_wkt = f"POLYGON(({wkt_points}))"

    # 3. Canonicalize and verify ECDSA signature
    canonical_bytes = AlertVerifier.canonicalize_alert(
        sender=payload.sender,
        sent_at=payload.sent_at,
        severity=payload.severity,
        event_category=payload.event_category,
        headline=payload.headline,
        polygon_wkt=polygon_wkt,
    )

    is_valid = AlertVerifier.verify_signature(
        payload_bytes=canonical_bytes,
        signature_b64=payload.signature_ecdsa,
    )

    if not is_valid:
        logger.warning(f"Signature verification failed for sender={payload.sender}, headline={payload.headline}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cryptographic verification failed: Invalid ECDSA signature for authority.",
        )

    # 4. Persist to PostGIS spatial database
    try:
        insert_query = text("""
            INSERT INTO public.disaster_alerts (
                sender,
                sent_at,
                status,
                severity,
                event_category,
                headline,
                description,
                instruction,
                affected_polygon,
                signature_ecdsa
            ) VALUES (
                :sender,
                :sent_at,
                :status,
                :severity,
                :event_category,
                :headline,
                :description,
                :instruction,
                extensions.ST_GeomFromText(:wkt, 4326),
                :sig
            )
            RETURNING alert_id;
        """)

        result = await db.execute(
            insert_query,
            {
                "sender": payload.sender,
                "sent_at": payload.sent_at,
                "status": payload.status,
                "severity": payload.severity,
                "event_category": payload.event_category,
                "headline": payload.headline,
                "description": payload.description,
                "instruction": payload.instruction,
                "wkt": polygon_wkt,
                "sig": payload.signature_ecdsa,
            },
        )
        await db.commit()

        alert_row = result.mappings().first()
        if alert_row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Alert was not persisted — database did not return an alert_id.",
            )

        alert_id = str(alert_row["alert_id"])

        # 5. [Priority 1] Real-Time Alert Broadcast to affected WebSockets/SSE clients
        asyncio.create_task(
            AlertBroadcaster.broadcast_alert(
                alert={
                    "alert_id": alert_id,
                    "sender": payload.sender,
                    "severity": payload.severity,
                    "event_category": payload.event_category,
                    "headline": payload.headline,
                    "description": payload.description,
                    "instruction": payload.instruction,
                    "sent_at": payload.sent_at,
                },
                polygon_coords=coords,
            )
        )

        return CAPAlertResponse(
            alert_id=alert_id,
            status="Ingested",
            verified=True,
            message="Alert verified, registered in spatial registry, and broadcasted to hazard area.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to persist alert in database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while registering disaster alert.",
        )


# ---------------------------------------------------------------------------
# WebSocket /ws — Real-time bidirectional alerting stream with GPS registration
# ---------------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_alert_stream(
    websocket: WebSocket,
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Client latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Client longitude"),
):
    """
    Subscribes a client to instant emergency alerts for their GPS location.
    Clients can send location update frames:
    {"type": "location_update", "latitude": 25.60, "longitude": 85.14}
    """
    await AlertBroadcaster.register_ws(websocket, latitude, longitude)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "location_update":
                    new_lat = float(msg["latitude"])
                    new_lon = float(msg["longitude"])
                    AlertBroadcaster.update_ws_location(websocket, new_lat, new_lon)
                    await websocket.send_text(
                        json.dumps({
                            "type": "ack",
                            "status": "location_updated",
                            "new_location": {"latitude": new_lat, "longitude": new_lon},
                        })
                    )
                elif mtype == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception as parse_err:
                logger.debug(f"WS message parse error: {parse_err}")
    except WebSocketDisconnect:
        AlertBroadcaster.unregister_ws(websocket)


# ---------------------------------------------------------------------------
# GET /stream — Server-Sent Events (SSE) stream for real-time alerts
# ---------------------------------------------------------------------------
@router.get(
    "/stream",
    summary="Server-Sent Events (SSE) stream for real-time disaster alerts",
)
async def sse_alert_stream(
    request: Request,
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Observer latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Observer longitude"),
):
    """
    HTTP Server-Sent Events stream delivering real-time CAP disaster alerts
    for clients located inside or near an active hazard polygon.
    """
    queue = AlertBroadcaster.register_sse(latitude, longitude)

    async def event_generator():
        try:
            # Initial connection frame
            yield f"data: {json.dumps({'type': 'connection_ack', 'status': 'connected', 'latitude': latitude, 'longitude': longitude})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat comment
                    yield ": heartbeat\n\n"
        finally:
            AlertBroadcaster.unregister_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /active — Query active alerts in a spatial radius (hardened)
# ---------------------------------------------------------------------------
@router.get(
    "/active",
    response_model=List[ActiveAlertSummary],
    summary="List active CAP alerts near a location",
)
@limiter.limit("60/minute")
async def get_active_alerts(
    request: Request,
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Observer latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Observer longitude"),
    radius_km: float = Query(
        default=50.0, ge=0.5, le=500.0,
        description="Search radius in kilometres",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all active (status='Actual') CAP v1.2 disaster alerts whose
    registered polygon overlaps or is within `radius_km` of the given
    coordinates. Uses PostGIS ST_DWithin on geography for metric accuracy.
    """
    try:
        query = text("""
            SELECT
                alert_id::text,
                sender,
                severity,
                event_category,
                headline,
                instruction,
                sent_at::text AS sent_at
            FROM public.disaster_alerts
            WHERE
                status = 'Actual'
                AND extensions.ST_DWithin(
                    affected_polygon::extensions.geography,
                    extensions.ST_SetSRID(
                        extensions.ST_MakePoint(:lon, :lat), 4326
                    )::extensions.geography,
                    :radius_meters
                )
            ORDER BY sent_at DESC;
        """)

        result = await db.execute(
            query,
            {
                "lat": float(latitude),
                "lon": float(longitude),
                "radius_meters": float(radius_km * 1000.0),
            },
        )
        rows = result.mappings().all()

        if not rows:
            return []

        return [
            ActiveAlertSummary(
                alert_id=str(row["alert_id"]),
                sender=row["sender"],
                severity=row["severity"],
                event_category=row["event_category"],
                headline=row["headline"],
                sent_at=str(row["sent_at"]),
                instruction=row.get("instruction"),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Active alerts query error: {e}", exc_info=True)
        return []