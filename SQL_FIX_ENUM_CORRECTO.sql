-- ============================================================================
-- SQL CORRECTO PARA ACTUALIZAR ENUM estadoservicio
-- ============================================================================
-- Este script soluciona el error del DEFAULT que no puede convertirse
-- ============================================================================

-- PASO 1: Crear el nuevo ENUM con todos los valores
CREATE TYPE estadoservicio_new AS ENUM (
    'creado',
    'tecnico_asignado',
    'en_camino',
    'en_lugar',
    'en_atencion',
    'finalizado',
    'cancelado'
);

-- PASO 2: Remover el DEFAULT de la columna estado en servicio
ALTER TABLE servicio 
ALTER COLUMN estado DROP DEFAULT;

-- PASO 3: Actualizar el tipo de la columna en servicio
ALTER TABLE servicio 
ALTER COLUMN estado TYPE estadoservicio_new 
USING (
    CASE estado::text
        WHEN 'en_proceso' THEN 'en_atencion'::estadoservicio_new
        WHEN 'completado' THEN 'finalizado'::estadoservicio_new
        ELSE estado::text::estadoservicio_new
    END
);

-- PASO 4: Restaurar el DEFAULT con el nuevo valor
ALTER TABLE servicio 
ALTER COLUMN estado SET DEFAULT 'creado'::estadoservicio_new;

-- PASO 5: Actualizar historial_estados_servicio (si existe)
-- Esta tabla probablemente no tiene DEFAULT, pero por si acaso
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'historial_estados_servicio'
    ) THEN
        -- Intentar quitar DEFAULT si existe
        BEGIN
            ALTER TABLE historial_estados_servicio 
            ALTER COLUMN estado DROP DEFAULT;
        EXCEPTION WHEN OTHERS THEN
            -- Ignorar si no existe DEFAULT
            NULL;
        END;
        
        -- Cambiar el tipo
        ALTER TABLE historial_estados_servicio 
        ALTER COLUMN estado TYPE estadoservicio_new 
        USING (
            CASE estado::text
                WHEN 'en_proceso' THEN 'en_atencion'::estadoservicio_new
                WHEN 'completado' THEN 'finalizado'::estadoservicio_new
                ELSE estado::text::estadoservicio_new
            END
        );
    END IF;
END $$;

-- PASO 6: Eliminar el ENUM antiguo
DROP TYPE estadoservicio;

-- PASO 7: Renombrar el nuevo ENUM al nombre original
ALTER TYPE estadoservicio_new RENAME TO estadoservicio;

-- PASO 8: Verificar que funcionó
SELECT enumlabel 
FROM pg_enum 
WHERE enumtypid = (
    SELECT oid 
    FROM pg_type 
    WHERE typname = 'estadoservicio'
)
ORDER BY enumsortorder;

-- Debería mostrar:
-- creado
-- tecnico_asignado
-- en_camino
-- en_lugar
-- en_atencion
-- finalizado
-- cancelado
