"""Logica de autenticacion de usuarios."""

from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from app.models import Usuario


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_contrasena(password_plana: str, password_hash: str) -> bool:
    """Compara la contrasena en texto plano contra el hash almacenado."""
    return pwd_context.verify(password_plana, password_hash)


def generar_hash_contrasena(password_plana: str) -> str:
    """Genera hash bcrypt de una contrasena."""
    return pwd_context.hash(password_plana)


def autenticar_usuario(db: Session, email: str, password_plana: str) -> Optional[Usuario]:
    """Busca usuario por email y valida su contrasena."""
    usuario = (
        db.query(Usuario)
        .options(joinedload(Usuario.rol))
        .filter(Usuario.email == email)
        .first()
    )

    if not usuario:
        return None

    if not verificar_contrasena(password_plana, usuario.password_hash):
        return None

    return usuario
