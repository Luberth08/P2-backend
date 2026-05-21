import os
import uuid
from typing import Dict, Any, Optional
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import persona as crud_persona, usuario as crud_usuario
from app.core.security import get_password_hash
from app.core.exceptions import InvalidOTPError
from app.services.user_service import update_persona_data, update_usuario_data, create_usuario_from_persona
from app.services.otp_service import get_otp_data, delete_otp, send_otp_email_safe
from app.crud.crud_sesion import sesion as crud_sesion
from app.core.config import settings

async def update_profile(
    db: AsyncSession,
    persona_id: int,
    data: Dict[str, Any],
    username: Optional[str] = None,
    url_img_perfil: Optional[str] = None
) -> Dict[str, Any]:
    """
    Actualiza los datos de perfil (persona y usuario) dentro de una transacción.
    Retorna un diccionario con la persona y el usuario actualizados.
    """
    # Obtener la persona
    persona = await crud_persona.get(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Obtener el usuario asociado (puede ser None)
    usuario = await crud_usuario.get_by_id_persona(db, persona_id)
    
    # Actualizar campos de persona (si hay)
    if data:
        persona = await update_persona_data(db, persona, data)
    
    # Actualizar usuario (si existe y se proporcionaron campos)
    if usuario:
        if username is not None or url_img_perfil is not None:
            usuario = await update_usuario_data(db, usuario, username, url_img_perfil)
    
    await db.commit()

    return {"persona": persona, "usuario": usuario}

async def create_usuario(
    db: AsyncSession,
    persona_id: int,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Crea un usuario para una persona que aún no tiene usuario.
    """
    # Obtener la persona
    persona = await crud_persona.get(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Verificar que no tenga usuario ya
    existing_usuario = await crud_usuario.get_by_id_persona(db, persona_id)
    if existing_usuario:
        raise HTTPException(status_code=400, detail="Esta persona ya tiene un usuario")
    
    # Crear el usuario
    usuario = await create_usuario_from_persona(db, persona, username, password)
    await db.commit()
    
    return {"persona": persona, "usuario": usuario}

async def request_password_change_otp(
    db: AsyncSession,
    email: str
) -> None:
    """
    Envía un OTP al correo del usuario para iniciar el proceso de cambio de contraseña.
    Verifica que el email exista y tenga usuario asociado.
    """
    persona = await crud_persona.get_by_email(db, email)
    if not persona:
        raise HTTPException(status_code=404, detail="Email no registrado")
    usuario = await crud_usuario.get_by_id_persona(db, persona.id)
    if not usuario:
        raise HTTPException(status_code=400, detail="Este email no tiene una cuenta de usuario (sin contraseña)")
    
    # Enviar OTP con acción "password_change"
    await send_otp_email_safe(email, action="password_change")

async def change_password(
    db: AsyncSession,
    email: str,
    code: str,
    new_password: str
) -> None:
    """
    Cambia la contraseña del usuario después de verificar el OTP.
    Invalida todas las sesiones activas del usuario.
    """
    # 1. Verificar el OTP
    record = get_otp_data(email)
    if not record or record["code"] != code:
        raise InvalidOTPError()
    if record["temp_data"].get("action") != "password_change":
        raise HTTPException(status_code=400, detail="Flujo OTP inválido")
    
    # 2. Obtener persona y usuario
    persona = await crud_persona.get_by_email(db, email)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    usuario = await crud_usuario.get_by_id_persona(db, persona.id)
    if not usuario:
        raise HTTPException(status_code=400, detail="El usuario no tiene cuenta de acceso")
    
    # 3. Actualizar contraseña
    hashed = get_password_hash(new_password)
    usuario.contrasena = hashed
    db.add(usuario)
    await db.commit()
    
    # 4. Invalidar todas las sesiones activas
    await crud_sesion.invalidate_all_for_persona(db, persona.id)
    
    # 5. Eliminar el OTP usado
    delete_otp(email)

async def upload_profile_picture(
    db: AsyncSession,
    persona_id: int,
    file: UploadFile
) -> str:
    """
    Guarda la foto de perfil en el sistema de archivos y actualiza la URL en la base de datos.
    Retorna la URL pública de la imagen.
    """
    # Validar tipo de archivo (más flexible para aceptar variaciones de JPEG)
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/pjpeg"]
    file_extension = file.filename.split(".")[-1].lower() if file.filename else ""
    allowed_extensions = ["jpg", "jpeg", "png"]
    
    # Validar por MIME type o por extensión
    is_valid = (
        file.content_type in allowed_types or 
        file_extension in allowed_extensions or
        (file.content_type and file.content_type.startswith("image/"))
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no permitido. Use JPEG, JPG o PNG. Tipo recibido: {file.content_type}"
        )
    
    # Obtener usuario actual
    usuario = await crud_usuario.get_by_id_persona(db, persona_id)
    if not usuario:
        raise HTTPException(404, "Usuario no encontrado")

    # Eliminar foto anterior si existe
    if usuario.url_img_perfil:
        try:
            relative_path = usuario.url_img_perfil.replace(settings.BASE_URL, "")
            if relative_path.startswith("/staticuploads//"):
                filename = relative_path.split("/")[-1]
                file_path = os.path.join("static/uploads", filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            # Si falla la eliminación, solo registra el error, no impide la subida
            print(f"Error al eliminar foto anterior: {e}")

    # Normalizar extensión (convertir jpg a jpeg si es necesario)
    if file_extension == "jpg":
        extension = "jpeg"
    elif file_extension in allowed_extensions:
        extension = file_extension
    else:
        # Si no hay extensión válida, usar jpeg por defecto
        extension = "jpeg"
    
    # Generar nombre único
    unique_name = f"{uuid.uuid4()}.{extension}"
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)
    
    # Guardar archivo
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al guardar la imagen")
    
    # Construir URL pública
    photo_url = f"{settings.BASE_URL}/static/uploads/{unique_name}"
    
    # Actualizar en la base de datos
    usuario = await crud_usuario.get_by_id_persona(db, persona_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    await update_usuario_data(db, usuario, url_img_perfil=photo_url)
    await db.commit()
    
    return photo_url

async def delete_profile_picture(
    db: AsyncSession,
    persona_id: int
) -> None:
    """
    Elimina la foto de perfil del usuario: borra el archivo físico y pone la URL a NULL.
    """
    usuario = await crud_usuario.get_by_id_persona(db, persona_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.url_img_perfil:
        # Eliminar archivo físico
        try:
            relative_path = usuario.url_img_perfil.replace(settings.BASE_URL, "")
            if relative_path.startswith("/static/uploads/"):
                filename = relative_path.split("/")[-1]
                file_path = os.path.join("static/uploads", filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"Error al eliminar archivo de foto: {e}")

        # Actualizar base de datos directamente
        usuario.url_img_perfil = None
        await db.commit()   # Confirma el cambio