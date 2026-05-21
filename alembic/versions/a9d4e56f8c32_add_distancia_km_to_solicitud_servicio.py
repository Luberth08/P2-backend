"""add distancia_km to solicitud_servicio

Revision ID: a9d4e56f8c32
Revises: f8b3c45d7e21
Create Date: 2026-04-25 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9d4e56f8c32'
down_revision: Union[str, Sequence[str], None] = '7ad5ca26661a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar columna distancia_km a solicitud_servicio
    op.add_column('solicitud_servicio', 
        sa.Column('distancia_km', sa.DECIMAL(precision=10, scale=2), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar columna distancia_km
    op.drop_column('solicitud_servicio', 'distancia_km')
