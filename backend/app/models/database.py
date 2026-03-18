"""Modelos SQLAlchemy para las tablas de AuraFit."""
from sqlalchemy import Column, Integer, String, Numeric, Time, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class Rol(Base):
    """Tabla de roles para permisos de usuario."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)

    # Relacion uno a muchos: un rol puede tener varios usuarios.
    usuarios = relationship("Usuario", back_populates="rol")

    def __repr__(self):
        return f"<Rol(id={self.id}, nombre={self.nombre})>"


class Usuario(Base):
    """Tabla de usuarios de la plataforma."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"))
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    # Relaciones principales del usuario.
    rol = relationship("Rol", back_populates="usuarios")
    perfil_salud = relationship("PerfilSalud", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    registros_diarios = relationship("RegistroDiario", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario(id={self.id}, email={self.email}, nombre={self.nombre})>"


class PerfilSalud(Base):
    """Perfil de salud y habitos del usuario."""
    __tablename__ = "perfiles_salud"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    peso_actual = Column(Numeric(5, 2))
    altura = Column(Integer)  # Altura en cm.
    imc_actual = Column(Numeric(4, 2))
    frecuencia_gym = Column(String(50))  # 'sedentario', '1-3 dias', '4+ dias'.
    hora_desayuno = Column(Time)
    hora_comida = Column(Time)
    hora_cena = Column(Time)
    momento_critico_picoteo = Column(String(50))  # 'manana', 'tarde', 'noche'.
    percepcion_corporal = Column(Text)

    # Relacion con usuario.
    usuario = relationship("Usuario", back_populates="perfil_salud")

    def __repr__(self):
        return f"<PerfilSalud(id={self.id}, usuario_id={self.usuario_id}, imc={self.imc_actual})>"


class RegistroDiario(Base):
    """Registros diarios para seguimiento nutricional y emocional."""
    __tablename__ = "registros_diarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha = Column(Date, default=datetime.utcnow().date())
    foto_comida_url = Column(String(255))
    analisis_nutricional_ia = Column(Text)
    estado_animo_puntuacion = Column(Integer)  # Rango esperado: 1..10.
    sentimiento_detectado_ia = Column(String(50))  # Ejemplo: 'ansiedad', 'felicidad'.
    notas_diario = Column(Text)

    # Relacion con usuario.
    usuario = relationship("Usuario", back_populates="registros_diarios")

    def __repr__(self):
        return f"<RegistroDiario(id={self.id}, usuario_id={self.usuario_id}, fecha={self.fecha})>"
