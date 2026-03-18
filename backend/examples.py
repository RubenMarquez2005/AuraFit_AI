#!/usr/bin/env python3
"""Ejemplos basicos de uso del ORM de AuraFit AI."""

from datetime import date, datetime, time
from app.db import Base, SessionLocal, engine
from app.models import PerfilSalud, RegistroDiario, Rol, Usuario


def preparar_tablas() -> None:
    """Crea las tablas si aun no existen."""
    Base.metadata.create_all(bind=engine)
    print("Tablas preparadas")


def crear_datos_demo() -> None:
    """Inserta datos de prueba simples para desarrollo local."""
    with SessionLocal() as db:
        # Rol base
        rol_cliente = db.query(Rol).filter(Rol.nombre == "cliente").first()
        if not rol_cliente:
            rol_cliente = Rol(nombre="cliente")
            db.add(rol_cliente)
            db.commit()
            db.refresh(rol_cliente)

        # Usuario demo
        usuario = db.query(Usuario).filter(Usuario.email == "demo@aurafit.ai").first()
        if not usuario:
            usuario = Usuario(
                nombre="Usuario Demo",
                email="demo@aurafit.ai",
                password_hash="pendiente_hash_seguro",
                rol_id=rol_cliente.id,
                fecha_registro=datetime.utcnow(),
            )
            db.add(usuario)
            db.commit()
            db.refresh(usuario)

        # Perfil de salud demo
        perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario.id).first()
        if not perfil:
            perfil = PerfilSalud(
                usuario_id=usuario.id,
                peso_actual=75.0,
                altura=175,
                imc_actual=24.5,
                frecuencia_gym="1-3 dias",
                hora_desayuno=time(8, 0),
                hora_comida=time(14, 0),
                hora_cena=time(21, 0),
                momento_critico_picoteo="tarde",
                percepcion_corporal="En proceso de mejora",
            )
            db.add(perfil)

        # Registro diario demo
        registro = RegistroDiario(
            usuario_id=usuario.id,
            fecha=date.today(),
            foto_comida_url=None,
            analisis_nutricional_ia="Registro de ejemplo",
            estado_animo_puntuacion=7,
            sentimiento_detectado_ia="estable",
            notas_diario="Dia de prueba",
        )
        db.add(registro)
        db.commit()

    print("Datos demo insertados")


if __name__ == "__main__":
    preparar_tablas()
    crear_datos_demo()
