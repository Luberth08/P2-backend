"""add cotizacion permisos

Revision ID: add_cotizacion_permisos
Revises: 
Create Date: 2026-06-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cotizacion_permisos'
down_revision = 'create_tipo_servicio_table'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar permiso cotizacion:revisar
    op.execute("""
        INSERT INTO permiso (concepto) 
        VALUES ('cotizacion:revisar')
        ON CONFLICT (concepto) DO NOTHING
    """)
    
    # Agregar permiso cotizacion:responder
    op.execute("""
        INSERT INTO permiso (concepto) 
        VALUES ('cotizacion:responder')
        ON CONFLICT (concepto) DO NOTHING
    """)
    
    # Obtener IDs de los roles y permisos
    op.execute("""
        INSERT INTO rol_permiso (id_rol, id_permiso)
        SELECT r.id, p.id
        FROM rol r, permiso p
        WHERE r.nombre IN ('admin_taller', 'super_admin_taller')
        AND p.concepto IN ('cotizacion:revisar', 'cotizacion:responder')
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    # Eliminar el permiso de los roles
    op.execute("""
        DELETE FROM rol_permiso
        WHERE id_permiso IN (
            SELECT id FROM permiso WHERE concepto IN ('cotizacion:revisar', 'cotizacion:responder')
        )
    """)
    
    # Eliminar los permisos
    op.execute("""
        DELETE FROM permiso WHERE concepto IN ('cotizacion:revisar', 'cotizacion:responder')
    """)
