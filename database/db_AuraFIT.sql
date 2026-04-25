CREATE DATABASE IF NOT EXISTS aurafit_db;

USE aurafit_db;

-- 1) ROLES
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);


-- 2) USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol_id INT NULL,
    cambio_contrasena_pendiente TINYINT(1) NOT NULL DEFAULT 0,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuarios_rol
        FOREIGN KEY (rol_id) REFERENCES roles(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE INDEX idx_usuarios_email ON usuarios(email);


-- 3) PERFILES DE SALUD
CREATE TABLE IF NOT EXISTS perfiles_salud (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL UNIQUE,
    peso_actual DECIMAL(5,2) NULL,
    altura INT NULL,
    imc_actual DECIMAL(4,2) NULL,
    frecuencia_gym VARCHAR(50) NULL,
    hora_desayuno TIME NULL,
    hora_comida TIME NULL,
    hora_cena TIME NULL,
    momento_critico_picoteo VARCHAR(50) NULL,
    percepcion_corporal TEXT NULL,
    CONSTRAINT fk_perfiles_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


-- 4) REGISTROS DIARIOS
CREATE TABLE IF NOT EXISTS registros_diarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    fecha DATE NOT NULL DEFAULT (CURRENT_DATE),
    foto_comida_url VARCHAR(255) NULL,
    analisis_nutricional_ia TEXT NULL,
    estado_animo_puntuacion INT NULL,
    sentimiento_detectado_ia VARCHAR(50) NULL,
    notas_diario TEXT NULL,
    CONSTRAINT fk_registros_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_registros_usuario_fecha ON registros_diarios(usuario_id, fecha);
CREATE UNIQUE INDEX uq_registros_usuario_fecha ON registros_diarios(usuario_id, fecha);


-- 5) DERIVACIONES ENTRE PROFESIONALES
CREATE TABLE IF NOT EXISTS derivaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    origen_profesional_id INT NOT NULL,
    destino_profesional_id INT NOT NULL,
    especialidad_destino VARCHAR(50) NOT NULL,
    motivo TEXT NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    nota_paciente TEXT NULL,
    leida_paciente INT NOT NULL DEFAULT 0,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_derivaciones_paciente
        FOREIGN KEY (paciente_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_derivaciones_origen
        FOREIGN KEY (origen_profesional_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_derivaciones_destino
        FOREIGN KEY (destino_profesional_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_derivaciones_paciente ON derivaciones(paciente_id);
CREATE INDEX idx_derivaciones_destino_fecha ON derivaciones(destino_profesional_id, fecha_creacion);


-- 6) AGENDA DE HABITOS
CREATE TABLE IF NOT EXISTS habitos_agenda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    dia_semana INT NOT NULL,
    titulo VARCHAR(120) NOT NULL,
    subtitulo VARCHAR(255) NOT NULL,
    franja VARCHAR(40) NOT NULL,
    color_hex VARCHAR(16) NOT NULL,
    orden INT NOT NULL DEFAULT 0,
    completado TINYINT(1) NOT NULL DEFAULT 0,
    ultima_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_habitos_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_habitos_usuario_dia ON habitos_agenda(usuario_id, dia_semana);


-- 7) EVALUACIONES IA POR SECCION
CREATE TABLE IF NOT EXISTS evaluaciones_ia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    seccion VARCHAR(60) NOT NULL,
    respuestas_json TEXT NOT NULL,
    plan_ia TEXT NOT NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evaluaciones_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_evaluaciones_usuario_seccion ON evaluaciones_ia(usuario_id, seccion);


-- 8) HISTORIAL DE CHAT
CREATE TABLE IF NOT EXISTS mensajes_chat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    emisor VARCHAR(20) NOT NULL,
    texto TEXT NOT NULL,
    peso_registrado DECIMAL(5,2) NULL,
    imc_calculado DECIMAL(4,2) NULL,
    imc_rango VARCHAR(30) NULL,
    solicitar_altura TINYINT(1) NOT NULL DEFAULT 0,
    activos_premium_json TEXT NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensajes_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_mensajes_usuario_fecha ON mensajes_chat(usuario_id, fecha_creacion);


-- 9) MEDICACION ASIGNADA
CREATE TABLE IF NOT EXISTS medicaciones_asignadas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    profesional_id INT NOT NULL,
    medicamento VARCHAR(120) NOT NULL,
    dosis VARCHAR(120) NOT NULL,
    frecuencia VARCHAR(120) NOT NULL,
    instrucciones TEXT NULL,
    activa TINYINT(1) NOT NULL DEFAULT 1,
    fecha_inicio DATE NOT NULL DEFAULT (CURRENT_DATE),
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_medicaciones_paciente
        FOREIGN KEY (paciente_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_medicaciones_profesional
        FOREIGN KEY (profesional_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_medicaciones_paciente ON medicaciones_asignadas(paciente_id);
CREATE INDEX idx_medicaciones_profesional ON medicaciones_asignadas(profesional_id);


-- 10) PLAN NUTRICIONAL CLINICO (CALORIAS + MACROS)
CREATE TABLE IF NOT EXISTS planes_nutricionales_clinicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    profesional_id INT NOT NULL,
    calorias_objetivo INT NOT NULL,
    proteinas_g INT NOT NULL,
    carbohidratos_g INT NOT NULL,
    grasas_g INT NOT NULL,
    objetivo_clinico VARCHAR(40) NOT NULL DEFAULT 'mantenimiento',
    riesgo_metabolico VARCHAR(20) NOT NULL DEFAULT 'bajo',
    observaciones TEXT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_planes_nutri_paciente
        FOREIGN KEY (paciente_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_planes_nutri_profesional
        FOREIGN KEY (profesional_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_planes_nutri_paciente ON planes_nutricionales_clinicos(paciente_id);
CREATE INDEX idx_planes_nutri_profesional ON planes_nutricionales_clinicos(profesional_id);


-- 11) PROTOCOLOS HOSPITALARIOS POR TRASTORNO Y SEVERIDAD
CREATE TABLE IF NOT EXISTS protocolos_hospitalarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trastorno VARCHAR(60) NOT NULL,
    severidad VARCHAR(20) NOT NULL,
    especialidad VARCHAR(50) NOT NULL,
    titulo VARCHAR(180) NOT NULL,
    checklist_json TEXT NOT NULL,
    ruta_escalado TEXT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_protocolos_trastorno ON protocolos_hospitalarios(trastorno);
CREATE INDEX idx_protocolos_severidad ON protocolos_hospitalarios(severidad);
CREATE INDEX idx_protocolos_especialidad ON protocolos_hospitalarios(especialidad);


-- 12) CHECKLIST CLINICO APLICADO A PACIENTES
CREATE TABLE IF NOT EXISTS checklists_clinicos_pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    profesional_id INT NOT NULL,
    trastorno VARCHAR(60) NOT NULL,
    severidad VARCHAR(20) NOT NULL,
    especialidad VARCHAR(50) NOT NULL,
    checklist_json TEXT NOT NULL,
    requiere_escalado TINYINT(1) NOT NULL DEFAULT 0,
    ruta_escalado_aplicada TEXT NULL,
    observaciones TEXT NULL,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_checklist_paciente
        FOREIGN KEY (paciente_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_checklist_profesional
        FOREIGN KEY (profesional_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_checklist_paciente ON checklists_clinicos_pacientes(paciente_id);
CREATE INDEX idx_checklist_trastorno ON checklists_clinicos_pacientes(trastorno);
CREATE INDEX idx_checklist_severidad ON checklists_clinicos_pacientes(severidad);


-- 13) AUDITORIA TEMPORAL DE CHECKLIST CLINICO
CREATE TABLE IF NOT EXISTS checklists_clinicos_historial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checklist_id INT NOT NULL,
    paciente_id INT NOT NULL,
    profesional_id INT NOT NULL,
    version INT NOT NULL,
    checklist_json TEXT NOT NULL,
    requiere_escalado TINYINT(1) NOT NULL DEFAULT 0,
    ruta_escalado_aplicada TEXT NULL,
    observaciones TEXT NULL,
    fecha_evento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_checklist_historial_checklist
        FOREIGN KEY (checklist_id) REFERENCES checklists_clinicos_pacientes(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_checklist_historial_paciente
        FOREIGN KEY (paciente_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_checklist_historial_profesional
        FOREIGN KEY (profesional_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_checklist_historial_checklist ON checklists_clinicos_historial(checklist_id);
CREATE INDEX idx_checklist_historial_paciente_fecha ON checklists_clinicos_historial(paciente_id, fecha_evento);


-- 14) REPOSITORIO DE RECURSOS CLINICOS
CREATE TABLE IF NOT EXISTS recursos_clinicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trastorno VARCHAR(60) NOT NULL,
    especialidad VARCHAR(50) NOT NULL,
    titulo VARCHAR(180) NOT NULL,
    descripcion TEXT NOT NULL,
    url VARCHAR(500) NULL,
    nivel_evidencia VARCHAR(40) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recursos_trastorno ON recursos_clinicos(trastorno);
CREATE INDEX idx_recursos_especialidad ON recursos_clinicos(especialidad);


-- 14) DATOS BASE
-- 15) DATOS BASE
INSERT INTO roles (nombre)
VALUES
    ('administrador'),
    ('cliente'),
    ('nutricionista'),
    ('psicologo'),
    ('coach'),
    ('medico')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

-- Usuarios iniciales:
-- - Los pacientes se crean desde el registro de la app (/register).
-- - Los usuarios demo profesionales se crean desde el backend al arrancar en modo DEBUG.
-- - La SQL se deja para estructura y roles, evitando duplicar hashes o usuarios de prueba.
