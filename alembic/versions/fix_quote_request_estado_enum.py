"""fix quote_request estado enum

Revision ID: fix_quote_request_estado_enum
Revises: add_cotizacion_permisos
Create Date: 2026-06-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_quote_request_estado_enum'
down_revision = 'add_cotizacion_permisos'
branch_labels = None
depends_on = None


def upgrade():
    # Crear el tipo enum para quote_request si no existe
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estadoquoterequest') THEN
                CREATE TYPE estadoquoterequest AS ENUM ('pendiente', 'con_respuesta', 'aceptada', 'rechazada', 'expirada');
            END IF;
        END
        $$
    """)
    
    # Actualizar datos inválidos en quote_request antes de convertir
    op.execute("""
        UPDATE quote_request 
        SET estado = 'pendiente' 
        WHERE estado NOT IN ('pendiente', 'con_respuesta', 'aceptada', 'rechazada', 'expirada')
    """)
    
    # Convertir la columna estado de VARCHAR a enum en quote_request
    op.execute("""
        ALTER TABLE quote_request 
        ALTER COLUMN estado TYPE estadoquoterequest 
        USING estado::text::estadoquoterequest
    """)
    
    # Crear el tipo enum para quote_response si no existe
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estadoquoteresponse') THEN
                CREATE TYPE estadoquoteresponse AS ENUM ('pendiente', 'respondida', 'rechazada', 'expirada');
            END IF;
        END
        $$
    """)
    
    # Actualizar datos inválidos en quote_response antes de convertir
    op.execute("""
        UPDATE quote_response 
        SET estado = 'pendiente' 
        WHERE estado NOT IN ('pendiente', 'respondida', 'rechazada', 'expirada')
    """)
    
    # Convertir la columna estado de VARCHAR a enum en quote_response
    op.execute("""
        ALTER TABLE quote_response 
        ALTER COLUMN estado TYPE estadoquoteresponse 
        USING estado::text::estadoquoteresponse
    """)


def downgrade():
    # Revertir la columna estado a VARCHAR en quote_response
    op.execute("""
        ALTER TABLE quote_response 
        ALTER COLUMN estado TYPE VARCHAR(50)
    """)
    
    # Revertir la columna estado a VARCHAR en quote_request
    op.execute("""
        ALTER TABLE quote_request 
        ALTER COLUMN estado TYPE VARCHAR(50)
    """)
    
    # Eliminar los tipos enum
    op.execute("DROP TYPE IF EXISTS estadoquoteresponse")
    op.execute("DROP TYPE IF EXISTS estadoquoterequest")
