import math
import json
import logging
import asyncio
from typing import Dict, List, Tuple, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("WeatherGPT.AlertBroadcaster")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two lat/lon points in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _ray_casting_point_in_polygon(lat: float, lon: float, polygon: List[List[float]]) -> bool:
    """
    Standard ray-casting algorithm to test if (lat, lon) is inside polygon.
    polygon format: [[lon, lat], [lon, lat], ...]
    """
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]

        # Check if ray crosses edge
        intersect = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-9) + xi
        )
        if intersect:
            inside = not inside
        j = i

    return inside


class AlertBroadcaster:
    """
    Priority 1: Real-Time Disaster Alert Broadcasting Service.
    Pub/Sub connection manager for WebSockets and Server-Sent Events (SSE).
    Uses spatial point-in-polygon and proximity buffering to push instant
    emergency warnings to clients located inside or near CAP hazard zones.
    """

    # Active WebSocket clients: websocket -> (lat, lon)
    _ws_clients: Dict[WebSocket, Tuple[float, float]] = {}

    # Active SSE subscriber queues: queue -> (lat, lon)
    _sse_queues: Dict[asyncio.Queue, Tuple[float, float]] = {}

    @classmethod
    async def register_ws(cls, websocket: WebSocket, latitude: float, longitude: float) -> None:
        """Registers a new WebSocket connection with the client's GPS coordinates."""
        await websocket.accept()
        cls._ws_clients[websocket] = (latitude, longitude)
        logger.info(
            f"WebSocket client registered at ({latitude:.4f}, {longitude:.4f}). "
            f"Total active WS: {len(cls._ws_clients)}"
        )
        # Send initial confirmation message
        await websocket.send_text(
            json.dumps({
                "type": "connection_ack",
                "status": "connected",
                "registered_location": {"latitude": latitude, "longitude": longitude},
                "message": "Subscribed to real-time CAP disaster alerts for your area.",
            })
        )

    @classmethod
    def unregister_ws(cls, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        if websocket in cls._ws_clients:
            del cls._ws_clients[websocket]
            logger.info(f"WebSocket client unregistered. Remaining WS: {len(cls._ws_clients)}")

    @classmethod
    def update_ws_location(cls, websocket: WebSocket, latitude: float, longitude: float) -> None:
        """Updates the registered GPS coordinates of an active WebSocket client."""
        if websocket in cls._ws_clients:
            cls._ws_clients[websocket] = (latitude, longitude)
            logger.debug(f"Updated WS location to ({latitude:.4f}, {longitude:.4f})")

    @classmethod
    def register_sse(cls, latitude: float, longitude: float) -> asyncio.Queue:
        """Registers a new SSE client queue."""
        q: asyncio.Queue = asyncio.Queue()
        cls._sse_queues[q] = (latitude, longitude)
        logger.info(f"SSE client registered at ({latitude:.4f}, {longitude:.4f}). Total SSE: {len(cls._sse_queues)}")
        return q

    @classmethod
    def unregister_sse(cls, q: asyncio.Queue) -> None:
        """Removes an SSE subscriber queue."""
        if q in cls._sse_queues:
            del cls._sse_queues[q]
            logger.info(f"SSE client unregistered. Remaining SSE: {len(cls._sse_queues)}")

    @classmethod
    def is_location_affected(
        cls,
        client_lat: float,
        client_lon: float,
        polygon_coords: List[List[float]],
        buffer_km: float = 10.0,
    ) -> bool:
        """
        Determines whether a client's GPS location is inside the hazard polygon
        or within `buffer_km` proximity buffer of the alert zone boundary.
        """
        # 1. Point-in-polygon check
        if _ray_casting_point_in_polygon(client_lat, client_lon, polygon_coords):
            return True

        # 2. Proximity check against vertices
        for pt in polygon_coords:
            v_lon, v_lat = pt[0], pt[1]
            dist = _haversine_km(client_lat, client_lon, v_lat, v_lon)
            if dist <= buffer_km:
                return True

        return False

    @classmethod
    async def broadcast_alert(
        cls,
        alert: Dict[str, Any],
        polygon_coords: List[List[float]],
        buffer_km: float = 10.0,
    ) -> int:
        """
        Broadcasts a CAP disaster alert to all connected WebSocket and SSE clients
        whose registered GPS locations fall within or near the alert's hazard polygon.
        Returns the count of notified clients.
        """
        notification_payload = {
            "type": "EMERGENCY_ALERT",
            "alert_id": alert.get("alert_id"),
            "sender": alert.get("sender"),
            "severity": alert.get("severity"),
            "event_category": alert.get("event_category"),
            "headline": alert.get("headline"),
            "description": alert.get("description"),
            "instruction": alert.get("instruction"),
            "sent_at": alert.get("sent_at"),
            "polygon_coordinates": polygon_coords,
        }
        serialized = json.dumps(notification_payload)
        notified_count = 0

        # 1. Push to matching WebSocket clients
        dead_ws = []
        for ws, (lat, lon) in list(cls._ws_clients.items()):
            if cls.is_location_affected(lat, lon, polygon_coords, buffer_km=buffer_km):
                try:
                    await ws.send_text(serialized)
                    notified_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send alert to WS client: {e}")
                    dead_ws.append(ws)

        for ws in dead_ws:
            cls.unregister_ws(ws)

        # 2. Push to matching SSE subscriber queues
        dead_sse = []
        for q, (lat, lon) in list(cls._sse_queues.items()):
            if cls.is_location_affected(lat, lon, polygon_coords, buffer_km=buffer_km):
                try:
                    q.put_nowait(f"data: {serialized}\n\n")
                    notified_count += 1
                except Exception as e:
                    logger.warning(f"Failed to push to SSE queue: {e}")
                    dead_sse.append(q)

        for q in dead_sse:
            cls.unregister_sse(q)

        logger.info(
            f"Alert '{alert.get('headline')}' broadcasted to {notified_count} active clients "
            f"within {buffer_km}km of hazard polygon."
        )
        return notified_count
