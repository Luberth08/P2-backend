-- ============================================================================
-- DIAGNÓSTICO: ¿Por qué no se encuentran talleres cercanos?
-- ============================================================================
-- Reemplaza [ID_DIAGNOSTICO] con el ID real del diagnóstico
-- ============================================================================

\set id_diagnostico 22

-- PASO 1: Verificar el diagnóstico
SELECT 'PASO 1: Diagnóstico' as paso;
SELECT id, descripcion, fecha
FROM diagnostico
WHERE id = :id_diagnostico;

-- PASO 2: Ver solicitud de diagnóstico y ubicación del cliente
SELECT 'PASO 2: Solicitud y Ubicación del Cliente' as paso;
SELECT 
    sd.id,
    sd.id_persona as cliente_id,
    sd.estado,
    ST_AsText(sd.ubicacion) as ubicacion_cliente,
    ST_Y(sd.ubicacion::geometry) as latitud,
    ST_X(sd.ubicacion::geometry) as longitud
FROM solicitud_diagnostico sd
JOIN diagnostico d ON d.id_solicitud_diagnostico = sd.id
WHERE d.id = :id_diagnostico;

-- PASO 3: Especialidades requeridas
SELECT 'PASO 3: Especialidades Requeridas' as paso;
SELECT DISTINCT 
    e.id,
    e.nombre as especialidad
FROM tecnico_especialidad te
JOIN especialidad e ON e.id = te.id_especialidad
WHERE te.id_diagnostico = :id_diagnostico;

-- PASO 4: Distancia máxima configurada
SELECT 'PASO 4: Distancia Máxima Configurada' as paso;
SELECT clave, valor || ' km' as distancia_maxima
FROM configuracion_sistema
WHERE clave = 'distancia_maxima_taller_km';

-- PASO 5: TODOS los talleres
SELECT 'PASO 5: Todos los Talleres en el Sistema' as paso;
SELECT 
    id,
    nombre,
    estado,
    CASE 
        WHEN ubicacion IS NULL THEN 'NO'
        ELSE 'SÍ'
    END as tiene_ubicacion,
    ST_Y(ubicacion::geometry) as latitud,
    ST_X(ubicacion::geometry) as longitud
FROM taller
ORDER BY id;

-- PASO 6: Talleres ACTIVOS
SELECT 'PASO 6: Talleres Activos' as paso;
SELECT COUNT(*) as total_activos
FROM taller
WHERE estado = 'activo';

SELECT id, nombre
FROM taller
WHERE estado = 'activo';

-- PASO 7: Talleres CERCANOS (dentro del rango)
SELECT 'PASO 7: Talleres Dentro del Rango de Distancia' as paso;

-- Primero obtener ubicación del cliente y distancia máxima
WITH cliente AS (
    SELECT 
        sd.ubicacion,
        COALESCE(
            (SELECT valor::numeric FROM configuracion_sistema WHERE clave = 'distancia_maxima_taller_km'),
            50
        ) * 1000 as distancia_max_metros
    FROM solicitud_diagnostico sd
    JOIN diagnostico d ON d.id_solicitud_diagnostico = sd.id
    WHERE d.id = :id_diagnostico
)
SELECT 
    t.id,
    t.nombre,
    ROUND(
        ST_Distance(t.ubicacion, c.ubicacion)::numeric / 1000, 
        2
    ) as distancia_km
FROM taller t, cliente c
WHERE t.estado = 'activo'
  AND t.ubicacion IS NOT NULL
  AND ST_DWithin(t.ubicacion, c.ubicacion, c.distancia_max_metros)
ORDER BY ST_Distance(t.ubicacion, c.ubicacion);

-- PASO 8: Técnicos por taller
SELECT 'PASO 8: Técnicos por Taller' as paso;
SELECT 
    t.id as taller_id,
    t.nombre as taller,
    COUNT(e.id) as num_tecnicos
FROM taller t
LEFT JOIN empleado e ON e.id_taller = t.id
LEFT JOIN usuario u ON u.id = e.id_usuario
LEFT JOIN rol_usuario ru ON ru.id_usuario = u.id
LEFT JOIN rol r ON r.id = ru.id_rol
WHERE t.estado = 'activo'
  AND (r.nombre = 'tecnico' OR r.nombre IS NULL)
GROUP BY t.id, t.nombre
ORDER BY t.id;

-- PASO 9: Especialidades de técnicos por taller
SELECT 'PASO 9: Especialidades de Técnicos por Taller' as paso;
SELECT 
    t.id as taller_id,
    t.nombre as taller,
    es.nombre as especialidad,
    COUNT(DISTINCT te.id_empleado) as num_tecnicos_con_especialidad
FROM taller t
JOIN empleado e ON e.id_taller = t.id
JOIN tecnico_especialidad te ON te.id_empleado = e.id
JOIN especialidad es ON es.id = te.id_especialidad
WHERE t.estado = 'activo'
  AND te.id_diagnostico IS NULL  -- Solo especialidades permanentes, no asignaciones temporales
GROUP BY t.id, t.nombre, es.id, es.nombre
ORDER BY t.id, es.nombre;

-- RESUMEN FINAL
SELECT 'RESUMEN FINAL' as paso;

WITH 
cliente AS (
    SELECT 
        sd.ubicacion,
        COALESCE(
            (SELECT valor::numeric FROM configuracion_sistema WHERE clave = 'distancia_maxima_taller_km'),
            50
        ) * 1000 as distancia_max_metros
    FROM solicitud_diagnostico sd
    JOIN diagnostico d ON d.id_solicitud_diagnostico = sd.id
    WHERE d.id = :id_diagnostico
),
especialidades_requeridas AS (
    SELECT ARRAY_AGG(DISTINCT id_especialidad) as ids
    FROM tecnico_especialidad
    WHERE id_diagnostico = :id_diagnostico
),
talleres_cercanos AS (
    SELECT t.id, t.nombre
    FROM taller t, cliente c
    WHERE t.estado = 'activo'
      AND t.ubicacion IS NOT NULL
      AND ST_DWithin(t.ubicacion, c.ubicacion, c.distancia_max_metros)
),
talleres_con_especialidades AS (
    SELECT DISTINCT tc.id, tc.nombre
    FROM talleres_cercanos tc
    JOIN empleado e ON e.id_taller = tc.id
    JOIN tecnico_especialidad te ON te.id_empleado = e.id
    CROSS JOIN especialidades_requeridas er
    WHERE te.id_diagnostico IS NULL  -- Solo especialidades permanentes
      AND (
          ARRAY_LENGTH(er.ids, 1) IS NULL  -- No se requieren especialidades específicas
          OR te.id_especialidad = ANY(er.ids)  -- O tiene alguna de las requeridas
      )
)
SELECT 
    (SELECT COUNT(*) FROM taller) as total_talleres,
    (SELECT COUNT(*) FROM taller WHERE estado = 'activo') as talleres_activos,
    (SELECT COUNT(*) FROM talleres_cercanos) as talleres_en_rango,
    (SELECT COUNT(*) FROM talleres_con_especialidades) as talleres_validos;

-- Ver cuáles talleres SON válidos
SELECT 'Talleres Válidos Encontrados' as resultado;
WITH 
cliente AS (
    SELECT 
        sd.ubicacion,
        COALESCE(
            (SELECT valor::numeric FROM configuracion_sistema WHERE clave = 'distancia_maxima_taller_km'),
            50
        ) * 1000 as distancia_max_metros
    FROM solicitud_diagnostico sd
    JOIN diagnostico d ON d.id_solicitud_diagnostico = sd.id
    WHERE d.id = :id_diagnostico
),
especialidades_requeridas AS (
    SELECT ARRAY_AGG(DISTINCT id_especialidad) as ids
    FROM tecnico_especialidad
    WHERE id_diagnostico = :id_diagnostico
),
talleres_cercanos AS (
    SELECT t.id, t.nombre,
           ROUND(ST_Distance(t.ubicacion, c.ubicacion)::numeric / 1000, 2) as distancia_km
    FROM taller t, cliente c
    WHERE t.estado = 'activo'
      AND t.ubicacion IS NOT NULL
      AND ST_DWithin(t.ubicacion, c.ubicacion, c.distancia_max_metros)
),
talleres_con_especialidades AS (
    SELECT DISTINCT tc.id, tc.nombre, tc.distancia_km
    FROM talleres_cercanos tc
    JOIN empleado e ON e.id_taller = tc.id
    JOIN tecnico_especialidad te ON te.id_empleado = e.id
    CROSS JOIN especialidades_requeridas er
    WHERE te.id_diagnostico IS NULL
      AND (
          ARRAY_LENGTH(er.ids, 1) IS NULL
          OR te.id_especialidad = ANY(er.ids)
      )
)
SELECT 
    id as taller_id,
    nombre as taller,
    distancia_km
FROM talleres_con_especialidades
ORDER BY distancia_km;

-- ============================================================================
-- SOLUCIONES SI NO ENCUENTRA TALLERES
-- ============================================================================

-- Si no hay talleres activos:
-- UPDATE taller SET estado = 'activo' WHERE id = [ID];

-- Si no hay talleres en rango:
-- UPDATE configuracion_sistema SET valor = '100' WHERE clave = 'distancia_maxima_taller_km';

-- Si no hay técnicos con especialidades:
-- Ver: Gestión de Técnicos en panel web → Asignar especialidades
