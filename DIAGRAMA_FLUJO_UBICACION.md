# 📍 DIAGRAMA: Flujo de Ubicación del Técnico

## 🔴 FLUJO ANTERIOR (CON ERROR)

```
┌─────────────────────────────────────────────────────────────┐
│ PASO 1: Técnico en Servicio A (ID=1)                       │
│ ─────────────────────────────────────────────────────────── │
│ Técnico guarda ubicación:                                   │
│   • id_empleado: 10                                         │
│   • id_servicio: 1                                          │
│   • latitud: -17.3935                                       │
│   • longitud: -66.1568                                      │
│   • activa: TRUE                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 2: Servicio A se finaliza                             │
│ ─────────────────────────────────────────────────────────── │
│ Técnico y vehículo se liberan                               │
│ ❌ PROBLEMA: La ubicación queda activa = TRUE              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 3: Técnico asignado a Servicio B (ID=2)               │
│ ─────────────────────────────────────────────────────────── │
│ Técnico NO actualiza su ubicación todavía                   │
│ (está en camino al nuevo servicio)                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 4: Cliente consulta ubicación                          │
│ ─────────────────────────────────────────────────────────── │
│ Backend ejecuta:                                            │
│   SELECT * FROM empleado_ubicacion                          │
│   WHERE id_empleado = 10                                    │
│     AND activa = TRUE                                       │
│   ORDER BY timestamp DESC;                                  │
│                                                              │
│ ❌ DEVUELVE: Ubicación del Servicio A (vieja)             │
│ ❌ Cliente ve al técnico en la ubicación anterior          │
└─────────────────────────────────────────────────────────────┘
```

## ✅ FLUJO CORREGIDO (NUEVO)

```
┌─────────────────────────────────────────────────────────────┐
│ PASO 1: Técnico en Servicio A (ID=1)                       │
│ ─────────────────────────────────────────────────────────── │
│ Técnico guarda ubicación:                                   │
│   • id_empleado: 10                                         │
│   • id_servicio: 1                                          │
│   • latitud: -17.3935                                       │
│   • longitud: -66.1568                                      │
│   • activa: TRUE                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 2: Servicio A se finaliza                             │
│ ─────────────────────────────────────────────────────────── │
│ ✅ Técnico y vehículo se liberan                           │
│ ✅ Ubicación puede quedar activa (no importa)              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 3: Técnico asignado a Servicio B (ID=2)               │
│ ─────────────────────────────────────────────────────────── │
│ Cuando el técnico actualiza su ubicación:                   │
│   1. Se DESACTIVAN todas las ubicaciones anteriores         │
│   2. Se crea nueva ubicación con id_servicio = 2            │
│                                                              │
│ Base de datos:                                              │
│   Row 1: id_servicio=1, activa=FALSE (desactivada)         │
│   Row 2: id_servicio=2, activa=TRUE  (nueva)               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ PASO 4: Cliente consulta ubicación del Servicio B          │
│ ─────────────────────────────────────────────────────────── │
│ Backend ejecuta:                                            │
│   SELECT * FROM empleado_ubicacion                          │
│   WHERE id_empleado = 10                                    │
│     AND activa = TRUE                                       │
│     AND id_servicio = 2  ← ✅ NUEVO FILTRO                │
│   ORDER BY timestamp DESC;                                  │
│                                                              │
│ ✅ DEVUELVE: Ubicación del Servicio B (correcta)          │
│ ✅ Cliente ve al técnico en la ubicación actual            │
└─────────────────────────────────────────────────────────────┘
```

## 📊 COMPARACIÓN DE CONSULTAS SQL

### ❌ CONSULTA ANTERIOR (INCORRECTA)
```sql
SELECT * FROM empleado_ubicacion
WHERE id_empleado = 10
  AND activa = true
ORDER BY timestamp DESC
LIMIT 1;
```
**Problema:** Puede devolver ubicación de cualquier servicio anterior.

### ✅ CONSULTA NUEVA (CORRECTA)
```sql
SELECT * FROM empleado_ubicacion
WHERE id_empleado = 10
  AND activa = true
  AND id_servicio = 2  -- Filtra por servicio específico
ORDER BY timestamp DESC
LIMIT 1;
```
**Solución:** Solo devuelve ubicación del servicio solicitado.

## 🎯 CASOS DE USO

### Caso 1: Técnico tiene ubicación para el servicio actual
```
Cliente solicita: Servicio ID=2, Técnico ID=10
Backend busca: id_empleado=10, id_servicio=2, activa=true
Resultado: ✅ Encuentra ubicación → Muestra en mapa
```

### Caso 2: Técnico NO tiene ubicación para el servicio actual
```
Cliente solicita: Servicio ID=2, Técnico ID=10
Backend busca: id_empleado=10, id_servicio=2, activa=true
Resultado: ❌ No encuentra → Muestra mensaje "Ubicación no disponible"
```

### Caso 3: Técnico tiene ubicación de servicio anterior
```
BD contiene:
  - Row 1: id_empleado=10, id_servicio=1, activa=false (vieja)
  - Row 2: id_empleado=10, id_servicio=1, activa=true (no desactivada)
  - Row 3: id_empleado=10, id_servicio=2, activa=true (actual)

Cliente solicita: Servicio ID=2, Técnico ID=10
Backend busca: id_empleado=10, id_servicio=2, activa=true
Resultado: ✅ Solo devuelve Row 3 → Ubicación correcta
```

## 🔄 FLUJO DE ACTUALIZACIÓN DE UBICACIÓN

```
┌──────────────────┐
│ App Móvil        │
│ (Técnico)        │
└────────┬─────────┘
         │ POST /tecnico/servicios/2/actualizar-ubicacion
         │ Body: { latitud: -17.40, longitud: -66.16 }
         ↓
┌────────────────────────────────────────────────────────────┐
│ Backend: actualizar_ubicacion_tecnico()                    │
│ ────────────────────────────────────────────────────────── │
│ 1. Verificar servicio existe                               │
│ 2. Verificar técnico asignado al servicio                  │
│ 3. Verificar servicio en estado activo                     │
│ 4. Llamar: crear_ubicacion(id_empleado, lat, lon, id_serv)│
└────────┬───────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────┐
│ CRUD: crear_ubicacion()                                    │
│ ────────────────────────────────────────────────────────── │
│ 1. DESACTIVAR todas las ubicaciones anteriores:            │
│    UPDATE empleado_ubicacion                               │
│    SET activa = false                                      │
│    WHERE id_empleado = 10 AND activa = true;               │
│                                                             │
│ 2. CREAR nueva ubicación activa:                           │
│    INSERT INTO empleado_ubicacion                          │
│    (id_empleado, latitud, longitud, activa, id_servicio)   │
│    VALUES (10, -17.40, -66.16, true, 2);                   │
└────────┬───────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────┐
│ Base de Datos                                              │
│ ────────────────────────────────────────────────────────── │
│ empleado_ubicacion:                                        │
│  id │ id_empleado │ id_servicio │ lat     │ lon    │ activa│
│ ────┼─────────────┼─────────────┼─────────┼────────┼───────│
│  1  │     10      │      1      │ -17.39  │ -66.15 │ FALSE │
│  2  │     10      │      2      │ -17.40  │ -66.16 │ TRUE  │← Nueva
└────────────────────────────────────────────────────────────┘
```

## 🎨 VISUALIZACIÓN EN LA APP DEL CLIENTE

### ❌ Antes (Error):
```
┌──────────────────────────────────────┐
│ Servicio #2 - En Camino              │
├──────────────────────────────────────┤
│ 🚗 Técnicos:                          │
│   • Juan Pérez                       │
├──────────────────────────────────────┤
│ MAPA:                                │
│                                      │
│  🏠 Cliente (Ubicación B)            │
│                                      │
│                                      │
│  👤 Técnico (Ubicación A) ❌ ERROR   │
│      ↑                               │
│      Muestra ubicación del           │
│      servicio anterior               │
└──────────────────────────────────────┘
```

### ✅ Después (Correcto):
```
┌──────────────────────────────────────┐
│ Servicio #2 - En Camino              │
├──────────────────────────────────────┤
│ 🚗 Técnicos:                          │
│   • Juan Pérez                       │
├──────────────────────────────────────┤
│ MAPA:                                │
│                                      │
│  🏠 Cliente (Ubicación B)            │
│      ↑                               │
│      │ ═══ Ruta ═══                 │
│      ↓                               │
│  👤 Técnico (Ubicación B) ✅         │
│      ↑                               │
│      Muestra ubicación actual        │
│      del servicio activo             │
└──────────────────────────────────────┘
```

## 📝 NOTAS IMPORTANTES

1. **Compatibilidad hacia atrás**: El parámetro `id_servicio` es opcional, por lo que código existente sigue funcionando.

2. **Desactivación automática**: Cuando un técnico actualiza su ubicación, TODAS las ubicaciones anteriores se desactivan automáticamente.

3. **Un técnico, múltiples servicios**: Un técnico puede estar asignado a varios servicios, pero solo tendrá una ubicación activa por servicio.

4. **Limpieza de datos**: Ejecutar `LIMPIAR_UBICACIONES_ANTIGUAS.sql` para eliminar ubicaciones huérfanas.

5. **Logs de debug**: El backend imprime logs útiles para diagnosticar problemas.
