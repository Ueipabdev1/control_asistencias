-- =====================================================
-- Base de Datos: Control de Asistencias
-- Sistema de Gestión Educativa
-- MariaDB/MySQL Compatible
-- =====================================================

-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS control_asistencias 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE control_asistencias;

-- =====================================================
-- Tabla: estudiantes
-- Almacena información básica de los estudiantes
-- =====================================================
-- Tabla de etapas educativas
CREATE TABLE etapa (
    id_etapa INT AUTO_INCREMENT PRIMARY KEY,
    nombre_etapa VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255)
);

-- Insertar las etapas predefinidas
INSERT INTO etapa (nombre_etapa, descripcion) VALUES
('Maternal', 'Etapa de educación maternal'),
('Primaria', 'Etapa de educación primaria'),
('Secundaria', 'Etapa de educación secundaria');

-- Tabla de usuarios (para todos los roles)
CREATE TABLE usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    contraseña VARCHAR(255) NOT NULL,
    rol ENUM('administrador', 'profesor') NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rol (rol)
);

-- Tabla de secciones (cursos/grupos) - Sin horario
CREATE TABLE secciones (
    id_seccion INT AUTO_INCREMENT PRIMARY KEY,
    nombre_seccion VARCHAR(50) NOT NULL,
    id_etapa INT NOT NULL,
    FOREIGN KEY (id_etapa) REFERENCES etapa(id_etapa),
    INDEX idx_etapa (id_etapa)
);

-- Tabla de relación profesor_secciones (muchos a muchos)
CREATE TABLE profesor_secciones (
    id_profesor_seccion INT AUTO_INCREMENT PRIMARY KEY,
    id_profesor INT NOT NULL,
    id_seccion INT NOT NULL,
    FOREIGN KEY (id_profesor) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_seccion) REFERENCES secciones(id_seccion) ON DELETE CASCADE,
    UNIQUE KEY unique_profesor_seccion (id_profesor, id_seccion)
);

-- Tabla de matrícula (almacena conteo por género por sección)
CREATE TABLE matricula (
    id_matricula INT AUTO_INCREMENT PRIMARY KEY,
    id_seccion INT NOT NULL,
    num_estudiantes_h INT DEFAULT 0 COMMENT 'Número de estudiantes hombres',
    num_estudiantes_m INT DEFAULT 0 COMMENT 'Número de estudiantes mujeres',
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_seccion) REFERENCES secciones(id_seccion) ON DELETE CASCADE,
    UNIQUE KEY unique_seccion (id_seccion)
);

-- Tabla de asistencia (registra por género por sección)
CREATE TABLE asistencia (
    id_asistencia INT AUTO_INCREMENT PRIMARY KEY,
    id_seccion INT NOT NULL,
    fecha DATE NOT NULL,
    asistentes_h INT DEFAULT 0 COMMENT 'Estudiantes hombres presentes',
    asistentes_m INT DEFAULT 0 COMMENT 'Estudiantes mujeres presentes',
    FOREIGN KEY (id_seccion) REFERENCES secciones(id_seccion) ON DELETE CASCADE,
    UNIQUE KEY unique_asistencia (id_seccion, fecha),
    INDEX idx_fecha (fecha)
);

-- Insertar secciones predefinidas con sus etapas (sin horario)
INSERT INTO secciones (nombre_seccion, id_etapa) VALUES
-- Maternal
('Nivel 1 maternal', 1),
('Nivel 2 maternal', 1),
('Nivel 3 maternal', 1),
-- Primaria
('1er grado primaria', 2),
('2do grado primaria', 2),
('3er grado primaria', 2),
('4to grado primaria', 2),
('5to grado primaria', 2),
('6to grado primaria', 2),
-- Secundaria
('1er año secundaria', 3),
('2do año secundaria', 3),
('3er año A secundaria', 3),
('3er año B secundaria', 3),
('4to año secundaria', 3),
('5to año secundaria', 3);
