import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_password
from app.crud import (
    persona as crud_persona,
    usuario as crud_usuario
)
from .session_service import create_token_and_session, invalidate_session
from .otp_service import get_otp_data, delete_otp, send_otp_email_safe
from app.schemas.auth import TokenResponse
from app.core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserAlreadyHasPasswordError,
    InvalidOTPError,
    InvalidOTPFlowError
)

logger = logging.getLogger(__name__)

async def authenticate_user(db: AsyncSession, email: str, password: str):
    """
    Verifica las credenciales y devuelve el usuario si son correctas.
    Lanza HTTPException 401 si no.
    """
    persona = await crud_persona.get_by_email(db, email)
    if not persona:
        raise InvalidCredentialsError()
    usuario = await crud_usuario.get_by_id_persona(db, persona.id)
    if not usuario or not verify_password(password, usuario.contrasena):
        raise InvalidCredentialsError()
    return usuario

async def start_conductor_login(db: AsyncSession, email: str) -> None:
    """
    Inicia el proceso de login de un conductor existente sin usuario:
    - Verifica que la persona exista y que no tenga usuario.
    - Envía un OTP con acción 'verify'.
    """
    persona = await crud_persona.get_by_email(db, email)
    if not persona:
        raise UserNotFoundError()
    usuario = await crud_usuario.get_by_id_persona(db, persona.id)
    if usuario:
        raise UserAlreadyHasPasswordError()
    await send_otp_email_safe(email, action="verify")
    logger.info(f"OTP de login enviado a {email}")

async def complete_conductor_login(db: AsyncSession, email: str, code: str, fcm_token: str = None) -> TokenResponse:
    """
    Completa el login de un conductor existente sin usuario:
    - Verifica el OTP.
    - Genera token y sesión.
    """
    record = get_otp_data(email)
    if not record or record["code"] != code:
        raise InvalidOTPError()
    if record["temp_data"].get("action") != "verify":
        raise InvalidOTPFlowError()

    # Verificar nuevamente que la persona exista y no tenga usuario (seguridad)
    persona = await crud_persona.get_by_email(db, email)
    if not persona:
        raise UserNotFoundError()
    usuario = await crud_usuario.get_by_id_persona(db, persona.id)
    if usuario:
        raise UserAlreadyHasPasswordError()

    delete_otp(email)

    # No usar db.begin() aquí porque la transacción ya está activa
    access_token = await create_token_and_session(db, email, fcm_token)
    await db.commit()
    logger.info(f"Conductor {email} ha iniciado sesión con OTP")
    return TokenResponse(access_token=access_token)

async def login_user(db: AsyncSession, email: str, password: str, fcm_token: str = None) -> TokenResponse:
    """
    Autentica al usuario, genera token y guarda sesión.
    """
    usuario = await authenticate_user(db, email, password)
    access_token = await create_token_and_session(db, email, fcm_token)
    await db.commit()
    logger.info(f"Usuario {usuario.id} ha iniciado sesión")
    return TokenResponse(access_token=access_token)

async def logout_user(db: AsyncSession, token: str) -> None:
    """
    Invalida la sesión activa del token.
    """
    # No usar db.begin() aquí porque la transacción ya está activa
    await invalidate_session(db, token)
    await db.commit()
    logger.info("Sesión cerrada")