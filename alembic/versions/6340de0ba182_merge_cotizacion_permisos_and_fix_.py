"""merge cotizacion permisos and fix ubicacion

Revision ID: 6340de0ba182
Revises: add_cotizacion_permisos, fix_quote_request_ubicacion_type
Create Date: 2026-06-06 16:29:04.103454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6340de0ba182'
down_revision: Union[str, Sequence[str], None] = ('add_cotizacion_permisos', 'fix_quote_request_ubicacion_type')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
