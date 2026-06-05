from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

k=ec.generate_private_key(ec.SECP256R1(),default_backend())
p=k.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8,encryption_algorithm=serialization.NoEncryption()).decode()
b=k.public_key().public_bytes(encoding=serialization.Encoding.X962,format=serialization.PublicFormat.UncompressedPoint)
u=base64.urlsafe_b64encode(b).decode().rstrip('=')
open('vapid_private_key.pem','w').write(p)
print(f"PUBLIC_KEY={u}")
