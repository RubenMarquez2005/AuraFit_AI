"""Rutas de autenticacion."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import autenticar_usuario


router = APIRouter(tags=["autenticacion"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Autentica usuario por email y contrasena y devuelve su rol."""
    usuario = autenticar_usuario(db, payload.email, payload.password_plana)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not usuario.rol:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El usuario no tiene rol asignado",
        )

    return LoginResponse(
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=usuario.rol.nombre,
    )
