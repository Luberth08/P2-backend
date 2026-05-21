"""update estadoservicio enum values

Revision ID: abc123update
Revises: 8573982aa8bc
Create Date: 2026-04-25 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123update'
down_revision: Union[str, Sequence[str], None] = '8573982aa8bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Recrear el enum estadoservicio con los nuevos valores
    # Como no hay datos, podemos recrear directamente
    
    # Crear el nuevo enum
    op.execute("CREATE TYPE estadoservicio_new AS ENUM ('creado', 'tecnico_asignado', 'en_camino', 'en_lugar', 'en_atencion', 'finalizado', 'cancelado')")
    
    # Remover el default temporalmente
    op.execute("ALTER TABLE servicio ALTER COLUMN estado DROP DEFAULT")
    
    # Cambiar la columna al nuevo enum
    op.execute("ALTER TABLE servicio ALTER COLUMN estado TYPE estadoservicio_new USING estado::text::estadoservicio_new")
    
    # Restaurar el default con el nuevo enum
    op.execute("ALTER TABLE servicio ALTER COLUMN estado SET DEFAULT 'creado'::estadoservicio_new")
    
    # Eliminar el enum anterior y renombrar
    op.execute("DROP TYPE estadoservicio")
    op.execute("ALTER TYPE estadoservicio_new RENAME TO estadoservicio")


def downgrade() -> None:
    """Downgrade schema."""
    # Revertir al enum original
    op.execute("CREATE TYPE estadoservicio_old AS ENUM ('creado', 'en_proceso', 'completado', 'cancelado')")
    
    # Cambiar la columna al enum anterior
    op.execute("ALTER TABLE servicio ALTER COLUMN estado TYPE estadoservicio_old USING 'creado'::estadoservicio_old")
    
    # Limpiar
    op.execute("DROP TYPE estadoservicio")
    op.execute("ALTER TYPE estadoservicio_old RENAME TO estadoservicio")