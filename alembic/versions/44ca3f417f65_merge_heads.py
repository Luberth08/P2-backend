"""Merge heads

Revision ID: 44ca3f417f65
Revises: add_quote_tables, add_sync_tables
Create Date: 2026-06-06 00:54:55.199670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44ca3f417f65'
down_revision: Union[str, Sequence[str], None] = ('add_quote_tables', 'add_sync_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
