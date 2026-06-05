"""
Script para regenerar claves VAPID y actualizar automáticamente los archivos
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
import os

# Generar nuevo par de claves EC (Elliptic Curve)
print("🔄 Generando nuevo par de claves VAPID...")
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
public_key = private_key.public_key()

# Serializar clave privada a PEM
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

# Obtener clave pública en formato raw (sin comprimir)
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Convertir a base64url (formato VAPID)
public_key_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')

# Guardar clave privada en archivo
with open('vapid_private_key.pem', 'w') as f:
    f.write(private_pem)

print("=" * 80)
print("✅ CLAVES VAPID GENERADAS Y GUARDADAS")
print("=" * 80)
print()
print("📝 Clave Privada guardada en: vapid_private_key.pem")
print()
print("📋 Clave Pública (base64url) - COPIA ESTE VALOR:")
print()
print(public_key_b64)
print()
print("=" * 80)
print("🔧 ACTUALIZA ESTOS ARCHIVOS:")
print("=" * 80)
print()
print("1. Backend (.env):")
print(f"   FCM_VAPID_KEY={public_key_b64}")
print()
print("2. Frontend (src/environments/environment.ts):")
print(f'   vapidKey: "{public_key_b64}"')
print()
print("=" * 80)
print("⚠️  IMPORTANTE: Los usuarios deben re-suscribirse a las notificaciones web")
print("=" * 80)
