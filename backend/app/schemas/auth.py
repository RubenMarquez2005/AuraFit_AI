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
    model_config = ConfigDict(from_attributes=True)
