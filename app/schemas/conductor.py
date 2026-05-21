from pydantic import BaseModel, Field
from typing import Optional

# ---------- Completar perfil de conductor (creando un usuario) ----------
class CompleteProfileRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    url_img_perfil: Optional[str] = None
    # Datos personales (opcionales)
    nombre: Optional[str] = None
    apellido_p: Optional[str] = None
    apellido_m: Optional[str] = None
    ci: Optional[str] = None
    complemento: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None