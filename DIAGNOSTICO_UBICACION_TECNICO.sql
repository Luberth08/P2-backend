-- ============================================================================
-- DIAGNÓSTICO: ¿Por qué no se muestra la ubicación del técnico en el mapa?
-- ============================================================================
-- Reemplaza los IDs según tu caso
-- ============================================================================

\set id_servicio 2
\set id_empleado 10

-- PASO 1: Ver el servicio
SELECT '=== PASO 1: Información del Servicio ===' as paso;
SELECT 
    s.id,
    s.estado,
    s.fecha,
    s.id_taller
FROM servicio s
WHERE s.id = :id_servicio;

-- PASO 2: Ver técnicos asignados al servicio
SELECT '=== PASO 2: Técnicos Asignados al Servicio ===' as paso;
SELECT 
    st.id_servicio,
    st.id_empleado,
    p.nombre || ' ' || p.apellido as tecnico,
    e.estado as estado_empleado
FROM servicio_tecnico st
JOIN empleado e ON e.id = st.id_empleado
JOIN usuario u ON u.id = e.id_usuario
JOIN persona p ON p.id = u.id_persona
WHERE st.id_servicio = :id_servicio;

-- PASO 3: Ver TODAS las ubicaciones del técnico
SELECT '=== PASO 3: Todas las Ubicaciones del Técnico ===' as paso;
SELECT 
    eu.id,
    eu.id_empleado,
    eu.latitud,
    eu.longitud,
    eu.timestamp,
    eu.activa,
    eu.id_servicio,
    AGE(NOW(), eu.timestamp) as antiguedad
FROM empleado_ubicacion eu
WHERE eu.id_empleado = :id_empleado
ORDER BY eu.timestamp DESC
LIMIT 10;

-- PASO 4: Ver ubicación ACTIVA del técnico
SELECT '=== PASO 4: Ubicación ACTIVA del Técnico ===' as paso;
SELECT 
    eu.id,
    eu.id_empleado,
    eu.latitud,
    eu.longitud,
    eu.timestamp,
    eu.activa,
    eu.id_servicio,
    AGE(NOW(), eu.timestamp) as antiguedad
FROM empleado_ubicacion eu
WHERE eu.id_empleado = :id_empleado
  AND eu.activa = true
ORDER BY eu.timestamp DESC;

-- PASO 5: Ver ubicación del cliente
SELECT '=== PASO 5: Ubicación del Cliente ===' as paso;
SELECT 
    sd.id,
    sd.id_persona,
    ST_Y(sd.ubicacion::geometry) as latitud_cliente,
    ST_X(sd.ubicacion::geometry) as longitud_cliente
FROM solicitud_diagnostico sd
JOIN diagnostico d ON d.id_solicitud_diagnostico = sd.id
JOIN solicitud_servicio ss ON ss.id_diagnostico = d.id
JOIN servicio s ON s.id_solicitud_servicio = ss.id
WHERE s.id = :id_servicio;

-- PASO 6: Verificar si el técnico guardó ubicación para ESTE servicio
SELECT '=== PASO 6: Ubicaciones del Técnico para ESTE Servicio ===' as paso;
SELECT 
    eu.id,
    eu.latitud,
    eu.longitud,
    eu.timestamp,
    eu.activa,
    AGE(NOW(), eu.timestamp) as antiguedad
FROM empleado_ubicacion eu
WHERE eu.id_empleado = :id_empleado
  AND eu.id_servicio = :id_servicio
ORDER BY eu.timestamp DESC;

-- RESUMEN
SELECT '=== RESUMEN FINAL ===' as paso;
WITH 
servicio_existe AS (
    SELECT COUNT(*) as total
    FROM servicio WHERE id = :id_servicio
),
tecnico_asignado AS (
    SELECT COUNT(*) as total
    FROM servicio_tecnico 
    WHERE id_servicio = :id_servicio AND id_empleado = :id_empleado
),
ubicaciones_totales AS (
    SELECT COUNT(*) as total
    FROM empleado_ubicacion
    WHERE id_empleado = :id_empleado
),
ubicacion_activa AS (
    SELECT COUNT(*) as total
    FROM empleado_ubicacion
    WHERE id_empleado = :id_empleado AND activa = true
),
ubicacion_para_servicio AS (
    SELECT COUNT(*) as total
    FROM empleado_ubicacion
    WHERE id_empleado = :id_empleado 
      AND id_servicio = :id_servicio
      AND activa = true
)
SELECT 
    (SELECT total FROM servicio_existe) as "1_servicio_existe",
    (SELECT total FROM tecnico_asignado) as "2_tecnico_asignado",
    (SELECT total FROM ubicaciones_totales) as "3_ubicaciones_totales",
    (SELECT total FROM ubicacion_activa) as "4_ubicacion_activa",
    (SELECT total FROM ubicacion_para_servicio) as "5_ubicacion_para_servicio";

-- ============================================================================
-- INTERPRETACIÓN
-- ============================================================================
/*
Si "1_servicio_existe" = 0:
  → El servicio no existe

Si "2_tecnico_asignado" = 0:
  → El técnico no está asignado a este servicio

Si "3_ubicaciones_totales" = 0:
  → El técnico NUNCA ha guardado su ubicación
  → PROBLEMA: El técnico no está actualizando su ubicación desde la app móvil

Si "4_ubicacion_activa" = 0:
  → El técnico NO tiene ninguna ubicación activa
  → PROBLEMA: Todas las ubicaciones fueron desactivadas o no hay ninguna

Si "4_ubicacion_activa" > 0 pero "5_ubicacion_para_servicio" = 0:
  → El técnico tiene ubicación activa pero NO para este servicio específico
  → SOLUCIÓN: Al guardar ubicación, pasar el id_servicio

Si "5_ubicacion_para_servicio" > 0:
  → TODO ESTÁ BIEN, debería aparecer en el mapa
  → Verificar el frontend/móvil
*/

-- ============================================================================
-- SOLUCIONES
-- ============================================================================

-- Si el técnico no tiene ubicación, crear una de prueba:
/*
INSERT INTO empleado_ubicacion (id_empleado, latitud, longitud, activa, id_servicio)
VALUES (:id_empleado, -17.3935, -66.1568, true, :id_servicio);
*/

-- Si hay ubicaciones viejas activas, desactivarlas:
/*
UPDATE empleado_ubicacion 
SET activa = false 
WHERE id_empleado = :id_empleado AND activa = true;
*/
