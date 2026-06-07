"""add_sync_tables

Revision ID: add_sync_tables
Revises: 0d77f7024a05
Create Date: 2026-06-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_sync_tables'
down_revision: Union[str, Sequence[str], None] = 'merge_heads_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Crear tabla sync_queue
    op.create_table(
        'sync_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.Enum('create', 'update', 'delete', name='operationtype'), nullable=False),
        sa.Column('entity_type', sa.Enum('solicitud_servicio', 'diagnostico', 'servicio', 'incidente', name='entitytype'), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('client_sync_id', sa.String(length=255), nullable=False),
        sa.Column('payload', postgresql.JSON(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='syncstatus'), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('processed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_sync_id')
    )
    op.create_index(op.f('ix_sync_queue_id'), 'sync_queue', ['id'], unique=False)
    op.create_index('ix_sync_queue_client_sync_id', 'sync_queue', ['client_sync_id'], unique=True)
    op.create_index('ix_sync_queue_status', 'sync_queue', ['status'], unique=False)
    op.create_index('ix_sync_queue_user_id', 'sync_queue', ['user_id'], unique=False)
    
    # Crear tabla sync_log
    op.create_table(
        'sync_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.Enum('create', 'update', 'delete', name='operationtype'), nullable=False),
        sa.Column('entity_type', sa.Enum('solicitud_servicio', 'diagnostico', 'servicio', 'incidente', name='entitytype'), nullable=False),
        sa.Column('client_sync_id', sa.String(length=255), nullable=False),
        sa.Column('server_entity_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('client_timestamp', sa.TIMESTAMP(), nullable=True),
        sa.Column('server_timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_log_id'), 'sync_log', ['id'], unique=False)
    op.create_index('ix_sync_log_client_sync_id', 'sync_log', ['client_sync_id'], unique=False)
    op.create_index('ix_sync_log_user_id', 'sync_log', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sync_log_user_id', table_name='sync_log')
    op.drop_index('ix_sync_log_client_sync_id', table_name='sync_log')
    op.drop_index(op.f('ix_sync_log_id'), table_name='sync_log')
    op.drop_table('sync_log')
    
    op.drop_index('ix_sync_queue_user_id', table_name='sync_queue')
    op.drop_index('ix_sync_queue_status', table_name='sync_queue')
    op.drop_index('ix_sync_queue_client_sync_id', table_name='sync_queue')
    op.drop_index(op.f('ix_sync_queue_id'), table_name='sync_queue')
    op.drop_table('sync_queue')
