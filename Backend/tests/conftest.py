import os
import base64
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.main import app
from app.services.alert_verifier import AlertVerifier
from app.schemas import NowcastResponse


@pytest.fixture(scope="session")
def test_ecdsa_keypair():
    """Generates a transient NIST P-256 ECDSA keypair for cryptographic testing."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_key, public_pem


@pytest.fixture
def sign_alert_payload(test_ecdsa_keypair):
    """Helper to generate a validly signed CAP alert payload using test keypair."""
    private_key, _, public_pem = test_ecdsa_keypair

    def _sign(
        sender="IMD_HQ_NEW_DELHI",
        sent_at="2026-09-20T12:00:00Z",
        severity="Severe",
        event_category="Urban Flood",
        headline="Heavy Waterlogging Warning",
        coords=None,
    ):
        if coords is None:
            coords = [
                [85.10, 25.55],
                [85.20, 25.55],
                [85.20, 25.65],
                [85.10, 25.65],
                [85.10, 25.55],
            ]

        wkt_points = ", ".join(f"{lon} {lat}" for lon, lat in coords)
        polygon_wkt = f"POLYGON(({wkt_points}))"

        canonical_bytes = AlertVerifier.canonicalize_alert(
            sender=sender,
            sent_at=sent_at,
            severity=severity,
            event_category=event_category,
            headline=headline,
            polygon_wkt=polygon_wkt,
        )

        signature = private_key.sign(canonical_bytes, ec.ECDSA(hashes.SHA256()))
        sig_b64 = base64.b64encode(signature).decode("utf-8")

        return {
            "payload": {
                "sender": sender,
                "sent_at": sent_at,
                "status": "Actual",
                "severity": severity,
                "event_category": event_category,
                "headline": headline,
                "description": "Intense rainfall causing urban waterlogging.",
                "instruction": "Avoid low-lying areas.",
                "polygon_coordinates": coords,
                "signature_ecdsa": sig_b64,
            },
            "public_pem": public_pem,
        }

    return _sign


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client bound to the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
