#!/usr/bin/env python3
"""Prueba rapida de configuracion y conexion de base de datos."""

import asyncio
import sys
from sqlalchemy import text
from app.config.settings import settings
from app.db import SessionLocal, verify_database_connection, engine, Base
from app.models import Rol, Usuario, PerfilSalud, RegistroDiario


def print_titulo(texto: str) -> None:
    """Imprime un titulo simple en consola."""
    print("\n" + "=" * 60)
    print(texto)
    print("=" * 60)


async def test_database() -> bool:
    """Ejecuta comprobaciones basicas de entorno y conexion."""
    print_titulo("Prueba de base de datos - AuraFit AI")

    print("Configuracion actual:")
    print(f"- APP_NAME: {settings.APP_NAME}")
    print(f"- DEBUG: {settings.DEBUG}")
    print(f"- DB_HOST: {settings.DB_HOST}")
    print(f"- DB_PORT: {settings.DB_PORT}")
    print(f"- DB_NAME: {settings.DB_NAME}")

    print("\nComprobando conexion...")
    if not await verify_database_connection():
        print("Resultado: conexion no disponible")
        return False

    print("Resultado: conexion correcta")

    try:
        # Garantiza que las tablas declaradas en modelos existan.
        Base.metadata.create_all(bind=engine)
        print("Tablas verificadas")
    except Exception as e:
        print(f"Error al crear/verificar tablas: {e}")
        return False

    print("Modelos cargados:")
    for nombre, model in [
        ("Rol", Rol),
        ("Usuario", Usuario),
        ("PerfilSalud", PerfilSalud),
        ("RegistroDiario", RegistroDiario),
    ]:
        print(f"- {nombre}: {model.__tablename__}")

    # Valida una consulta minima de sesion.
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))

    print("Sesion de base de datos operativa")
    return True


if __name__ == "__main__":
    try:
        ok = asyncio.run(test_database())
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Error en la prueba: {e}")
        sys.exit(1)
