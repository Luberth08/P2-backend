from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# ---------- Request/Response para check-email ----------
class EmailCheckRequest(BaseModel):
    email: EmailStr

class EmailCheckResponse(BaseModel):
    exists: bool           # si la persona existe
    has_user: bool         # si la persona tiene un usuario asociado (con contraseña)

# ---------- Solicitar OTP ----------
class RequestOTPRequest(BaseModel):
    email: EmailStr

# ---------- Verificar OTP (para registro nuevo o login sin contraseña) ----------
class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    fcm_token: Optional[str] = None

# ---------- Login con contraseña ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    fcm_token: Optional[str] = None

# ---------- Respuesta común ----------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------- Para registro de usuario via web ----------
class WebRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    nombre: Optional[str] = None
    apellido_p: Optional[str] = None
    apellido_m: Optional[str] = None
    ci: Optional[str] = None
    complemento: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None

class RegisterInitRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    nombre: Optional[str] = None
    apellido_p: Optional[str] = None
    apellido_m: Optional[str] = None
    ci: Optional[str] = None
    complemento: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None

class RegisterCompleteRequest(BaseModel):
    email: EmailStr
    code: str