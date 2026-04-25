"""Esquemas Pydantic para autenticacion."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    """Datos de entrada para el endpoint de login."""

    email: EmailStr
    password: Optional[str] = Field(default=None, min_length=1)
    contrasena: Optional[str] = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validar_password(self) -> "LoginRequest":
        """Exige password o contrasena para permitir compatibilidad de clientes."""
        if not self.password and not self.contrasena:
            raise ValueError("Debes enviar password o contrasena")
        return self

    @property
    def password_plana(self) -> str:
        """Devuelve la contrasena recibida por cualquiera de las dos claves."""
        return self.password or self.contrasena or ""


class LoginResponse(BaseModel):
    """Respuesta del login para que frontend seleccione pantalla por rol."""

    usuario_id: int
    nombre: str
    email: EmailStr
    rol: str
    access_token: str
    token_type: str = "bearer"
    requiere_cambio_contrasena: bool = False
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    """Datos de alta para crear una cuenta con rol especifico."""

    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    rol: str = Field(..., min_length=2, max_length=50)

    model_config = ConfigDict(extra="forbid")


class RegisterProfesionalRequest(BaseModel):
    """Alta privada para especialistas mediante clave de invitacion."""

    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    rol: str = Field(..., min_length=3, max_length=50)
    clave_registro: str = Field(..., min_length=6, max_length=120)

    model_config = ConfigDict(extra="forbid")


class RegisterResponse(BaseModel):
    """Respuesta de registro con sesion iniciada."""

    usuario_id: int
    nombre: str
    email: EmailStr
    rol: str
    access_token: str
    token_type: str = "bearer"
    requiere_cambio_contrasena: bool = False
    contrasena_temporal: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Datos para cambiar la contrasena desde una sesion autenticada."""

    nueva_password: str = Field(..., min_length=8, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ChangePasswordResponse(BaseModel):
    """Respuesta del cambio de contrasena."""

    detail: str
    requiere_cambio_contrasena: bool = False


class MeResponse(BaseModel):
    """Perfil basico del usuario autenticado."""

    usuario_id: int
    nombre: str
    email: EmailStr
    rol: str
    requiere_cambio_contrasena: bool = False


class RolOption(BaseModel):
    """Rol disponible para pantalla de registro."""

    id: int
    nombre: str


class ResetPasswordRequest(BaseModel):
    """Datos para restablecer la contrasena de un usuario existente."""

    email: EmailStr
    nueva_password: str = Field(..., min_length=8, max_length=100)

    model_config = ConfigDict(extra="forbid")
