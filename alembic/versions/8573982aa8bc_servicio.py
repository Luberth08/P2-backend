"""servicio

Revision ID: 8573982aa8bc
Revises: a9d4e56f8c32
Create Date: 2026-04-25 08:53:43.379789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8573982aa8bc'
down_revision: Union[str, Sequence[str], None] = 'a9d4e56f8c32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Crear tabla servicio
    op.create_table('servicio',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('estado', sa.Enum('creado', 'en_proceso', 'completado', 'cancelado', name='estadoservicio'), server_default='creado', nullable=False),
    sa.Column('id_taller', sa.Integer(), nullable=False),
    sa.Column('id_solicitud_servicio', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_solicitud_servicio'], ['solicitud_servicio.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['id_taller'], ['taller.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_solicitud_servicio', name='uq_servicio_solicitud')
    )
    op.create_index(op.f('ix_servicio_id'), 'servicio', ['id'], unique=False)
    op.create_index('ix_servicio_taller', 'servicio', ['id_taller'], unique=False)
    op.create_index('ix_servicio_estado', 'servicio', ['estado'], unique=False)
    op.create_index('ix_servicio_fecha', 'servicio', [sa.text('fecha DESC')], unique=False)
    
    # Crear tabla servicio_tecnico
    op.create_table('servicio_tecnico',
    sa.Column('id_servicio', sa.Integer(), nullable=False),
    sa.Column('id_empleado', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_empleado'], ['empleado.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['id_servicio'], ['servicio.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_servicio', 'id_empleado')
    )
    op.create_index('ix_servicio_tecnico_servicio', 'servicio_tecnico', ['id_servicio'], unique=False)
    op.create_index('ix_servicio_tecnico_empleado', 'servicio_tecnico', ['id_empleado'], unique=False)
    
    # Crear tabla servicio_vehiculo
    op.create_table('servicio_vehiculo',
    sa.Column('id_servicio', sa.Integer(), nullable=False),
    sa.Column('id_vehiculo_taller', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_servicio'], ['servicio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_vehiculo_taller'], ['vehiculo_taller.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id_servicio', 'id_vehiculo_taller')
    )
    op.create_index('ix_servicio_vehiculo_servicio', 'servicio_vehiculo', ['id_servicio'], unique=False)
    op.create_index('ix_servicio_vehiculo_vehiculo', 'servicio_vehiculo', ['id_vehiculo_taller'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar índices y tablas en orden inverso
    op.drop_index('ix_servicio_vehiculo_vehiculo', table_name='servicio_vehiculo')
    op.drop_index('ix_servicio_vehiculo_servicio', table_name='servicio_vehiculo')
    op.drop_table('servicio_vehiculo')
    
    op.drop_index('ix_servicio_tecnico_empleado', table_name='servicio_tecnico')
    op.drop_index('ix_servicio_tecnico_servicio', table_name='servicio_tecnico')
    op.drop_table('servicio_tecnico')
    
    op.drop_index('ix_servicio_fecha', table_name='servicio')
    op.drop_index('ix_servicio_estado', table_name='servicio')
    op.drop_index('ix_servicio_taller', table_name='servicio')
    op.drop_index(op.f('ix_servicio_id'), table_name='servicio')
    op.drop_table('servicio')
    
    # Eliminar tipo ENUM (comentado por seguridad)
    # op.execute('DROP TYPE IF EXISTS estadoservicio')
