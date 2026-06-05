"""
Script para extraer la clave pública VAPID de la clave privada existente
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

# Leer la clave privada desde el archivo PEM
with open('vapid_private_key.pem', 'r') as f:
    private_pem = f.read()

# Cargar la clave privada
private_key = serialization.load_pem_private_key(
    private_pem.encode('utf-8'),
    password=None,
    backend=default_backend()
)

# Obtener la clave pública
public_key = private_key.public_key()

# Serializar clave pública en formato raw (sin comprimir)
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Convertir a base64url (formato VAPID)
public_key_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')

print("=" * 80)
print("🔑 CLAVE PÚBLICA VAPID EXTRAÍDA")
print("=" * 80)
print()
print("Clave Pública (base64url) - Usar en el FRONTEND y en FCM_VAPID_KEY del .env:")
print()
print(public_key_b64)
print()
print("=" * 80)
print()
print("Actualiza el .env con:")
print(f'FCM_VAPID_KEY={public_key_b64}')
print()
print("=" * 80)
