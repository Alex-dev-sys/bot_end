import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate key
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096,
)

# Save private key
with open("pvp_bot_key", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))

# Save public key
public_key = key.public_key()
with open("pvp_bot_key.pub", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ))
print("Keys generated successfully.")
