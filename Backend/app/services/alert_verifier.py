import base64
import os
from typing import Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

DEFAULT_PUBLIC_KEY_PATH = os.path.join("keys", "alert_public.pem")


class AlertVerifier:
    """
    Cryptographic verification service for CAP v1.2 alerts.
    Enforces ECDSA (NIST P-256 / SHA-256) signature verification on canonical payloads.
    """

    @staticmethod
    def canonicalize_alert(
        sender: str,
        sent_at: str,
        severity: str,
        event_category: str,
        headline: str,
        polygon_wkt: str,
    ) -> bytes:
        """
        Builds a deterministic, reproducible UTF-8 representation
        for cryptographic signature validation.
        """
        raw_repr = (
            f"sender={sender}|"
            f"sent_at={sent_at}|"
            f"severity={severity}|"
            f"event_category={event_category}|"
            f"headline={headline}|"
            f"polygon={polygon_wkt}"
        )
        return raw_repr.encode("utf-8")

    @classmethod
    def get_public_key_pem(cls) -> bytes:
        """Loads public key from settings or the keys directory."""
        from app.config import settings
        if settings.IMD_PUBLIC_KEY_PEM and settings.IMD_PUBLIC_KEY_PEM.strip():
            return settings.IMD_PUBLIC_KEY_PEM.strip().encode("utf-8")

        if os.path.exists(DEFAULT_PUBLIC_KEY_PATH):
            with open(DEFAULT_PUBLIC_KEY_PATH, "rb") as f:
                return f.read()
        raise FileNotFoundError(
            f"Authority public key not found at {DEFAULT_PUBLIC_KEY_PATH} and not configured in settings. "
            "Run python generate_keys.py first or set IMD_PUBLIC_KEY_PEM."
        )

    @classmethod
    def verify_signature(
        cls,
        payload_bytes: bytes,
        signature_b64: str,
        public_key_pem: Optional[bytes] = None,
    ) -> bool:
        """
        Validates ECDSA (SHA-256 with NIST P-256) signature.
        """
        try:
            pem_data = public_key_pem or cls.get_public_key_pem()
            public_key = load_pem_public_key(pem_data)
            signature = base64.b64decode(signature_b64)

            public_key.verify(
                signature,
                payload_bytes,
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except (InvalidSignature, ValueError, Exception):
            return False