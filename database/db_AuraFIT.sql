CREATE DATABASE IF NOT EXISTS aurafit_db;

USE aurafit_db;



-- 1. Tabla de Roles

CREATE TABLE roles (

    id INT AUTO_INCREMENT PRIMARY KEY,

    nombre VARCHAR(50) NOT NULL -- 'cliente', 'nutricionista', 'psicologo', 'coach'

);



-- 2. Tabla de Usuarios

CREATE TABLE usuarios (

    id INT AUTO_INCREMENT PRIMARY KEY,

    nombre VARCHAR(100) NOT NULL,

    email VARCHAR(100) UNIQUE NOT NULL,

    password_hash VARCHAR(255) NOT NULL,

    rol_id INT,

    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (rol_id) REFERENCES roles(id)

);



-- 3. Perfil de Salud y Hábitos (Lo que la IA analizará)

CREATE TABLE perfiles_salud (

    id INT AUTO_INCREMENT PRIMARY KEY,

    usuario_id INT,

    peso_actual DECIMAL(5,2),

    altura INT, -- en cm

    imc_actual DECIMAL(4,2),

    frecuencia_gym VARCHAR(50), -- 'sedentario', '1-3 dias', '4+ dias'

    hora_desayuno TIME,

    hora_comida TIME,

    hora_cena TIME,

    momento_critico_picoteo VARCHAR(50), -- 'mañana', 'tarde', 'noche'

    percepcion_corporal TEXT, -- Respuesta a "¿Cómo te ves?"

    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)

);



-- 4. Registros Diarios (Nutrición y Mente)

CREATE TABLE registros_diarios (

    id INT AUTO_INCREMENT PRIMARY KEY,

    usuario_id INT,

    fecha DATE,

    foto_comida_url VARCHAR(255), -- Para la IA de visión

    analisis_nutricional_ia TEXT,

    estado_animo_puntuacion INT, -- 1 al 10

    sentimiento_detectado_ia VARCHAR(50), -- 'ansiedad', 'felicidad', etc.

    notas_diario TEXT,

    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)

);



-- Inserción de roles básicos

INSERT INTO roles (nombre) VALUES ('administrador'), ('cliente'), ('nutricionista'), ('psicologo'), ('coach');