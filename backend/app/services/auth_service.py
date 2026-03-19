"""Logica de autenticacion de usuarios."""

import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from app.models import Usuario
from app.config.settings import settings


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


def _b64url_encode(data: bytes) -> str:
    """Codifica bytes en base64 url-safe sin padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    """Decodifica base64 url-safe anadiendo padding si falta."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generar_token_usuario(usuario_id: int) -> str:
    """Genera token firmado con HMAC SHA256 para el usuario."""
    now = int(time.time())
    exp = now + int(settings.AUTH_TOKEN_EXP_MINUTES) * 60
    payload = {
        "sub": usuario_id,
        "iat": now,
        "exp": exp,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    firma = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_b64url_encode(firma)}"


def _leer_payload_token(token: str) -> Optional[dict]:
    """Valida firma/expiracion y devuelve payload del token."""
    try:
        payload_b64, firma_b64 = token.split(".", 1)
    except ValueError:
        return None

    firma_esperada = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    firma_recibida = _b64url_decode(firma_b64)

    if not hmac.compare_digest(firma_recibida, firma_esperada):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return None

    exp = payload.get("exp")
    sub = payload.get("sub")
    if not isinstance(exp, int) or not isinstance(sub, int):
        return None

    if int(time.time()) >= exp:
        return None

    return payload


def obtener_usuario_por_token(db: Session, token: str) -> Optional[Usuario]:
    """Obtiene el usuario autenticado a partir de un token Bearer valido."""
    payload = _leer_payload_token(token)
    if not payload:
        return None

    usuario_id = payload["sub"]
    return (
        db.query(Usuario)
        .options(joinedload(Usuario.rol))
        .filter(Usuario.id == usuario_id)
        .first()
    )
