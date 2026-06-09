-- ============================================================================
-- DIAGNÓSTICO SIMPLE: ¿Por qué no aparecen talleres?
-- ============================================================================
-- Reemplaza 22 con tu ID de diagnóstico
-- ============================================================================

-- PASO 1: Incidentes del diagnóstico
SELECT '=== PASO 1: Incidentes del Diagnóstico ===' as paso;
SELECT 
    i.id,
    i.descripcion,
    i.id_tipo_incidente,
    ti.nombre as tipo_incidente
FROM incidente i
LEFT JOIN tipo_incidente ti ON ti.id = i.id_tipo_incidente
WHERE i.id_diagnostico = 22;

-- PASO 2: Categorías de esos tipos de incidentes
SELECT '=== PASO 2: Categorías de Incidentes ===' as paso;
SELECT DISTINCT
    ti.id as tipo_id,
    ti.nombre as tipo_nombre,
    ti.id_categoria_incidente,
    ci.nombre as categoria_nombre
FROM incidente i
JOIN tipo_incidente ti ON ti.id = i.id_tipo_incidente
LEFT JOIN categoria_incidente ci ON ci.id = ti.id_categoria_incidente
WHERE i.id_diagnostico = 22;

-- PASO 3: Especialidades requeridas por esas categorías
SELECT '=== PASO 3: Especialidades Requeridas ===' as paso;
SELECT DISTINCT
    e.id as especialidad_id,
    e.nombre as especialidad_nombre
FROM incidente i
JOIN tipo_incidente ti ON ti.id = i.id_tipo_incidente
JOIN categoria_incidente ci ON ci.id = ti.id_categoria_incidente
JOIN requiere_especialidad re ON re.id_categoria_incidente = ci.id
JOIN especialidad e ON e.id = re.id_especialidad
WHERE i.id_diagnostico = 22;

-- PASO 4: Talleres activos
SELECT '=== PASO 4: Talleres Activos ===' as paso;
SELECT 
    id,
    nombre,
    estado,
    ubicacion IS NOT NULL as tiene_ubicacion
FROM taller
WHERE estado = 'activo';

-- PASO 5: Técnicos por taller con sus especialidades
SELECT '=== PASO 5: Técnicos y Especialidades por Taller ===' as paso;
SELECT 
    t.id as taller_id,
    t.nombre as taller,
    e.id as empleado_id,
    e.nombre || ' ' || e.apellido as tecnico,
    esp.id as especialidad_id,
    esp.nombre as especialidad
FROM taller t
JOIN empleado e ON e.id_taller = t.id
JOIN tecnico_especialidad te ON te.id_empleado = e.id
JOIN especialidad esp ON esp.id = te.id_especialidad
WHERE t.estado = 'activo'
ORDER BY t.id, e.id;

-- PASO 6: Distancia máxima configurada
SELECT '=== PASO 6: Distancia Máxima ===' as paso;
SELECT clave, valor
FROM configuracion_sistema
WHERE clave = 'distancia_maxima_taller_km';

-- PASO 7: Ubicación del cliente
SELECT '=== PASO 7: Ubicación del Cliente ===' as paso;
SELECT 
    sd.id,
    sd.id_persona,
    ST_Y(sd.ubicacion::geometry) as latitud,
    ST_X(sd.ubicacion::geometry) as longitud,
    sd.ubicacion IS NOT NULL as tiene_ubicacion
FROM solicitud_diagnostico sd
JOIN diagnostico d ON d.id_solicitud_diagnostico = sd.id
WHERE d.id = 22;

-- RESUMEN: ¿Por qué no encuentra talleres?
SELECT '=== RESUMEN FINAL ===' as paso;

-- Contar cada paso del flujo
WITH 
incidentes AS (
    SELECT COUNT(*) as total
    FROM incidente WHERE id_diagnostico = 22
),
categorias AS (
    SELECT COUNT(DISTINCT ti.id_categoria_incidente) as total
    FROM incidente i
    JOIN tipo_incidente ti ON ti.id = i.id_tipo_incidente
    WHERE i.id_diagnostico = 22
      AND ti.id_categoria_incidente IS NOT NULL
),
especialidades_requeridas AS (
    SELECT COUNT(DISTINCT re.id_especialidad) as total
    FROM incidente i
    JOIN tipo_incidente ti ON ti.id = i.id_tipo_incidente
    JOIN requiere_especialidad re ON re.id_categoria_incidente = ti.id_categoria_incidente
    WHERE i.id_diagnostico = 22
),
talleres_activos AS (
    SELECT COUNT(*) as total
    FROM taller WHERE estado = 'activo'
),
talleres_con_ubicacion AS (
    SELECT COUNT(*) as total
    FROM taller WHERE estado = 'activo' AND ubicacion IS NOT NULL
),
tecnicos_con_especialidades AS (
    SELECT COUNT(DISTINCT te.id_empleado) as total
    FROM taller t
    JOIN empleado e ON e.id_taller = t.id
    JOIN tecnico_especialidad te ON te.id_empleado = e.id
    WHERE t.estado = 'activo'
)
SELECT 
    (SELECT total FROM incidentes) as "1_incidentes",
    (SELECT total FROM categorias) as "2_categorias",
    (SELECT total FROM especialidades_requeridas) as "3_especialidades_requeridas",
    (SELECT total FROM talleres_activos) as "4_talleres_activos",
    (SELECT total FROM talleres_con_ubicacion) as "5_talleres_con_ubicacion",
    (SELECT total FROM tecnicos_con_especialidades) as "6_tecnicos_con_especialidades";

-- ============================================================================
-- INTERPRETACIÓN DE RESULTADOS
-- ============================================================================
/*
Si "1_incidentes" = 0:
  → El diagnóstico no tiene incidentes detectados
  → SOLUCIÓN: El sistema de IA debería crear incidentes al generar el diagnóstico

Si "2_categorias" = 0:
  → Los tipos de incidentes no tienen categoría asignada
  → SOLUCIÓN: Asignar categorías a los tipos de incidentes en la BD

Si "3_especialidades_requeridas" = 0:
  → Las categorías no tienen especialidades asociadas
  → SOLUCIÓN: Llenar la tabla "requiere_especialidad"
  → O cambiar lógica para aceptar cualquier taller (sin filtro de especialidades)

Si "4_talleres_activos" = 0:
  → No hay talleres activos
  → SOLUCIÓN: UPDATE taller SET estado = 'activo'

Si "5_talleres_con_ubicacion" = 0:
  → Los talleres no tienen ubicación GPS
  → SOLUCIÓN: UPDATE taller SET ubicacion = ST_GeogFromText('POINT(lon lat)')

Si "6_tecnicos_con_especialidades" = 0:
  → Los técnicos no tienen especialidades asignadas
  → SOLUCIÓN: Ir al panel web → Gestión de Técnicos → Asignar especialidades
*/
