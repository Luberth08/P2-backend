# 🗺️ SOLUCIÓN: Ubicación del Técnico no se Muestra en el Mapa del Cliente

## 📋 PROBLEMA IDENTIFICADO

Cuando el cliente visualiza un servicio activo en la app móvil y selecciona un técnico, **no se muestra la ubicación del técnico en el mapa ni la ruta trazada**, a pesar de que el técnico ha guardado su ubicación.

## 🔍 CAUSA RAÍZ

El problema estaba en la función `get_ubicacion_activa()` en el archivo `crud_empleado_ubicacion.py`:

### Código Anterior (INCORRECTO):
```python
async def get_ubicacion_activa(
    self,
    db: AsyncSession,
    id_empleado: int
) -> Optional[EmpleadoUbicacion]:
    """Obtiene la ubicación activa de un empleado"""
    result = await db.execute(
        select(EmpleadoUbicacion).where(
            and_(
                EmpleadoUbicacion.id_empleado == id_empleado,
                EmpleadoUbicacion.activa == True
            )
        ).order_by(EmpleadoUbicacion.timestamp.desc())
    )
    return result.scalar_one_or_none()
```

**Problema:** Solo filtraba por `id_empleado` y `activa = true`, sin verificar el `id_servicio`.

### Escenario del Bug:
1. Técnico guardó su ubicación en un **Servicio A** (finalizado)
2. Su ubicación quedó marcada como `activa = true` con `id_servicio = A`
3. Técnico fue asignado a un **Servicio B** (actual)
4. Técnico guardó ubicación en **Servicio B** → esto DESACTIVÓ la ubicación del Servicio A
5. ✅ El sistema ahora correctamente devuelve la ubicación del Servicio B

**Pero si el técnico NO guardaba ubicación en el nuevo servicio:**
- La consulta devolvía una ubicación activa del servicio anterior
- El cliente veía la ubicación del técnico en el servicio viejo

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. Modificar `get_ubicacion_activa()` para Aceptar `id_servicio` Opcional

**Archivo:** `app/crud/crud_empleado_ubicacion.py`

```python
async def get_ubicacion_activa(
    self,
    db: AsyncSession,
    id_empleado: int,
    id_servicio: Optional[int] = None
) -> Optional[EmpleadoUbicacion]:
    """
    Obtiene la ubicación activa de un empleado.
    Si se proporciona id_servicio, filtra solo ubicaciones de ese servicio.
    """
    conditions = [
        EmpleadoUbicacion.id_empleado == id_empleado,
        EmpleadoUbicacion.activa == True
    ]
    
    if id_servicio is not None:
        conditions.append(EmpleadoUbicacion.id_servicio == id_servicio)
    
    result = await db.execute(
        select(EmpleadoUbicacion).where(and_(*conditions))
        .order_by(EmpleadoUbicacion.timestamp.desc())
    )
    return result.scalar_one_or_none()
```

**Mejora:** Ahora acepta un parámetro opcional `id_servicio` para filtrar ubicaciones específicas del servicio actual.

### 2. Actualizar Endpoint de Seguimiento del Cliente

**Archivo:** `app/api/api_v1/endpoints/cliente_servicios.py`

**Endpoint:** `GET /cliente/servicio-actual`

```python
# Obtener ubicación activa del técnico PARA ESTE SERVICIO específico
ubicacion = await crud_empleado_ubicacion.empleado_ubicacion.get_ubicacion_activa(
    db, empleado.id, id_servicio=servicio.id
)
```

**Cambio:** Se pasa `id_servicio=servicio.id` para garantizar que solo se devuelvan ubicaciones del servicio actual.

### 3. Actualizar Endpoint de Ruta del Técnico

**Archivo:** `app/api/api_v1/endpoints/cliente_servicios.py`

**Endpoint:** `GET /cliente/servicio/{servicio_id}/tecnico/{empleado_id}/ruta`

```python
# Obtener ubicación del técnico PARA ESTE SERVICIO específico
ubicacion_tecnico = await crud_empleado_ubicacion.empleado_ubicacion.get_ubicacion_activa(
    db, empleado_id, id_servicio=servicio_id
)

if not ubicacion_tecnico:
    raise HTTPException(
        status_code=404,
        detail="El técnico no tiene ubicación disponible para este servicio"
    )
```

**Cambio:** Mensaje de error más descriptivo y filtrado por servicio específico.

## 🔄 FLUJO CORRECTO AHORA

### Cuando el Técnico Guarda su Ubicación:
1. Técnico llama: `POST /tecnico/servicios/{servicio_id}/actualizar-ubicacion`
2. Backend ejecuta `crear_ubicacion()`:
   ```python
   await self.desactivar_ubicaciones_empleado(db, id_empleado)
   ubicacion = EmpleadoUbicacion(
       id_empleado=id_empleado,
       latitud=latitud,
       longitud=longitud,
       activa=True,
       id_servicio=id_servicio  # ✅ Se guarda el servicio
   )
   ```
3. ✅ Todas las ubicaciones anteriores se desactivan
4. ✅ Nueva ubicación se marca como activa con el `id_servicio` correcto

### Cuando el Cliente Consulta Ubicación:
1. Cliente llama: `GET /cliente/servicio-actual`
2. Backend busca ubicación: `get_ubicacion_activa(db, empleado.id, id_servicio=servicio.id)`
3. SQL ejecuta:
   ```sql
   SELECT * FROM empleado_ubicacion
   WHERE id_empleado = X
     AND activa = true
     AND id_servicio = Y  -- ✅ Filtra por servicio específico
   ORDER BY timestamp DESC;
   ```
4. ✅ Solo devuelve ubicaciones del servicio actual

## 🧪 CÓMO PROBAR

### 1. Verificar Ubicaciones en Base de Datos

Ejecutar el script de diagnóstico:
```bash
psql -U postgres -d nombre_bd -f DIAGNOSTICO_UBICACION_RAPIDO.sql
```

Debería mostrar:
- Cuántas ubicaciones activas existen
- A qué servicio pertenecen
- Timestamp de cada una

### 2. Probar desde App Móvil del Técnico

1. **Asignar técnico a un servicio**
2. **Desde app del técnico:**
   - Abrir el servicio asignado
   - Presionar "Actualizar Ubicación"
   - Verificar mensaje de éxito
3. **En base de datos, verificar:**
   ```sql
   SELECT id, id_empleado, id_servicio, latitud, longitud, activa, timestamp
   FROM empleado_ubicacion
   WHERE id_empleado = [ID_TECNICO]
   ORDER BY timestamp DESC
   LIMIT 5;
   ```
   - Debe haber UNA ubicación `activa = true` con el `id_servicio` correcto
   - Las anteriores deben estar `activa = false`

### 3. Probar desde App Móvil del Cliente

1. **Desde app del cliente:**
   - Ir a "Servicios" → "Mis Servicios"
   - Presionar "Actualizar"
   - Debe aparecer el servicio activo
2. **Abrir el servicio**
3. **Seleccionar el técnico en la lista**
4. **Verificar:**
   - ✅ Debe aparecer un marcador en el mapa con la ubicación del técnico
   - ✅ Debe trazarse una ruta desde el técnico hasta el cliente
   - ✅ La ubicación debe coincidir con la guardada en la base de datos

## 📊 LOGS DE DEBUG

El endpoint `obtener_servicio_actual` imprime logs útiles:

```python
print(f"🔍 DEBUG - Servicio {servicio.id}: {len(asignaciones)} técnicos asignados")
print(f"👤 DEBUG - Técnico {empleado.id}: {empleado.usuario.nombre}")
print(f"📍 DEBUG - Ubicación encontrada: lat={ubicacion.latitud}, lon={ubicacion.longitud}")
print(f"⚠️ DEBUG - No hay ubicación activa para técnico {empleado.id} en servicio {servicio.id}")
```

**Verificar logs del backend** para diagnosticar problemas.

## 🚀 PRÓXIMOS PASOS

1. **Reiniciar el servidor backend** para que tome los cambios
   ```bash
   # Si usas uvicorn
   uvicorn app.main:app --reload
   ```

2. **Limpiar ubicaciones antiguas** (opcional):
   ```sql
   -- Desactivar todas las ubicaciones activas sin servicio
   UPDATE empleado_ubicacion 
   SET activa = false 
   WHERE id_servicio IS NULL AND activa = true;
   
   -- Desactivar ubicaciones de servicios finalizados/cancelados
   UPDATE empleado_ubicacion eu
   SET activa = false
   FROM servicio s
   WHERE eu.id_servicio = s.id
     AND eu.activa = true
     AND s.estado IN ('finalizado', 'cancelado');
   ```

3. **Probar flujo completo** end-to-end

## ✅ RESULTADO ESPERADO

Después de estos cambios:
- ✅ El cliente ve la ubicación correcta del técnico en el mapa
- ✅ La ruta se traza correctamente desde técnico → cliente
- ✅ La ubicación se actualiza en tiempo real (cada 30s)
- ✅ No se muestran ubicaciones de servicios anteriores
- ✅ Si el técnico no tiene ubicación para el servicio actual, se muestra mensaje apropiado

## 📝 ARCHIVOS MODIFICADOS

1. ✅ `app/crud/crud_empleado_ubicacion.py` - Agregar filtro por `id_servicio`
2. ✅ `app/api/api_v1/endpoints/cliente_servicios.py` - Usar filtro en 2 endpoints
3. ✅ `DIAGNOSTICO_UBICACION_RAPIDO.sql` - Script de diagnóstico

## 🔧 COMPATIBILIDAD

**Cambio compatible hacia atrás:** ✅
- El parámetro `id_servicio` es **opcional**
- El código existente que llame `get_ubicacion_activa(db, empleado_id)` seguirá funcionando
- Solo los nuevos llamados con `id_servicio` obtienen el filtrado mejorado
