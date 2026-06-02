"""simplify empleado estado

Revision ID: simplify_empleado_estado
Revises: e3a8b12c6d45
Create Date: 2026-05-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'simplify_empleado_estado'
down_revision = '75d50c36d769'
branch_label = None
depends_on = None


def upgrade():
    """
    Simplifica el enum EstadoEmpleado de 4 valores a 3:
    - Elimina el estado 'activo'
    - Convierte todos los empleados con estado 'activo' a 'disponible'
    - Mantiene: disponible, en_servicio, suspendido
    """
    
    # Paso 1: Actualizar todos los registros con estado 'activo' a 'disponible'
    op.execute("""
        UPDATE empleado 
        SET estado = 'disponible' 
        WHERE estado = 'activo'
    """)
    
    # Paso 2: Crear el nuevo tipo enum sin 'activo'
    op.execute("ALTER TYPE estadoempleado RENAME TO estadoempleado_old")
    
    # Crear el nuevo enum
    op.execute("CREATE TYPE estadoempleado AS ENUM ('disponible', 'en_servicio', 'suspendido')")
    
    # Paso 3: Alterar la columna para usar el nuevo tipo
    op.execute("""
        ALTER TABLE empleado 
        ALTER COLUMN estado TYPE estadoempleado 
        USING estado::text::estadoempleado
    """)
    
    # Paso 4: Eliminar el tipo antiguo
    op.execute("DROP TYPE estadoempleado_old")


def downgrade():
    """
    Revierte el cambio, restaurando el estado 'activo'
    """
    
    # Paso 1: Crear el tipo enum antiguo con 'activo'
    op.execute("ALTER TYPE estadoempleado RENAME TO estadoempleado_new")
    
    # Crear el enum antiguo
    op.execute("CREATE TYPE estadoempleado AS ENUM ('activo', 'disponible', 'en_servicio', 'suspendido')")
    
    # Paso 2: Alterar la columna para usar el tipo antiguo
    op.execute("""
        ALTER TABLE empleado 
        ALTER COLUMN estado TYPE estadoempleado 
        USING estado::text::estadoempleado
    """)
    
    # Paso 3: Eliminar el tipo nuevo
    op.execute("DROP TYPE estadoempleado_new")
    
    # Nota: No podemos saber qué empleados eran 'activo' vs 'disponible' originalmente,
    # así que todos quedan como 'disponible' después del downgrade
