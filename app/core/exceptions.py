from fastapi import HTTPException, status

class AppException(HTTPException):
    """Excepción base de la aplicación."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

# Excepciones de autenticación y autorización
class InvalidCredentialsError(AppException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

class PersonaNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Persona no encontrada")

class UserNotFoundError(AppException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

class UserAlreadyExistsError(AppException):
    def __init__(self, field: str = "email"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field.capitalize()} ya registrado")

class UserAlreadyHasPasswordError(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya tiene una contraseña asociada. Usa /login en lugar de OTP."
        )

class InvalidTokenError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

class PermissionDeniedError(AppException):
    def __init__(self, permiso: str = None):
        msg = f"Permiso '{permiso}' requerido" if permiso else "No tienes permiso para realizar esta acción"
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=msg)

# Excepciones de OTP
class OTPNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Código OTP no encontrado")

class OTPExpiredError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Código OTP expirado")

class OTPSendError(HTTPException):
    def __init__(self, detail: str = "Error al enviar el código"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class InvalidOTPError(AppException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Código OTP inválido o expirado")

class InvalidOTPFlowError(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flujo de OTP inválido. La acción no coincide con lo esperado."
        )

# Excepciones de registro
class UsernameTakenError(AppException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de usuario ya en uso")

class EmailAlreadyRegisteredError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="El email ya está registrado")

class UsernameTakenError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="El nombre de usuario ya está en uso")

class CIDuplicatedError(AppException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe una persona con ese CI")

class RoleNotFoundError(HTTPException):
    def __init__(self, role_name: str):
        super().__init__(status_code=500, detail=f"Rol '{role_name}' no encontrado")