"""add_requiere_especialidad

Revision ID: e3a8b12c6d45
Revises: d1f9a07ba5b1
Create Date: 2026-04-23 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a8b12c6d45'
down_revision: Union[str, Sequence[str], None] = 'd1f9a07ba5b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'requiere_especialidad',
        sa.Column('id_categoria_incidente', sa.Integer(), nullable=False),
        sa.Column('id_especialidad', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_categoria_incidente'], ['categoria_incidente.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_especialidad'], ['especialidad.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_categoria_incidente', 'id_especialidad')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('requiere_especialidad')
