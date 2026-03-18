"""Esquemas Pydantic para validacion y serializacion de datos."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time


# Esquemas de rol

class RolBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)


class RolCreate(RolBase):
    pass


class RolResponse(RolBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Esquemas de usuario

class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    rol_id: Optional[int] = None


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contrasena debe incluir al menos una mayuscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contrasena debe incluir al menos un numero")
        return v


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    rol_id: Optional[int] = None


class UsuarioResponse(UsuarioBase):
    id: int
    fecha_registro: datetime
    rol: Optional[RolResponse] = None
    model_config = ConfigDict(from_attributes=True)


# Esquemas de perfil de salud

class PerfilSaludBase(BaseModel):
    peso_actual: Optional[float] = Field(None, gt=0, le=300)
    altura: Optional[int] = Field(None, gt=0, le=250)  # cm
    imc_actual: Optional[float] = Field(None, gt=0, le=100)
    frecuencia_gym: Optional[str] = Field(None, max_length=50)
    hora_desayuno: Optional[time] = None
    hora_comida: Optional[time] = None
    hora_cena: Optional[time] = None
    momento_critico_picoteo: Optional[str] = Field(None, max_length=50)
    percepcion_corporal: Optional[str] = None


class PerfilSaludCreate(PerfilSaludBase):
    usuario_id: int


class PerfilSaludUpdate(PerfilSaludBase):
    pass


class PerfilSaludResponse(PerfilSaludBase):
    id: int
    usuario_id: int
    model_config = ConfigDict(from_attributes=True)


# Esquemas de registro diario

class RegistroDiarioBase(BaseModel):
    foto_comida_url: Optional[str] = Field(None, max_length=255)
    analisis_nutricional_ia: Optional[str] = None
    estado_animo_puntuacion: Optional[int] = Field(None, ge=1, le=10)
    sentimiento_detectado_ia: Optional[str] = Field(None, max_length=50)
    notas_diario: Optional[str] = None


class RegistroDiarioCreate(RegistroDiarioBase):
    usuario_id: int
    fecha: Optional[date] = None


class RegistroDiarioUpdate(RegistroDiarioBase):
    pass


class RegistroDiarioResponse(RegistroDiarioBase):
    id: int
    usuario_id: int
    fecha: date
    model_config = ConfigDict(from_attributes=True)


# Esquema compuesto

class UsuarioConDetalles(UsuarioResponse):
    """Usuario con su perfil y registros diarios relacionados."""
    perfil_salud: Optional[PerfilSaludResponse] = None
    registros_diarios: List[RegistroDiarioResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
