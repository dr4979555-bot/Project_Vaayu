import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

os.makedirs("keys", exist_ok=True)

# Generate NIST P-256 (SECP256R1) private key
private_key = ec.generate_private_key(ec.SECP256R1())

# Serialize Private Key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

# Serialize Public Key
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

with open("keys/alert_private.pem", "wb") as f:
    f.write(private_pem)

with open("keys/alert_public.pem", "wb") as f:
    f.write(public_pem)

print("Generated keys/alert_private.pem and keys/alert_public.pem")