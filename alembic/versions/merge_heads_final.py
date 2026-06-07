"""merge heads

Revision ID: merge_heads_final
Revises: f4b9c23d7e56, update_estadoservicio
Create Date: 2026-06-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_heads_final'
down_revision: Union[str, Sequence[str], None] = ('f4b9c23d7e56', 'update_estadoservicio')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads - no schema changes needed."""
    pass


def downgrade() -> None:
    """Downgrade - no schema changes to revert."""
    pass
