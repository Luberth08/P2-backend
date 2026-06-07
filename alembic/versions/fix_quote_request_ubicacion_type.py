"""fix quote request ubicacion type

Revision ID: fix_quote_request_ubicacion_type
Revises: add_quote_tables
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fix_quote_request_ubicacion_type'
down_revision: Union[str, Sequence[str], None] = 'add_quote_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Cambiar la columna ubicacion de VARCHAR a Geography(POINT, 4326)
    op.execute("""
        ALTER TABLE quote_request 
        ALTER COLUMN ubicacion TYPE geography(POINT, 4326) 
        USING ubicacion::geography
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Revertir a VARCHAR
    op.execute("""
        ALTER TABLE quote_request 
        ALTER COLUMN ubicacion TYPE VARCHAR 
        USING ST_AsText(ubicacion)
    """)
