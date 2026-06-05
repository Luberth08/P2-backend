"""merge heads for notifications

Revision ID: merge_heads_notifications
Revises: f4b9c23d7e56, simplify_empleado_estado
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_heads_notifications'
down_revision: Union[str, Sequence[str], None] = ('f4b9c23d7e56', 'simplify_empleado_estado')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge migration - no changes needed
    pass


def downgrade() -> None:
    # Merge migration - no changes needed
    pass
