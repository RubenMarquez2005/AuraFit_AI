#!/usr/bin/env python3
"""Crea usuarios en la tabla usuarios con hash bcrypt y rol asociado."""

import argparse
import sys
from pathlib import Path

# Permite ejecutar el script como archivo directo desde backend/.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Rol, Usuario
from app.services.auth_service import generar_hash_contrasena

ROLES_VALIDOS = {"administrador", "cliente", "nutricionista", "psicologo", "coach"}


def crear_usuario(db: Session, nombre: str, email: str, password: str, rol_nombre: str) -> Usuario:
    """Inserta un usuario nuevo si email y rol son validos."""
    rol = db.query(Rol).filter(Rol.nombre == rol_nombre).first()
    if not rol:
        raise ValueError(f"Rol no encontrado: {rol_nombre}")

    existente = db.query(Usuario).filter(Usuario.email == email).first()
    if existente:
        raise ValueError(f"Ya existe un usuario con email: {email}")

    usuario = Usuario(
        nombre=nombre,
        email=email,
        password_hash=generar_hash_contrasena(password),
        rol_id=rol.id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de linea de comandos."""
    parser = argparse.ArgumentParser(description="Alta de usuario en AuraFit AI")
    parser.add_argument("--nombre", required=True, help="Nombre del usuario")
    parser.add_argument("--email", required=True, help="Email unico del usuario")
    parser.add_argument("--password", required=True, help="Contrasena en texto plano")
    parser.add_argument("--rol", required=True, choices=sorted(ROLES_VALIDOS), help="Rol del usuario")
    return parser.parse_args()


def main() -> int:
    """Ejecuta el flujo de alta de usuario."""
    args = parse_args()

    with SessionLocal() as db:
        try:
            usuario = crear_usuario(
                db=db,
                nombre=args.nombre.strip(),
                email=args.email.strip().lower(),
                password=args.password,
                rol_nombre=args.rol.strip().lower(),
            )
            print("Usuario creado correctamente")
            print(f"id: {usuario.id}")
            print(f"email: {usuario.email}")
            print(f"rol_id: {usuario.rol_id}")
            return 0
        except Exception as e:
            print(f"Error al crear usuario: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
