"""
Script para generar nuevas claves VAPID y actualizar todos los archivos automáticamente
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
import re

# Generar nuevo par de claves
print("🔄 Generando nuevas claves VAPID...")
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
public_key = private_key.public_key()

# Serializar clave privada a PEM
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

# Obtener clave pública en formato base64url
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
public_key_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')

# 1. Guardar clave privada
with open('vapid_private_key.pem', 'w') as f:
    f.write(private_pem)
print("✅ Clave privada guardada en vapid_private_key.pem")

# 2. Actualizar .env
try:
    with open('.env', 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # Reemplazar FCM_VAPID_KEY
    env_content = re.sub(
        r'FCM_VAPID_KEY=.*',
        f'FCM_VAPID_KEY={public_key_b64}',
        env_content
    )
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    print("✅ .env actualizado")
except Exception as e:
    print(f"❌ Error actualizando .env: {e}")

# 3. Actualizar frontend environment.ts
frontend_path = '../P2-frontend/src/environments/environment.ts'
try:
    with open(frontend_path, 'r', encoding='utf-8') as f:
        env_ts_content = f.read()
    
    # Reemplazar vapidKey
    env_ts_content = re.sub(
        r'vapidKey:\s*"[^"]*"',
        f'vapidKey: "{public_key_b64}"',
        env_ts_content
    )
    
    with open(frontend_path, 'w', encoding='utf-8') as f:
        f.write(env_ts_content)
    print("✅ Frontend environment.ts actualizado")
except Exception as e:
    print(f"❌ Error actualizando frontend: {e}")

print()
print("=" * 80)
print("✅ ACTUALIZACIÓN COMPLETA")
print("=" * 80)
print()
print(f"Nueva clave pública VAPID: {public_key_b64}")
print()
print("🔄 PRÓXIMOS PASOS:")
print("1. Reiniciar el servidor backend")
print("2. Recompilar el frontend (si está en ejecución)")
print("3. Los usuarios web deben:")
print("   - Cerrar sesión y volver a iniciar sesión")
print("   - O limpiar suscripciones antiguas desde el navegador")
print()
print("=" * 80)
