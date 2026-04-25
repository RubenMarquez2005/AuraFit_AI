"""Rutas de autenticacion."""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.config.settings import settings
from app.models import Rol, Usuario
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    ResetPasswordRequest,
    RegisterRequest,
    RegisterResponse,
    RolOption,
    RegisterProfesionalRequest,
)
from app.services.auth_service import (
    autenticar_usuario,
    generar_contrasena_temporal,
    generar_hash_contrasena,
    generar_token_usuario,
    obtener_usuario_por_token,
)


router = APIRouter(tags=["autenticacion"])

ROL_REGISTRO_PUBLICO = "cliente"
ROLES_PUBLICOS = {ROL_REGISTRO_PUBLICO}
ROLES_PROFESIONALES_ALTA_PRIVADA = {"nutricionista", "psicologo", "coach", "medico", "administrador"}


def _extraer_token_bearer(authorization: Optional[str]) -> str:
    """Extrae token desde cabecera Authorization en formato Bearer."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado",
        )

    esquema, _, token = authorization.partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token invalido. Usa: Bearer <token>",
        )

    return token


def obtener_usuario_actual(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Usuario:
    """Resuelve el usuario autenticado a partir del Bearer token."""
    token = _extraer_token_bearer(authorization)
    usuario = obtener_usuario_por_token(db, token)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        )

    return usuario


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

    access_token = generar_token_usuario(usuario.id)

    return LoginResponse(
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=usuario.rol.nombre,
        access_token=access_token,
        token_type="bearer",
        requiere_cambio_contrasena=bool(getattr(usuario, "cambio_contrasena_pendiente", False)),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Crea cuenta nueva como paciente y devuelve sesion iniciada."""
    rol_nombre = ROL_REGISTRO_PUBLICO

    rol = db.query(Rol).filter(Rol.nombre == rol_nombre).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol '{rol_nombre}' no esta disponible",
        )

    email = payload.email.strip().lower()
    existente = db.query(Usuario).filter(Usuario.email == email).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )

    usuario = Usuario(
        nombre=payload.nombre.strip(),
        email=email,
        password_hash=generar_hash_contrasena(payload.password),
        rol_id=rol.id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    access_token = generar_token_usuario(usuario.id)

    return RegisterResponse(
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=rol.nombre,
        access_token=access_token,
        token_type="bearer",
        requiere_cambio_contrasena=False,
    )


@router.post("/register-profesional", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_profesional(payload: RegisterProfesionalRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Crea cuenta de especialista solo si presenta clave privada de alta."""
    if payload.clave_registro.strip() != settings.PROFESSIONAL_REGISTRATION_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de registro profesional invalida",
        )

    rol_nombre = payload.rol.strip().lower()
    if rol_nombre not in ROLES_PROFESIONALES_ALTA_PRIVADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol profesional no permitido para alta privada",
        )

    rol = db.query(Rol).filter(Rol.nombre == rol_nombre).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol '{rol_nombre}' no esta disponible",
        )

    email = payload.email.strip().lower()
    existente = db.query(Usuario).filter(Usuario.email == email).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )

    contrasena_temporal = generar_contrasena_temporal()

    usuario = Usuario(
        nombre=payload.nombre.strip(),
        email=email,
        password_hash=generar_hash_contrasena(contrasena_temporal),
        rol_id=rol.id,
        cambio_contrasena_pendiente=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    access_token = generar_token_usuario(usuario.id)
    return RegisterResponse(
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=rol.nombre,
        access_token=access_token,
        token_type="bearer",
        requiere_cambio_contrasena=True,
        contrasena_temporal=contrasena_temporal,
    )


@router.get("/roles", response_model=list[RolOption])
def roles_disponibles(db: Session = Depends(get_db)) -> list[RolOption]:
    """Devuelve roles visibles para el formulario de registro."""
    roles = (
        db.query(Rol)
        .filter(Rol.nombre.in_(ROLES_PUBLICOS))
        .order_by(Rol.nombre.asc())
        .all()
    )
    return [RolOption(id=r.id, nombre=r.nombre) for r in roles]


@router.get("/me", response_model=MeResponse)
def me(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> MeResponse:
    """Devuelve datos basicos de la sesion actual."""
    rol_nombre = usuario_actual.rol.nombre if usuario_actual.rol else "cliente"
    return MeResponse(
        usuario_id=usuario_actual.id,
        nombre=usuario_actual.nombre,
        email=usuario_actual.email,
        rol=rol_nombre,
        requiere_cambio_contrasena=bool(getattr(usuario_actual, "cambio_contrasena_pendiente", False)),
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    payload: ChangePasswordRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    """Cambia la contrasena de la sesion autenticada y desactiva el primer acceso."""
    usuario_actual.password_hash = generar_hash_contrasena(payload.nueva_password)
    usuario_actual.cambio_contrasena_pendiente = False
    db.add(usuario_actual)
    db.commit()

    return ChangePasswordResponse(
        detail="Contrasena actualizada correctamente",
        requiere_cambio_contrasena=False,
    )


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Restablece la contrasena de un usuario existente identificado por email."""
    email = payload.email.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario:
      raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un usuario con ese email",
        )

    usuario.password_hash = generar_hash_contrasena(payload.nueva_password)
    usuario.cambio_contrasena_pendiente = False
    db.add(usuario)
    db.commit()

    return {"detail": "Contrasena actualizada correctamente"}
