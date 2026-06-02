"""enhance_dispositivo_usuario_table

Revision ID: f4b9c23d7e56
Revises: e3a8b12c6d45
Create Date: 2026-04-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4b9c23d7e56'
down_revision: Union[str, Sequence[str], None] = 'e3a8b12c6d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Mejora la tabla dispositivo_usuario para soportar gestión avanzada de tokens FCM.
    
    Añade las siguientes columnas:
    - plataforma: Identifica el tipo de dispositivo (android, ios, web)
    - activo: Indica si el token está activo o ha sido desregistrado
    - fecha_registro: Timestamp de cuando se registró el token por primera vez
    - fecha_ultima_actividad: Timestamp de la última vez que el token fue usado
    
    También añade restricción UNIQUE en token_fcm e índices para optimizar consultas.
    """
    
    # Añadir columna plataforma para identificar el tipo de dispositivo
    op.add_column('dispositivo_usuario', 
                  sa.Column('plataforma', sa.String(length=20), nullable=True))
    
    # Añadir columna activo para marcar tokens inactivos sin eliminarlos
    op.add_column('dispositivo_usuario', 
                  sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'))
    
    # Añadir columna fecha_registro para rastrear cuando se registró el token
    op.add_column('dispositivo_usuario', 
                  sa.Column('fecha_registro', sa.DateTime(), nullable=False, 
                           server_default=sa.text('NOW()')))
    
    # Añadir columna fecha_ultima_actividad para gestión de tokens inactivos
    op.add_column('dispositivo_usuario', 
                  sa.Column('fecha_ultima_actividad', sa.DateTime(), nullable=False, 
                           server_default=sa.text('NOW()')))
    
    # Crear restricción UNIQUE en token_fcm para evitar duplicados
    # Primero verificar si ya existe la restricción
    op.create_unique_constraint('uq_dispositivo_usuario_token_fcm', 
                               'dispositivo_usuario', ['token_fcm'])
    
    # Crear índice en token_fcm para búsquedas rápidas por token
    op.create_index('idx_dispositivo_usuario_token_fcm', 
                   'dispositivo_usuario', ['token_fcm'], unique=False)
    
    # Crear índice en id_persona para búsquedas rápidas de tokens por usuario
    op.create_index('idx_dispositivo_usuario_id_persona', 
                   'dispositivo_usuario', ['id_persona'], unique=False)
    
    # Crear índice en activo para filtrar tokens activos/inactivos eficientemente
    op.create_index('idx_dispositivo_usuario_activo', 
                   'dispositivo_usuario', ['activo'], unique=False)


def downgrade() -> None:
    """
    Revierte los cambios realizados en la tabla dispositivo_usuario.
    
    Elimina todos los índices, restricciones y columnas añadidas.
    """
    
    # Eliminar índices en orden inverso
    op.drop_index('idx_dispositivo_usuario_activo', table_name='dispositivo_usuario')
    op.drop_index('idx_dispositivo_usuario_id_persona', table_name='dispositivo_usuario')
    op.drop_index('idx_dispositivo_usuario_token_fcm', table_name='dispositivo_usuario')
    
    # Eliminar restricción UNIQUE
    op.drop_constraint('uq_dispositivo_usuario_token_fcm', 'dispositivo_usuario', type_='unique')
    
    # Eliminar columnas en orden inverso
    op.drop_column('dispositivo_usuario', 'fecha_ultima_actividad')
    op.drop_column('dispositivo_usuario', 'fecha_registro')
    op.drop_column('dispositivo_usuario', 'activo')
    op.drop_column('dispositivo_usuario', 'plataforma')
