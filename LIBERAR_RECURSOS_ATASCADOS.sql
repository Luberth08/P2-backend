-- ============================================================================
-- SCRIPT: Liberar recursos atascados en estado "en_servicio"
-- ============================================================================
-- Este script libera técnicos y vehículos que están atascados en estado
-- "en_servicio" cuando el servicio al que están asignados ya finalizó o
-- fue cancelado.
--
-- USAR EN: Base de datos de producción (Render) o desarrollo (local)
-- ============================================================================

-- PASO 1: Ver cuántos recursos están atascados
-- ============================================================================

-- Técnicos atascados
SELECT 
    'TECNICOS ATASCADOS' as tipo,
    COUNT(*) as cantidad
FROM empleado e
JOIN servicio_tecnico st ON e.id = st.id_empleado
JOIN servicio s ON st.id_servicio = s.id
WHERE e.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado');

-- Vehículos atascados
SELECT 
    'VEHICULOS ATASCADOS' as tipo,
    COUNT(*) as cantidad
FROM vehiculo_taller vt
JOIN servicio_vehiculo sv ON vt.id = sv.id_vehiculo_taller
JOIN servicio s ON sv.id_servicio = s.id
WHERE vt.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado');


-- PASO 2: Ver detalles de los recursos atascados
-- ============================================================================

-- Detalles de técnicos atascados
SELECT 
    e.id as tecnico_id,
    e.nombre || ' ' || e.apellido as tecnico_nombre,
    e.estado as estado_tecnico,
    s.id as servicio_id,
    s.estado as estado_servicio,
    s.fecha as fecha_servicio,
    t.nombre as taller_nombre
FROM empleado e
JOIN servicio_tecnico st ON e.id = st.id_empleado
JOIN servicio s ON st.id_servicio = s.id
JOIN taller t ON e.id_taller = t.id
WHERE e.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado')
ORDER BY s.fecha DESC;

-- Detalles de vehículos atascados
SELECT 
    vt.id as vehiculo_id,
    vt.marca || ' ' || vt.modelo || ' (' || vt.matricula || ')' as vehiculo_info,
    vt.estado as estado_vehiculo,
    s.id as servicio_id,
    s.estado as estado_servicio,
    s.fecha as fecha_servicio,
    t.nombre as taller_nombre
FROM vehiculo_taller vt
JOIN servicio_vehiculo sv ON vt.id = sv.id_vehiculo_taller
JOIN servicio s ON sv.id_servicio = s.id
JOIN taller t ON vt.id_taller = t.id
WHERE vt.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado')
ORDER BY s.fecha DESC;


-- PASO 3: Liberar recursos atascados
-- ============================================================================
-- ⚠️ IMPORTANTE: Ejecutar estas consultas solo después de verificar los datos
-- ============================================================================

BEGIN;

-- Liberar técnicos atascados
UPDATE empleado e
SET estado = 'disponible'
FROM servicio_tecnico st
JOIN servicio s ON st.id_servicio = s.id
WHERE e.id = st.id_empleado
  AND e.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado');

-- Ver cuántos técnicos se liberaron
SELECT 'Técnicos liberados: ' || COUNT(*) as resultado
FROM empleado e
JOIN servicio_tecnico st ON e.id = st.id_empleado
JOIN servicio s ON st.id_servicio = s.id
WHERE e.estado = 'disponible'
  AND s.estado IN ('finalizado', 'cancelado');

-- Liberar vehículos atascados
UPDATE vehiculo_taller vt
SET estado = 'disponible'
FROM servicio_vehiculo sv
JOIN servicio s ON sv.id_servicio = s.id
WHERE vt.id = sv.id_vehiculo_taller
  AND vt.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado');

-- Ver cuántos vehículos se liberaron
SELECT 'Vehículos liberados: ' || COUNT(*) as resultado
FROM vehiculo_taller vt
JOIN servicio_vehiculo sv ON vt.id = sv.id_vehiculo_taller
JOIN servicio s ON sv.id_servicio = s.id
WHERE vt.estado = 'disponible'
  AND s.estado IN ('finalizado', 'cancelado');

-- Si todo está bien, hacer COMMIT
COMMIT;

-- Si algo salió mal, hacer ROLLBACK
-- ROLLBACK;


-- PASO 4: Verificar que se liberaron correctamente
-- ============================================================================

-- Debería dar 0 si todo salió bien
SELECT 
    'Técnicos aún atascados' as verificacion,
    COUNT(*) as cantidad
FROM empleado e
JOIN servicio_tecnico st ON e.id = st.id_empleado
JOIN servicio s ON st.id_servicio = s.id
WHERE e.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado');

SELECT 
    'Vehículos aún atascados' as verificacion,
    COUNT(*) as cantidad
FROM vehiculo_taller vt
JOIN servicio_vehiculo sv ON vt.id = sv.id_vehiculo_taller
JOIN servicio s ON sv.id_servicio = s.id
WHERE vt.estado = 'en_servicio'
  AND s.estado IN ('finalizado', 'cancelado');


-- ============================================================================
-- RESUMEN DE ESTADOS
-- ============================================================================

-- Estado de todos los técnicos
SELECT 
    estado,
    COUNT(*) as cantidad
FROM empleado
GROUP BY estado
ORDER BY cantidad DESC;

-- Estado de todos los vehículos
SELECT 
    estado,
    COUNT(*) as cantidad
FROM vehiculo_taller
GROUP BY estado
ORDER BY cantidad DESC;


-- ============================================================================
-- NOTAS
-- ============================================================================
-- 1. Este script debe ejecutarse en la base de datos de producción (Render)
--    o en desarrollo (local) según donde estén atascados los recursos.
--
-- 2. Si estás en Render:
--    - Ir a: https://dashboard.render.com
--    - Seleccionar tu base de datos
--    - Click en "Connect" → "External Connection"
--    - Usar psql o pgAdmin para conectar y ejecutar este script
--
-- 3. Si estás en local:
--    - Abrir pgAdmin o terminal
--    - Conectar a tu base de datos local
--    - Ejecutar este script
--
-- 4. El script usa transacciones (BEGIN/COMMIT) para seguridad.
--    Si algo sale mal, se puede hacer ROLLBACK.
--
-- 5. Después de ejecutar, reiniciar el backend para que tome el nuevo código
--    que libera recursos automáticamente.
-- ============================================================================
