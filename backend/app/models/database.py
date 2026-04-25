"""Modelos SQLAlchemy para las tablas de AuraFit."""
from sqlalchemy import Column, Integer, String, Numeric, Time, Date, Text, DateTime, ForeignKey, Boolean
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
    cambio_contrasena_pendiente = Column(Boolean, nullable=False, default=False)

    # Relaciones principales del usuario.
    rol = relationship("Rol", back_populates="usuarios")
    perfil_salud = relationship("PerfilSalud", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    registros_diarios = relationship("RegistroDiario", back_populates="usuario", cascade="all, delete-orphan")
    derivaciones_como_paciente = relationship(
        "Derivacion",
        foreign_keys="Derivacion.paciente_id",
        back_populates="paciente",
        cascade="all, delete-orphan",
    )
    derivaciones_emitidas = relationship(
        "Derivacion",
        foreign_keys="Derivacion.origen_profesional_id",
        back_populates="origen_profesional",
    )
    derivaciones_recibidas = relationship(
        "Derivacion",
        foreign_keys="Derivacion.destino_profesional_id",
        back_populates="destino_profesional",
    )
    habitos_agenda = relationship("HabitoAgenda", back_populates="usuario", cascade="all, delete-orphan")
    evaluaciones_ia = relationship("EvaluacionIA", back_populates="usuario", cascade="all, delete-orphan")
    mensajes_chat = relationship("MensajeChat", back_populates="usuario", cascade="all, delete-orphan")
    memoria_chat = relationship(
        "MemoriaChat",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )
    citas_disponibles_publicadas = relationship(
        "CitaDisponible",
        foreign_keys="CitaDisponible.especialista_id",
        back_populates="especialista",
        cascade="all, delete-orphan",
    )
    citas_como_paciente = relationship(
        "CitaReservada",
        foreign_keys="CitaReservada.paciente_id",
        back_populates="paciente",
        cascade="all, delete-orphan",
    )
    citas_como_especialista = relationship(
        "CitaReservada",
        foreign_keys="CitaReservada.especialista_id",
        back_populates="especialista",
    )
    medicaciones_como_paciente = relationship(
        "MedicacionAsignada",
        foreign_keys="MedicacionAsignada.paciente_id",
        back_populates="paciente",
        cascade="all, delete-orphan",
    )
    medicaciones_prescritas = relationship(
        "MedicacionAsignada",
        foreign_keys="MedicacionAsignada.profesional_id",
        back_populates="profesional",
    )
    planes_nutricionales_como_paciente = relationship(
        "PlanNutricionalClinico",
        foreign_keys="PlanNutricionalClinico.paciente_id",
        back_populates="paciente",
        cascade="all, delete-orphan",
    )
    planes_nutricionales_emitidos = relationship(
        "PlanNutricionalClinico",
        foreign_keys="PlanNutricionalClinico.profesional_id",
        back_populates="profesional",
    )
    checklists_clinicos_como_paciente = relationship(
        "ChecklistClinicoPaciente",
        foreign_keys="ChecklistClinicoPaciente.paciente_id",
        back_populates="paciente",
        cascade="all, delete-orphan",
    )
    checklists_clinicos_emitidos = relationship(
        "ChecklistClinicoPaciente",
        foreign_keys="ChecklistClinicoPaciente.profesional_id",
        back_populates="profesional",
    )

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
    objetivo_principal = Column(String(40), nullable=False, default="perder_grasa")
    deslices_hoy_json = Column(Text, nullable=True)
    deslices_fecha = Column(Date, nullable=True)
    restricciones_alimentarias_json = Column(Text, nullable=True)
    ultima_actualizacion_metricas = Column(DateTime, nullable=True)

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


class Derivacion(Base):
    """Derivaciones entre especialistas para seguimiento del paciente."""

    __tablename__ = "derivaciones"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    origen_profesional_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    destino_profesional_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    especialidad_destino = Column(String(50), nullable=False)
    motivo = Column(Text, nullable=False)
    estado = Column(String(30), nullable=False, default="pendiente")
    nota_paciente = Column(Text)
    leida_paciente = Column(Integer, nullable=False, default=0)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    paciente = relationship(
        "Usuario",
        foreign_keys=[paciente_id],
        back_populates="derivaciones_como_paciente",
    )
    origen_profesional = relationship(
        "Usuario",
        foreign_keys=[origen_profesional_id],
        back_populates="derivaciones_emitidas",
    )
    destino_profesional = relationship(
        "Usuario",
        foreign_keys=[destino_profesional_id],
        back_populates="derivaciones_recibidas",
    )

    def __repr__(self):
        return (
            f"<Derivacion(id={self.id}, paciente_id={self.paciente_id}, "
            f"origen={self.origen_profesional_id}, destino={self.destino_profesional_id})>"
        )


class CitaDisponible(Base):
    """Hueco de calendario habilitado por un especialista para reserva de pacientes."""

    __tablename__ = "citas_disponibles"

    id = Column(Integer, primary_key=True, index=True)
    especialista_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    especialidad = Column(String(50), nullable=False, index=True)
    inicio = Column(DateTime, nullable=False, index=True)
    fin = Column(DateTime, nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="disponible", index=True)
    notas = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    especialista = relationship(
        "Usuario",
        foreign_keys=[especialista_id],
        back_populates="citas_disponibles_publicadas",
    )

    def __repr__(self):
        return (
            f"<CitaDisponible(id={self.id}, especialista_id={self.especialista_id}, "
            f"especialidad={self.especialidad}, estado={self.estado})>"
        )


class CitaReservada(Base):
    """Reserva de cita clínica con triaje de prioridad asistido por IA."""

    __tablename__ = "citas_reservadas"

    id = Column(Integer, primary_key=True, index=True)
    cita_disponible_id = Column(Integer, ForeignKey("citas_disponibles.id"), nullable=True, index=True)
    paciente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    especialista_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    especialidad = Column(String(50), nullable=False, index=True)
    inicio = Column(DateTime, nullable=False, index=True)
    fin = Column(DateTime, nullable=False, index=True)
    motivo = Column(Text, nullable=False)
    formulario_json = Column(Text, nullable=True)
    prioridad_ia = Column(String(20), nullable=False, default="normal", index=True)
    puntuacion_prioridad = Column(Integer, nullable=False, default=1)
    justificacion_ia = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default="pendiente", index=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    cita_disponible = relationship("CitaDisponible", foreign_keys=[cita_disponible_id])
    paciente = relationship(
        "Usuario",
        foreign_keys=[paciente_id],
        back_populates="citas_como_paciente",
    )
    especialista = relationship(
        "Usuario",
        foreign_keys=[especialista_id],
        back_populates="citas_como_especialista",
    )

    def __repr__(self):
        return (
            f"<CitaReservada(id={self.id}, paciente_id={self.paciente_id}, "
            f"especialista_id={self.especialista_id}, prioridad={self.prioridad_ia})>"
        )


class HabitoAgenda(Base):
    """Tareas de agenda persistentes por usuario y dia de la semana."""

    __tablename__ = "habitos_agenda"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    dia_semana = Column(Integer, nullable=False, index=True)
    titulo = Column(String(120), nullable=False)
    subtitulo = Column(String(255), nullable=False)
    franja = Column(String(40), nullable=False)
    color_hex = Column(String(16), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    completado = Column(Boolean, nullable=False, default=False)
    ultima_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    usuario = relationship("Usuario", back_populates="habitos_agenda")

    def __repr__(self):
        return (
            f"<HabitoAgenda(id={self.id}, usuario_id={self.usuario_id}, dia={self.dia_semana}, "
            f"titulo={self.titulo})>"
        )


class EvaluacionIA(Base):
    """Persistencia de cuestionarios IA por seccion para cada usuario."""

    __tablename__ = "evaluaciones_ia"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    seccion = Column(String(60), nullable=False, index=True)
    respuestas_json = Column(Text, nullable=False)
    plan_ia = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    usuario = relationship("Usuario", back_populates="evaluaciones_ia")

    def __repr__(self):
        return f"<EvaluacionIA(id={self.id}, usuario_id={self.usuario_id}, seccion={self.seccion})>"


class MensajeChat(Base):
    """Historial persistente de conversación chat IA por usuario."""

    __tablename__ = "mensajes_chat"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    emisor = Column(String(20), nullable=False)
    texto = Column(Text, nullable=False)
    peso_registrado = Column(Numeric(5, 2), nullable=True)
    imc_calculado = Column(Numeric(4, 2), nullable=True)
    imc_rango = Column(String(30), nullable=True)
    solicitar_altura = Column(Boolean, nullable=False, default=False)
    activos_premium_json = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    usuario = relationship("Usuario", back_populates="mensajes_chat")

    def __repr__(self):
        return f"<MensajeChat(id={self.id}, usuario_id={self.usuario_id}, emisor={self.emisor})>"


class MemoriaChat(Base):
    """Estado persistido para preguntas encadenadas del chat IA."""

    __tablename__ = "memorias_chat"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    tema = Column(String(80), nullable=False)
    preguntas_json = Column(Text, nullable=False)
    respuestas_json = Column(Text, nullable=False, default="{}")
    pregunta_actual = Column(Text, nullable=True)
    indice_pregunta = Column(Integer, nullable=False, default=0)
    activa = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    usuario = relationship("Usuario", back_populates="memoria_chat")

    def __repr__(self):
        return f"<MemoriaChat(id={self.id}, usuario_id={self.usuario_id}, tema={self.tema})>"


class MedicacionAsignada(Base):
    """Plan farmacológico prescrito por profesional para un paciente."""

    __tablename__ = "medicaciones_asignadas"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    profesional_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    medicamento = Column(String(120), nullable=False)
    dosis = Column(String(120), nullable=False)
    frecuencia = Column(String(120), nullable=False)
    instrucciones = Column(Text, nullable=True)
    activa = Column(Boolean, nullable=False, default=True)
    fecha_inicio = Column(Date, default=datetime.utcnow().date, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    paciente = relationship(
        "Usuario",
        foreign_keys=[paciente_id],
        back_populates="medicaciones_como_paciente",
    )
    profesional = relationship(
        "Usuario",
        foreign_keys=[profesional_id],
        back_populates="medicaciones_prescritas",
    )

    def __repr__(self):
        return (
            f"<MedicacionAsignada(id={self.id}, paciente_id={self.paciente_id}, "
            f"profesional_id={self.profesional_id}, activa={self.activa})>"
        )


class PlanNutricionalClinico(Base):
    """Plan nutricional clínico por paciente con objetivo calórico y macronutrientes."""

    __tablename__ = "planes_nutricionales_clinicos"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    profesional_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    calorias_objetivo = Column(Integer, nullable=False)
    proteinas_g = Column(Integer, nullable=False)
    carbohidratos_g = Column(Integer, nullable=False)
    grasas_g = Column(Integer, nullable=False)
    objetivo_clinico = Column(String(40), nullable=False, default="mantenimiento")
    riesgo_metabolico = Column(String(20), nullable=False, default="bajo")
    observaciones = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    paciente = relationship(
        "Usuario",
        foreign_keys=[paciente_id],
        back_populates="planes_nutricionales_como_paciente",
    )
    profesional = relationship(
        "Usuario",
        foreign_keys=[profesional_id],
        back_populates="planes_nutricionales_emitidos",
    )

    def __repr__(self):
        return (
            f"<PlanNutricionalClinico(id={self.id}, paciente_id={self.paciente_id}, "
            f"profesional_id={self.profesional_id}, kcal={self.calorias_objetivo})>"
        )


class ProtocoloHospitalario(Base):
    """Plantillas de protocolo clínico por trastorno, severidad y especialidad."""

    __tablename__ = "protocolos_hospitalarios"

    id = Column(Integer, primary_key=True, index=True)
    trastorno = Column(String(60), nullable=False, index=True)
    severidad = Column(String(20), nullable=False, index=True)
    especialidad = Column(String(50), nullable=False, index=True)
    titulo = Column(String(180), nullable=False)
    checklist_json = Column(Text, nullable=False)
    ruta_escalado = Column(Text, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<ProtocoloHospitalario(id={self.id}, trastorno={self.trastorno}, "
            f"severidad={self.severidad}, especialidad={self.especialidad})>"
        )


class ChecklistClinicoPaciente(Base):
    """Checklist clínico aplicado a un paciente con trazabilidad profesional."""

    __tablename__ = "checklists_clinicos_pacientes"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    profesional_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    trastorno = Column(String(60), nullable=False, index=True)
    severidad = Column(String(20), nullable=False, index=True)
    especialidad = Column(String(50), nullable=False, index=True)
    checklist_json = Column(Text, nullable=False)
    requiere_escalado = Column(Boolean, nullable=False, default=False)
    ruta_escalado_aplicada = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    paciente = relationship(
        "Usuario",
        foreign_keys=[paciente_id],
        back_populates="checklists_clinicos_como_paciente",
    )
    profesional = relationship(
        "Usuario",
        foreign_keys=[profesional_id],
        back_populates="checklists_clinicos_emitidos",
    )
    historial_cambios = relationship(
        "ChecklistClinicoHistorial",
        back_populates="checklist",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<ChecklistClinicoPaciente(id={self.id}, paciente_id={self.paciente_id}, "
            f"trastorno={self.trastorno}, severidad={self.severidad})>"
        )


class ChecklistClinicoHistorial(Base):
    """Auditoria temporal de cambios de checklist clínico por paciente."""

    __tablename__ = "checklists_clinicos_historial"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("checklists_clinicos_pacientes.id"), nullable=False, index=True)
    paciente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    profesional_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    checklist_json = Column(Text, nullable=False)
    requiere_escalado = Column(Boolean, nullable=False, default=False)
    ruta_escalado_aplicada = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_evento = Column(DateTime, default=datetime.utcnow, nullable=False)

    checklist = relationship("ChecklistClinicoPaciente", back_populates="historial_cambios")

    def __repr__(self):
        return (
            f"<ChecklistClinicoHistorial(id={self.id}, checklist_id={self.checklist_id}, "
            f"version={self.version})>"
        )


class RecursoClinico(Base):
    """Repositorio persistente de recursos clínicos por trastorno y especialidad."""

    __tablename__ = "recursos_clinicos"

    id = Column(Integer, primary_key=True, index=True)
    trastorno = Column(String(60), nullable=False, index=True)
    especialidad = Column(String(50), nullable=False, index=True)
    titulo = Column(String(180), nullable=False)
    descripcion = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)
    nivel_evidencia = Column(String(40), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<RecursoClinico(id={self.id}, trastorno={self.trastorno}, "
            f"especialidad={self.especialidad})>"
        )
