# 🔐 Instrucciones para Regenerar Claves VAPID

## Problema Actual
Las suscripciones Web Push fueron creadas con una clave VAPID diferente (de Firebase), 
pero el backend tiene otra clave privada local que no coincide.

**Error:** `403 Forbidden - the VAPID credentials do not correspond to the credentials used to create the subscriptions`

## Solución

### Opción 1: Regenerar Claves VAPID (Recomendado)

1. **Ejecuta en la terminal** (dentro de P2-backend):
   ```bash
   python gen_keys.py
   ```

2. **Copia la clave pública** que aparece (algo como `PUBLIC_KEY=BAbC123...`)

3. **Actualiza `.env`** (línea 50 aprox):
   ```
   FCM_VAPID_KEY=[PEGAR_AQUI_LA_CLAVE_PUBLICA]
   ```

4. **Actualiza `P2-frontend/src/environments/environment.ts`** (línea 14 aprox):
   ```typescript
   vapidKey: "[PEGAR_AQUI_LA_CLAVE_PUBLICA]"
   ```

5. **Reinicia**:
   - Backend: detener y reiniciar
   - Frontend: recompilar si está corriendo

6. **Los usuarios deben**:
   - Cerrar sesión y volver a iniciar sesión en la web
   - Aceptar nuevamente las notificaciones push cuando el navegador lo solicite

### Opción 2: Usar Solo FCM (Firebase Cloud Messaging)

Si prefieres no usar Web Push nativo y solo usar FCM:

1. Modifica `app/services/notification_service.py` para que solo use FCM
2. Elimina el código de Web Push del frontend
3. Usa solo tokens FCM tradicionales

## ¿Por qué pasó esto?

Las claves VAPID son pares criptográficos (pública/privada):
- **Clave pública**: Se usa en el frontend al suscribirse a notificaciones
- **Clave privada**: Se usa en el backend al enviar notificaciones

Si cambias una, debes cambiar la otra y **los usuarios deben re-suscribirse**.

## Verificación

Después de actualizar, en los logs del backend deberías ver:
```
✅ Clave privada VAPID cargada desde archivo PEM
📌 Clave pública VAPID: [primeros 50 caracteres]
```

Y NO debe aparecer:
```
⚠️ La clave FCM_VAPID_KEY del .env no coincide con la clave privada
```
