from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash
from app.crud import (
    usuario as crud_usuario,
    persona as crud_persona
)
from app.models import Persona, Usuario
from typing import Optional, Dict, Any
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    CIDuplicatedError,
    UsernameTakenError,
    PersonaNotFoundError,
)

async def create_persona(
    db: AsyncSession,
    email: str,
    data: Optional[Dict[str, Any]] = None
) -> Persona:
    """
    Crea una nueva persona con email y datos opcionales.
    Valida que el email no exista y que el CI (si se proporciona) sea único.
    """
    # Verificar email único
    existing = await crud_persona.get_by_email(db, email)
    if existing:
        raise EmailAlreadyRegisteredError()
    # Preparar datos de persona
    persona_data = {"email": email}
    if data:
        # Si hay CI, verificar unicidad antes de crear
        ci = data.get("ci")
        complemento = data.get("complemento")
        if ci:
            existing_ci = await crud_persona.get_by_ci_complemento(db, ci, complemento)
            if existing_ci:
                raise CIDuplicatedError()
        # Agregar otros campos
        for key in ["nombre", "apellido_p", "apellido_m", "ci", "complemento", "telefono", "direccion"]:
            if key in data and data[key] is not None:
                persona_data[key] = data[key]
    nueva_persona = await crud_persona.create(db, persona_data)
    return nueva_persona

async def create_usuario_from_persona(
    db: AsyncSession,
    persona: Persona,
    username: str,
    password: str,
    url_img_perfil: Optional[str] = None
) -> Usuario:
    """Crea un usuario asociado a una persona existente. Valida username único."""
    existing = await crud_usuario.get_by_nombre(db, username)
    if existing:
        raise UsernameTakenError()
    hashed = get_password_hash(password)
    usuario_data = {
        "nombre": username,
        "contrasena": hashed,
        "url_img_perfil": url_img_perfil,
        "id_persona": persona.id
    }
    return await crud_usuario.create(db, usuario_data)

async def update_persona_data(
    db: AsyncSession,
    persona: Persona,
    data: dict
) -> Persona:
    """Actualiza solo los campos no nulos de persona"""
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        return persona
    # Validar unicidad de CI (si se está actualizando)
    if "ci" in update_data:
        ci = update_data["ci"]
        complemento = update_data.get("complemento")
        # Buscar otra persona con el mismo CI+complemento
        existing = await crud_persona.get_by_ci_complemento(db, ci, complemento)
        if existing and existing.id != persona.id:
            raise CIDuplicatedError()
    persona = await crud_persona.update(db, persona, update_data)
    return persona

async def update_usuario_data(
    db: AsyncSession,
    usuario: Usuario,
    username: Optional[str] = None,
    url_img_perfil: Optional[str] = None
) -> Usuario:
    """
    Actualiza el nombre de usuario y/o la foto de perfil.
    """
    if username is not None and username != usuario.nombre:
        existing = await crud_usuario.get_by_nombre(db, username)
        if existing and existing.id != usuario.id:
            raise UsernameTakenError()
        usuario.nombre = username
    if url_img_perfil is not None:
        usuario.url_img_perfil = url_img_perfil
    if username is not None or url_img_perfil is not None:
        await db.flush()
        await db.refresh(usuario)
    return usuario