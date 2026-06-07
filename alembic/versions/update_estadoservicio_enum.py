"""update estadoservicio enum

Revision ID: update_estadoservicio
Revises: simplify_empleado_estado
Create Date: 2026-06-04 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_estadoservicio'
down_revision: Union[str, Sequence[str], None] = 'simplify_empleado_estado'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Actualizar el enum estadoservicio para incluir los nuevos valores.
    
    PostgreSQL no permite modificar ENUMs directamente, así que necesitamos:
    1. Crear un nuevo ENUM con todos los valores
    2. Alterar la columna para usar el nuevo tipo
    3. Eliminar el ENUM antiguo
    """
    
    # Paso 1: Crear nuevo ENUM con todos los valores necesarios
    op.execute("""
        CREATE TYPE estadoservicio_new AS ENUM (
            'creado',
            'tecnico_asignado',
            'en_camino',
            'en_lugar',
            'en_atencion',
            'finalizado',
            'cancelado'
        )
    """)
    
    # Paso 2: Actualizar la columna estado en la tabla servicio
    # Primero, mapear valores antiguos a nuevos (si hay datos existentes)
    op.execute("""
        ALTER TABLE servicio 
        ALTER COLUMN estado TYPE estadoservicio_new 
        USING (
            CASE estado::text
                WHEN 'en_proceso' THEN 'en_atencion'::estadoservicio_new
                WHEN 'completado' THEN 'finalizado'::estadoservicio_new
                ELSE estado::text::estadoservicio_new
            END
        )
    """)
    
    # Paso 3: Actualizar la columna estado en historial_estados_servicio (si existe)
    # Verificar si la tabla existe primero
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'historial_estados_servicio'
            ) THEN
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
    """)
    
    # Paso 4: Eliminar el ENUM antiguo
    op.execute("DROP TYPE estadoservicio")
    
    # Paso 5: Renombrar el nuevo ENUM al nombre original
    op.execute("ALTER TYPE estadoservicio_new RENAME TO estadoservicio")


def downgrade() -> None:
    """
    Revertir a los valores antiguos del enum.
    """
    
    # Crear el ENUM antiguo
    op.execute("""
        CREATE TYPE estadoservicio_old AS ENUM (
            'creado',
            'en_proceso',
            'completado',
            'cancelado'
        )
    """)
    
    # Convertir la columna estado en servicio
    op.execute("""
        ALTER TABLE servicio 
        ALTER COLUMN estado TYPE estadoservicio_old 
        USING (
            CASE estado::text
                WHEN 'tecnico_asignado' THEN 'en_proceso'::estadoservicio_old
                WHEN 'en_camino' THEN 'en_proceso'::estadoservicio_old
                WHEN 'en_lugar' THEN 'en_proceso'::estadoservicio_old
                WHEN 'en_atencion' THEN 'en_proceso'::estadoservicio_old
                WHEN 'finalizado' THEN 'completado'::estadoservicio_old
                ELSE estado::text::estadoservicio_old
            END
        )
    """)
    
    # Convertir la columna estado en historial_estados_servicio (si existe)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'historial_estados_servicio'
            ) THEN
                ALTER TABLE historial_estados_servicio 
                ALTER COLUMN estado TYPE estadoservicio_old 
                USING (
                    CASE estado::text
                        WHEN 'tecnico_asignado' THEN 'en_proceso'::estadoservicio_old
                        WHEN 'en_camino' THEN 'en_proceso'::estadoservicio_old
                        WHEN 'en_lugar' THEN 'en_proceso'::estadoservicio_old
                        WHEN 'en_atencion' THEN 'en_proceso'::estadoservicio_old
                        WHEN 'finalizado' THEN 'completado'::estadoservicio_old
                        ELSE estado::text::estadoservicio_old
                    END
                );
            END IF;
        END $$;
    """)
    
    # Eliminar el ENUM nuevo
    op.execute("DROP TYPE estadoservicio")
    
    # Renombrar el ENUM antiguo
    op.execute("ALTER TYPE estadoservicio_old RENAME TO estadoservicio")

