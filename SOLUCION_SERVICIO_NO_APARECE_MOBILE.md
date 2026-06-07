# 🔧 Solución: Servicio no aparece en app móvil del cliente

## ❌ PROBLEMA

Después de que el taller acepta una solicitud desde el panel web:
- El servicio se crea correctamente
- Pero NO aparece en la app móvil del cliente
- Muestra "No hay servicio activo"

## 🔍 ANÁLISIS DEL CÓDIGO

### 1. Estado al crear el servicio (Backend)

Cuando el taller acepta una solicitud (`servicio_service.py` línea 205):
```python
servicio_data = {
    'id_taller': id_taller,
    'id_solicitud_servicio': id_solicitud,
    'estado': EstadoServicio.tecnico_asignado  # ⭐ ESTE ES EL ESTADO
}
```

### 2. Estados considerados "activos" en el móvil (Backend)

Endpoint `/cliente/servicio-actual` (`cliente_servicios.py` línea 77-82):
```python
Servicio.estado.in_([
    EstadoServicio.creado,
    EstadoServicio.tecnico_asignado,  # ✅ SÍ ESTÁ EN LA LISTA
    EstadoServicio.en_camino,
    EstadoServicio.en_lugar,
    EstadoServicio.en_atencion
])
```

✅ **El estado `tecnico_asignado` SÍ está en la lista de estados activos**

---

## 🔍 CAUSAS POSIBLES

### CAUSA 1: Enum no actualizado en la base de datos ⭐ (MÁS PROBABLE)

Si ejecutaste el SQL para actualizar el enum solo en **local**, pero NO en **producción (Render)**, entonces:

- **Local:** El enum tiene `tecnico_asignado` ✅
- **Render:** El enum NO tiene `tecnico_asignado` ❌

Cuando el backend en Render intenta insertar `tecnico_asignado`, falla silenciosamente o lanza error 500.

### CAUSA 2: BASE_URL apunta a producción pero trabajas en local

En tu `.env` tienes:
```env
BASE_URL="https://backend-repo-2ncr.onrender.com"
```

Si estás probando **localmente** pero el móvil está configurado para apuntar a Render, entonces:
- El servicio se crea en **local**
- El móvil consulta a **Render**
- No encuentra el servicio porque está en otra BD

### CAUSA 3: Error al crear el servicio

El servicio puede estar fallando al crearse por el error del enum que vimos antes.

---

## ✅ SOLUCIÓN

### PASO 1: Verificar si el enum está actualizado en Render

#### Opción A: Conectarte a la BD de Render

```bash
# Obtén la URL de conexión externa de tu BD en Render
# Dashboard → PostgreSQL → External Database URL

psql "postgresql://asistencia_vehicular_db_0fqi_user:wFXf1gxboekuFegZlfFsafd5NdhuwrRX@dpg-d8gs4iugvqtc738q9kdg-a.oregon-postgres.render.com/asistencia_vehicular_db_0fqi?sslmode=require"

# Verificar el enum
\dT+ estadoservicio

# Deberías ver:
# creado
# tecnico_asignado  ⭐
# en_camino
# en_lugar
# en_atencion
# finalizado
# cancelado
```

#### Opción B: Revisar logs de Render

1. Ve al dashboard de Render
2. Abre tu servicio de Backend
3. Click en "Logs"
4. Busca errores al aceptar solicitud
5. Busca: `invalid input value for enum estadoservicio`

---

### PASO 2: Aplicar la migración del enum en Render

Si el enum NO está actualizado en Render:

#### Opción A: Via Shell de Render (MÁS FÁCIL)

1. Dashboard de Render → Backend service
2. Click en "Shell" (arriba a la derecha)
3. Ejecutar:
   ```bash
   cd /opt/render/project/src
   alembic stamp merge_heads_final
   ```

#### Opción B: Via SQL directo en la BD de Render

1. Conectarte a la BD (comando psql de arriba)
2. Ejecutar el contenido de `SQL_FIX_ENUM_CORRECTO.sql`

```sql
-- Copiar y pegar TODO el contenido de SQL_FIX_ENUM_CORRECTO.sql
```

---

### PASO 3: Verificar que el móvil apunta al servidor correcto

En `MOBILE-repo/lib/services/cliente_api.dart` (línea 7):
```dart
static const String baseUrl = 'https://backend-repo-2ncr.onrender.com/api/v1';
```

Opciones:
- **Si trabajas en local:** Cambia a `'http://10.0.2.2:8000/api/v1'` (para emulador)
- **Si trabajas con Render:** Deja la URL de Render

---

### PASO 4: Probar el flujo completo

1. **Limpiar la app móvil:**
   - Desinstalar la app
   - Reinstalar
   - O limpiar datos de la app

2. **Crear una nueva solicitud desde el móvil:**
   - Iniciar sesión como cliente
   - Ir a Diagnóstico
   - Crear solicitud con foto/audio
   - Enviar

3. **Aceptar desde el panel web:**
   - Iniciar sesión como admin del taller
   - Ir a Gestión de Servicios → Solicitudes
   - Ver detalle
   - Seleccionar técnicos y vehículos
   - Aceptar servicio

4. **Verificar en el móvil:**
   - Ir a pestaña "Servicios"
   - Debería aparecer el servicio activo
   - Con estado "Técnico asignado"

---

## 🔍 DIAGNÓSTICO RÁPIDO

### Test 1: Verificar que el servicio se crea

Después de aceptar una solicitud, en tu BD ejecuta:

```sql
SELECT id, estado, fecha, id_solicitud_servicio 
FROM servicio 
ORDER BY fecha DESC 
LIMIT 5;
```

¿Aparece el servicio con estado `tecnico_asignado`?
- ✅ SÍ → El problema está en el móvil o en la consulta
- ❌ NO → El problema está al crear el servicio (enum)

### Test 2: Verificar el endpoint desde Postman/curl

```bash
# Obtén el token del cliente
# Luego:
curl -X GET "https://backend-repo-2ncr.onrender.com/api/v1/cliente/servicio-actual" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

¿Devuelve el servicio?
- ✅ SÍ → El problema está en el móvil
- ❌ NO (null) → El problema está en el endpoint o la consulta

### Test 3: Ver logs del backend

Al aceptar la solicitud, busca en los logs:

```
✅ Correcto:
INFO: Servicio creado con estado tecnico_asignado

❌ Error:
ERROR: invalid input value for enum estadoservicio: "tecnico_asignado"
```

---

## 📋 CHECKLIST DE SOLUCIÓN

- [ ] Enum actualizado en BD local
- [ ] Enum actualizado en BD de Render
- [ ] `alembic stamp merge_heads_final` ejecutado en Render
- [ ] Servicio se crea correctamente (verificar en BD)
- [ ] Móvil apunta al servidor correcto
- [ ] App móvil reinstalada/limpiada
- [ ] Test completo: crear solicitud → aceptar → ver en móvil

---

## 🎯 COMANDOS RESUMIDOS

### Para Render (Shell):
```bash
cd /opt/render/project/src
alembic stamp merge_heads_final
```

### Para BD de Render (psql):
```bash
# Conectar
psql "postgresql://asistencia_vehicular_db_0fqi_user:wFXf1gxboekuFegZlfFsafd5NdhuwrRX@dpg-d8gs4iugvqtc738q9kdg-a.oregon-postgres.render.com/asistencia_vehicular_db_0fqi?sslmode=require"

# Verificar enum
\dT+ estadoservicio

# Si no tiene tecnico_asignado, ejecutar SQL_FIX_ENUM_CORRECTO.sql
```

### Para verificar:
```sql
-- Ver últimos servicios creados
SELECT id, estado, fecha, id_solicitud_servicio 
FROM servicio 
ORDER BY fecha DESC 
LIMIT 5;
```

---

## 💡 RECOMENDACIÓN

**El problema MÁS PROBABLE es que el enum NO está actualizado en Render.**

1. Conecta a la BD de Render
2. Verifica el enum: `\dT+ estadoservicio`
3. Si NO tiene `tecnico_asignado`, ejecuta `SQL_FIX_ENUM_CORRECTO.sql`
4. Prueba crear una nueva solicitud y aceptarla
5. Debería aparecer en el móvil

---

**¡Aplica el SQL del enum en Render y prueba de nuevo!** 🚀
