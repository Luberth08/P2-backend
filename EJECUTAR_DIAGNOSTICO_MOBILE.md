# 🔍 Diagnóstico: Servicio No Aparece en Móvil

## Paso 1: Ejecutar Script de Diagnóstico

```bash
cd BACKEND-repo
python debug_servicio_mobile.py
```

Cuando te pregunte, ingresa el **id_persona del cliente** (probablemente 19).

---

## Qué Verificará el Script

1. ✅ Solicitudes de diagnóstico del cliente
2. ✅ Diagnósticos generados
3. ✅ Solicitudes de servicio creadas
4. ✅ Servicios creados
5. ✅ **Estados considerados "activos" por el endpoint**
6. ✅ Query EXACTA que usa el endpoint `/cliente/servicio-actual`
7. ✅ Análisis de por qué no se encontró (si aplica)
8. ✅ Valores del enum EstadoServicio

---

## Posibles Causas

### 1. Estado del Servicio NO está en la lista de activos
El endpoint solo devuelve servicios con estos estados:
- `creado`
- `tecnico_asignado`
- `en_camino`
- `en_lugar`
- `en_atencion`

**NO devuelve**:
- `finalizado`
- `cancelado`

### 2. Base URL Incorrecta en el Móvil
Verifica que en `lib/services/cliente_api.dart` y `lib/services/servicio_api.dart`:
```dart
static const String baseUrl = 'https://backend-repo-2ncr.onrender.com/api/v1';
```

Si estás probando localmente, cambiar a:
```dart
static const String baseUrl = 'http://localhost:8000/api/v1';
```

O usar la IP de tu PC en la red local:
```dart
static const String baseUrl = 'http://192.168.X.X:8000/api/v1';
```

### 3. Token Expirado o Incorrecto
El token JWT debe ser válido y corresponder al cliente correcto.

---

## Paso 2: Analizar Resultado

### Si el script muestra "✅ SERVICIO ACTIVO ENCONTRADO"
Entonces el backend SÍ está funcionando. El problema está en:
1. **Base URL** incorrecta en el móvil
2. **Token** incorrecto o expirado
3. **Network** - el móvil no puede conectarse al backend

### Si el script muestra "❌ NO SE ENCONTRÓ SERVICIO ACTIVO"
Lee el análisis que muestra el script. Probablemente:
1. **Estado incorrecto** - el servicio tiene un estado que no está en la lista
2. **Joins rotos** - problema con las relaciones en BD
3. **Cliente incorrecto** - el servicio no pertenece a ese cliente

---

## Paso 3: Verificar Conectividad desde Móvil

### Desde el móvil, verifica los logs:

```bash
adb logcat | findstr "flutter"
```

Busca líneas como:
```
🔍 Consultando servicio actual...
📡 Status code: 200
📦 Response body: {...}
```

---

## Soluciones Rápidas

### Solución 1: Cambiar Base URL a Local (Desarrollo)

**Opción A: Usar IP de PC en red local**
1. Obtener IP de tu PC: `ipconfig` (Windows) → buscar "IPv4 Address"
2. Cambiar en móvil:
```dart
static const String baseUrl = 'http://192.168.X.X:8000/api/v1';
```
3. Asegurar que el backend local esté corriendo:
```bash
cd BACKEND-repo
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Opción B: Usar ngrok (exponer backend local a internet)**
```bash
ngrok http 8000
```
Usar la URL que da ngrok en el móvil.

### Solución 2: Verificar Estado del Servicio en BD

```sql
-- Conectar a PostgreSQL
SELECT id, estado, fecha, id_solicitud_servicio
FROM servicio
ORDER BY fecha DESC
LIMIT 5;
```

Si el estado NO está en la lista de activos, cambiarlo:
```sql
UPDATE servicio
SET estado = 'tecnico_asignado'
WHERE id = [ID_DEL_SERVICIO];
```

### Solución 3: Reiniciar App Móvil Completamente

1. Cerrar app completamente (no solo minimizar)
2. Abrir app de nuevo
3. Iniciar sesión de nuevo
4. Ir a tab "Servicios"
5. Tocar "Actualizar"

---

## Comandos Útiles

```bash
# Ver logs en tiempo real del móvil
adb logcat -c && adb logcat | findstr "flutter"

# Ver solo logs de HTTP
adb logcat | findstr "Status code"

# Ejecutar backend local con logs visibles
cd BACKEND-repo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verificar que el backend responde
curl http://localhost:8000/api/v1/cliente/servicio-actual -H "Authorization: Bearer [TOKEN]"
```

---

## Checklist de Verificación

- [ ] Script de diagnóstico ejecutado
- [ ] Script muestra "SERVICIO ACTIVO ENCONTRADO"
- [ ] Estado del servicio está en lista de activos
- [ ] Base URL en móvil es correcta
- [ ] Backend está corriendo y accesible
- [ ] Móvil puede conectarse al backend
- [ ] Token es válido
- [ ] Logs del móvil muestran Status 200
- [ ] App móvil reiniciada completamente

---

**EJECUTA EL SCRIPT Y COMPARTE EL RESULTADO** 🔍
