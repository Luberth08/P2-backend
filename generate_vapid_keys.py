"""
Script para generar un par de claves VAPID para Web Push
Ejecutar: python generate_vapid_keys.py
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Generar par de claves EC (Elliptic Curve)
private_key = ec.generate_private_key(ec.SECP256R1())
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

print("=" * 60)
print("🔑 CLAVES VAPID GENERADAS")
print("=" * 60)
print()
print("Clave Pública (base64url) para el FRONTEND:")
print(public_key_b64)
print()
print("Clave Privada (PEM) para el BACKEND:")
print(private_pem)
print()
print("=" * 60)
print("📋 PRÓXIMOS PASOS:")
print("=" * 60)
print()
print("Pégame estas dos claves completas aquí y yo las actualizo en el código.")
print()
print("=" * 60)
