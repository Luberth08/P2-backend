import logging
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.constants import ROL_CONDUCTOR
from app.core.security import create_access_token
from app.crud import (
    persona as crud_persona,
    usuario as crud_usuario,
    rol_usuario as crud_rol_usuario,
    sesion as crud_sesion,
    dispositivo_usuario as crud_dispositivo
)
from app.core.exceptions import PersonaNotFoundError

logger = logging.getLogger(__name__)

async def _save_fcm_token(db: AsyncSession, persona_id: int, fcm_token: str = None):
    """Guarda el token FCM si es nuevo."""
    if fcm_token:
        dispositivos = await crud_dispositivo.get_by_persona(db, persona_id)
        if not any(d.token_fcm == fcm_token for d in dispositivos):
            await crud_dispositivo.create(db, {"token_fcm": fcm_token, "id_persona": persona_id})

async def create_token_and_session(db: AsyncSession, email: str, fcm_token: str = None) -> str:
    """
    Genera un token JWT, guarda la sesión en la tabla `sesion` y opcionalmente el token FCM.
    """
    # Buscar persona por email
    persona = await crud_persona.get_by_email(db, email)
    if not persona:
        raise PersonaNotFoundError()

    # Buscar usuario asociado
    usuario = await crud_usuario.get_by_id_persona(db, persona.id)
    # Determinar roles
    if usuario:
        roles = await crud_rol_usuario.get_roles_by_usuario(db, usuario.id)
        role_names = [r.rol.nombre for r in roles]
    else:
        role_names = [ROL_CONDUCTOR]

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {
        "sub": email,
        "persona_id": persona.id,
        "roles": role_names,
    }
    access_token, expires_at = create_access_token(data, expires_delta)
    await crud_sesion.create_session(db, access_token, expires_at, persona.id)
    await _save_fcm_token(db, persona.id, fcm_token)
    return access_token

async def invalidate_session(db: AsyncSession, token: str) -> None:
    """Invalida la sesión correspondiente al token."""
    sesion = await crud_sesion.get_by_token(db, token)
    if sesion and sesion.activa:
        sesion.activa = False
        await db.flush()
        logger.debug(f"Sesión {sesion.id} invalidada")