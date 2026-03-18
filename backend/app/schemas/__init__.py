"""Pydantic schemas module"""
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.users import (
    RolBase, RolCreate, RolResponse,
    UsuarioBase, UsuarioCreate, UsuarioUpdate, UsuarioResponse,
    PerfilSaludBase, PerfilSaludCreate, PerfilSaludUpdate, PerfilSaludResponse,
    RegistroDiarioBase, RegistroDiarioCreate, RegistroDiarioUpdate, RegistroDiarioResponse,
    UsuarioConDetalles
)

__all__ = [
    "LoginRequest", "LoginResponse",
    "RolBase", "RolCreate", "RolResponse",
    "UsuarioBase", "UsuarioCreate", "UsuarioUpdate", "UsuarioResponse",
    "PerfilSaludBase", "PerfilSaludCreate", "PerfilSaludUpdate", "PerfilSaludResponse",
    "RegistroDiarioBase", "RegistroDiarioCreate", "RegistroDiarioUpdate", "RegistroDiarioResponse",
    "UsuarioConDetalles"
]
