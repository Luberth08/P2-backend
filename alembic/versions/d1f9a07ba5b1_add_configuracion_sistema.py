"""add_configuracion_sistema

Revision ID: d1f9a07ba5b1
Revises: c2484a04b923
Create Date: 2026-04-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1f9a07ba5b1'
down_revision: Union[str, Sequence[str], None] = 'c2484a04b923'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'configuracion_sistema',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clave', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.Text(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clave')
    )
    op.create_index(op.f('ix_configuracion_sistema_id'), 'configuracion_sistema', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_configuracion_sistema_id'), table_name='configuracion_sistema')
    op.drop_table('configuracion_sistema')
