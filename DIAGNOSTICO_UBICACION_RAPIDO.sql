-- ============================================================================
-- DIAGNÓSTICO RÁPIDO: Ubicaciones del técnico
-- ============================================================================
-- Ejecuta esto para ver todas las ubicaciones guardadas
-- ============================================================================

-- Ver todas las ubicaciones activas (problema: puede haber de otros servicios)
SELECT 
    eu.id,
    eu.id_empleado,
    p.nombre || ' ' || p.apellido as tecnico,
    eu.id_servicio,
    s.estado as estado_servicio,
    eu.latitud,
    eu.longitud,
    eu.activa,
    eu.timestamp,
    AGE(NOW(), eu.timestamp) as antiguedad
FROM empleado_ubicacion eu
JOIN empleado e ON e.id = eu.id_empleado
JOIN usuario u ON u.id = e.id_usuario
JOIN persona p ON p.id = u.id_persona
LEFT JOIN servicio s ON s.id = eu.id_servicio
WHERE eu.activa = true
ORDER BY eu.timestamp DESC;

-- Ver el servicio activo del cliente (reemplaza id_persona con el tuyo)
-- SELECT 
--     s.id as servicio_id,
--     s.estado,
--     s.fecha,
--     COUNT(st.id_empleado) as tecnicos_asignados
-- FROM servicio s
-- JOIN solicitud_servicio ss ON ss.id = s.id_solicitud_servicio
-- JOIN diagnostico d ON d.id = ss.id_diagnostico
-- JOIN solicitud_diagnostico sd ON sd.id = d.id_solicitud_diagnostico
-- LEFT JOIN servicio_tecnico st ON st.id_servicio = s.id
-- WHERE sd.id_persona = XXX  -- REEMPLAZAR
--   AND s.estado IN ('creado', 'tecnico_asignado', 'en_camino', 'en_lugar', 'en_atencion')
-- GROUP BY s.id, s.estado, s.fecha
-- ORDER BY s.fecha DESC;

-- ============================================================================
-- PROBLEMA IDENTIFICADO:
-- ============================================================================
-- La función get_ubicacion_activa() busca:
--   WHERE id_empleado = X AND activa = true
--
-- Pero NO verifica que id_servicio coincida con el servicio actual.
-- Si el técnico tiene una ubicación activa de un servicio anterior,
-- el sistema devolverá esa ubicación en lugar de la del servicio actual.
--
-- SOLUCIÓN:
-- Modificar el endpoint para que también filtre por id_servicio
-- ============================================================================
