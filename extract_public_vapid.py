#!/usr/bin/env python3
"""
Script para extraer la clave pública VAPID desde el archivo PEM
"""
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import base64
    
    # Leer la clave privada
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
    
    # Serializar en formato X962 (uncompressed point)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Convertir a base64url sin padding
    vapid_public_key = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
    
    print("="*60)
    print("CLAVE PÚBLICA VAPID EXTRAÍDA:")
    print("="*60)
    print(vapid_public_key)
    print("="*60)
    print("\nCopia esta clave y úsala en:")
    print("1. Backend .env -> FCM_VAPID_KEY")
    print("2. Frontend environment.ts -> firebase.vapidKey")
    
except ImportError:
    print("ERROR: El módulo 'cryptography' no está instalado")
    print("Instala con: pip install cryptography")
except Exception as e:
    print(f"ERROR: {e}")
