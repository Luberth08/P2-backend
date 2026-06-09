-- ============================================================================
-- SCRIPT: Limpiar ubicaciones antiguas y huérfanas
-- ============================================================================
-- Ejecutar DESPUÉS de implementar los cambios en el código
-- ============================================================================

-- Ver cuántas ubicaciones hay en cada categoría
SELECT 
    'Total ubicaciones' as categoria,
    COUNT(*) as cantidad
FROM empleado_ubicacion
UNION ALL
SELECT 
    'Ubicaciones activas' as categoria,
    COUNT(*) as cantidad
FROM empleado_ubicacion
WHERE activa = true
UNION ALL
SELECT 
    'Ubicaciones sin servicio' as categoria,
    COUNT(*) as cantidad
FROM empleado_ubicacion
WHERE id_servicio IS NULL
UNION ALL
SELECT 
    'Ubicaciones de servicios finalizados/cancelados' as categoria,
    COUNT(*) as cantidad
FROM empleado_ubicacion eu
JOIN servicio s ON s.id = eu.id_servicio
WHERE s.estado IN ('finalizado', 'cancelado')
  AND eu.activa = true;

-- ============================================================================
-- LIMPIEZA 1: Desactivar ubicaciones sin servicio asociado
-- ============================================================================
-- Estas ubicaciones son de antes de implementar el id_servicio

UPDATE empleado_ubicacion 
SET activa = false 
WHERE id_servicio IS NULL 
  AND activa = true;

-- Ver resultado
SELECT 
    'Ubicaciones sin servicio desactivadas' as resultado,
    COUNT(*) as cantidad
FROM empleado_ubicacion
WHERE id_servicio IS NULL 
  AND activa = false;

-- ============================================================================
-- LIMPIEZA 2: Desactivar ubicaciones de servicios finalizados/cancelados
-- ============================================================================
-- Si un servicio ya terminó, sus ubicaciones no deberían estar activas

UPDATE empleado_ubicacion eu
SET activa = false
FROM servicio s
WHERE eu.id_servicio = s.id
  AND eu.activa = true
  AND s.estado IN ('finalizado', 'cancelado');

-- Ver resultado
SELECT 
    s.estado,
    COUNT(*) as ubicaciones_desactivadas
FROM empleado_ubicacion eu
JOIN servicio s ON s.id = eu.id_servicio
WHERE eu.activa = false
  AND s.estado IN ('finalizado', 'cancelado')
GROUP BY s.estado;

-- ============================================================================
-- LIMPIEZA 3: Detectar técnicos con múltiples ubicaciones activas
-- ============================================================================
-- Cada técnico debería tener máximo 1 ubicación activa por servicio

SELECT 
    eu.id_empleado,
    p.nombre || ' ' || p.apellido as tecnico,
    eu.id_servicio,
    COUNT(*) as ubicaciones_activas,
    MAX(eu.timestamp) as ultima_actualizacion
FROM empleado_ubicacion eu
JOIN empleado e ON e.id = eu.id_empleado
JOIN usuario u ON u.id = e.id_usuario
JOIN persona p ON p.id = u.id_persona
WHERE eu.activa = true
GROUP BY eu.id_empleado, p.nombre, p.apellido, eu.id_servicio
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

-- Si hay duplicados, desactivar todos excepto el más reciente
WITH ranked_locations AS (
    SELECT 
        id,
        id_empleado,
        id_servicio,
        timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY id_empleado, id_servicio 
            ORDER BY timestamp DESC
        ) as rn
    FROM empleado_ubicacion
    WHERE activa = true
)
UPDATE empleado_ubicacion eu
SET activa = false
FROM ranked_locations rl
WHERE eu.id = rl.id
  AND rl.rn > 1;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

-- Ver estado final de ubicaciones activas
SELECT 
    'Ubicaciones activas finales' as verificacion,
    COUNT(*) as cantidad
FROM empleado_ubicacion
WHERE activa = true;

-- Ver ubicaciones activas por servicio
SELECT 
    s.id as servicio_id,
    s.estado as estado_servicio,
    COUNT(DISTINCT eu.id_empleado) as tecnicos_con_ubicacion,
    COUNT(*) as ubicaciones_activas,
    MAX(eu.timestamp) as ultima_actualizacion
FROM servicio s
LEFT JOIN empleado_ubicacion eu ON eu.id_servicio = s.id AND eu.activa = true
WHERE s.estado IN ('tecnico_asignado', 'en_camino', 'en_lugar', 'en_atencion')
GROUP BY s.id, s.estado
ORDER BY s.id DESC;

-- Ver técnicos con ubicación activa
SELECT 
    e.id as empleado_id,
    p.nombre || ' ' || p.apellido as tecnico,
    eu.id_servicio,
    s.estado as estado_servicio,
    eu.latitud,
    eu.longitud,
    eu.timestamp,
    AGE(NOW(), eu.timestamp) as antiguedad
FROM empleado e
JOIN usuario u ON u.id = e.id_usuario
JOIN persona p ON p.id = u.id_persona
LEFT JOIN empleado_ubicacion eu ON eu.id_empleado = e.id AND eu.activa = true
LEFT JOIN servicio s ON s.id = eu.id_servicio
WHERE eu.id IS NOT NULL
ORDER BY eu.timestamp DESC;

-- ============================================================================
-- RESULTADO ESPERADO
-- ============================================================================
/*
Después de ejecutar este script:

✅ Todas las ubicaciones sin id_servicio están desactivadas
✅ Todas las ubicaciones de servicios finalizados/cancelados están desactivadas
✅ Cada técnico tiene máximo 1 ubicación activa por servicio
✅ Solo hay ubicaciones activas para servicios en estados activos

Esto garantiza que el cliente siempre vea la ubicación correcta del técnico
para el servicio actual.
*/
