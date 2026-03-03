-- =====================================================
-- Base de Datos: Control de Asistencias V2
-- Sistema de Gestión Educativa con Asistencia Individual
-- MariaDB/MySQL Compatible
-- Versión: 2.0
-- Fecha: 2026-02-03
-- =====================================================
-- CAMBIOS PRINCIPALES:
-- - Estructura normalizada: Etapa → Grado → Sección → Estudiante
-- - Sistema de asistencia individual por estudiante
-- - Soporte para carga de estudiantes desde Excel
-- =====================================================

-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS control_asistencias 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE control_asistencias;

-- =====================================================
-- Tabla: etapa
-- Almacena las etapas educativas (Maternal, Primaria, Secundaria)
-- =====================================================
CREATE TABLE IF NOT EXISTS etapa (
    id_etapa INT AUTO_INCREMENT PRIMARY KEY,
    nombre_etapa VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    activa BOOLEAN DEFAULT TRUE,
    INDEX idx_activa (activa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Tabla: grado
-- Almacena los grados/niveles dentro de cada etapa
-- Ejemplos: 1er grado, 2do grado, 1er año, Nivel 1, etc.
-- =====================================================
CREATE TABLE IF NOT EXISTS grado (
    id_grado INT AUTO_INCREMENT PRIMARY KEY,
    id_etapa INT NOT NULL,
    nombre_grado VARCHAR(100) NOT NULL,
    orden INT NOT NULL COMMENT 'Orden del grado dentro de la etapa (1, 2, 3...)',
    descripcion VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (id_etapa) REFERENCES etapa(id_etapa) ON DELETE CASCADE,
    UNIQUE KEY unique_grado_etapa (id_etapa, nombre_grado),
    INDEX idx_etapa (id_etapa),
    INDEX idx_orden (orden),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Tabla: seccion
-- Almacena las secciones dentro de cada grado
-- Ejemplos: A, B, C, Única, etc.
-- =====================================================
CREATE TABLE IF NOT EXISTS seccion (
    id_seccion INT AUTO_INCREMENT PRIMARY KEY,
    id_grado INT NOT NULL,
    nombre_seccion VARCHAR(50) NOT NULL COMMENT 'A, B, C, Única, etc.',
    capacidad_maxima INT DEFAULT NULL COMMENT 'Capacidad máxima de estudiantes (opcional)',
    activa BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_grado) REFERENCES grado(id_grado) ON DELETE CASCADE,
    UNIQUE KEY unique_seccion_grado (id_grado, nombre_seccion),
    INDEX idx_grado (id_grado),
    INDEX idx_activa (activa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Tabla: usuario
-- Almacena administradores y profesores del sistema
-- =====================================================
CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    contraseña VARCHAR(255) NOT NULL,
    rol ENUM('administrador', 'profesor') NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rol (rol),
    INDEX idx_email (email),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Tabla: profesor_seccion
-- Relación muchos a muchos entre profesores y secciones
-- Un profesor puede tener múltiples secciones
-- Una sección puede tener múltiples profesores
-- =====================================================
CREATE TABLE IF NOT EXISTS profesor_seccion (
    id_profesor_seccion INT AUTO_INCREMENT PRIMARY KEY,
    id_profesor INT NOT NULL,
    id_seccion INT NOT NULL,
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_profesor) REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_seccion) REFERENCES seccion(id_seccion) ON DELETE CASCADE,
    UNIQUE KEY unique_profesor_seccion (id_profesor, id_seccion),
    INDEX idx_profesor (id_profesor),
    INDEX idx_seccion (id_seccion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Tabla: estudiante
-- Almacena información individual de cada estudiante
-- Datos cargados desde archivo Excel
-- =====================================================
CREATE TABLE IF NOT EXISTS estudiante (
    id_estudiante INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL UNIQUE COMMENT 'Cédula de identidad del estudiante',
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    genero ENUM('M', 'F') NOT NULL COMMENT 'M=Masculino, F=Femenino',
    id_seccion INT NOT NULL COMMENT 'Sección a la que pertenece',
    activo BOOLEAN DEFAULT TRUE COMMENT 'Estudiante activo en el sistema',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_seccion) REFERENCES seccion(id_seccion) ON DELETE RESTRICT,
    INDEX idx_cedula (cedula),
    INDEX idx_seccion (id_seccion),
    INDEX idx_activo (activo),
    INDEX idx_genero (genero),
    INDEX idx_nombre_apellido (nombre, apellido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Tabla: asistencia_estudiante
-- Registra la asistencia individual de cada estudiante
-- Sistema nuevo: marca presente/ausente por estudiante
-- =====================================================
CREATE TABLE IF NOT EXISTS asistencia_estudiante (
    id_asistencia_estudiante INT AUTO_INCREMENT PRIMARY KEY,
    id_estudiante INT NOT NULL,
    fecha DATE NOT NULL,
    presente BOOLEAN DEFAULT FALSE NOT NULL COMMENT 'TRUE=Presente, FALSE=Ausente',
    observaciones TEXT COMMENT 'Observaciones opcionales (tardanza, justificación, etc.)',
    id_usuario INT COMMENT 'Usuario que registró la asistencia',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    UNIQUE KEY unique_asistencia_estudiante (id_estudiante, fecha),
    INDEX idx_fecha (fecha),
    INDEX idx_estudiante (id_estudiante),
    INDEX idx_presente (presente),
    INDEX idx_fecha_presente (fecha, presente),
    INDEX idx_usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TABLAS LEGACY (Mantener temporalmente para compatibilidad)
-- Estas tablas se mantendrán para no perder datos históricos
-- =====================================================

-- Tabla legacy: matricula (conteo por género)
CREATE TABLE IF NOT EXISTS matricula_legacy (
    id_matricula INT AUTO_INCREMENT PRIMARY KEY,
    id_seccion_legacy INT NOT NULL COMMENT 'Referencia a secciones antiguas',
    num_estudiantes_h INT DEFAULT 0,
    num_estudiantes_m INT DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_seccion (id_seccion_legacy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla legacy: asistencia (conteo por género)
CREATE TABLE IF NOT EXISTS asistencia_legacy (
    id_asistencia INT AUTO_INCREMENT PRIMARY KEY,
    id_seccion_legacy INT NOT NULL,
    id_usuario INT,
    fecha DATE NOT NULL,
    asistentes_h INT DEFAULT 0,
    asistentes_m INT DEFAULT 0,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    INDEX idx_fecha (fecha),
    INDEX idx_seccion (id_seccion_legacy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- DATOS INICIALES
-- =====================================================

-- Insertar etapas educativas
INSERT INTO etapa (nombre_etapa, descripcion, activa) VALUES
('Maternal', 'Etapa de educación maternal', TRUE),
('Primaria', 'Etapa de educación primaria', TRUE),
('Secundaria', 'Etapa de educación secundaria', TRUE);

-- Insertar grados para Maternal
INSERT INTO grado (id_etapa, nombre_grado, orden, activo) VALUES
(1, 'Nivel 1', 1, TRUE),
(1, 'Nivel 2', 2, TRUE),
(1, 'Nivel 3', 3, TRUE);

-- Insertar grados para Primaria
INSERT INTO grado (id_etapa, nombre_grado, orden, activo) VALUES
(2, '1er grado', 1, TRUE),
(2, '2do grado', 2, TRUE),
(2, '3er grado', 3, TRUE),
(2, '4to grado', 4, TRUE),
(2, '5to grado', 5, TRUE),
(2, '6to grado', 6, TRUE);

-- Insertar grados para Secundaria
INSERT INTO grado (id_etapa, nombre_grado, orden, activo) VALUES
(3, '1er año', 1, TRUE),
(3, '2do año', 2, TRUE),
(3, '3er año', 3, TRUE),
(3, '4to año', 4, TRUE),
(3, '5to año', 5, TRUE);

-- Insertar secciones para cada grado
-- Maternal: Sección única para cada nivel
INSERT INTO seccion (id_grado, nombre_seccion, activa) VALUES
(1, 'Única', TRUE),  -- Nivel 1
(2, 'Única', TRUE),  -- Nivel 2
(3, 'Única', TRUE);  -- Nivel 3

-- Primaria: Sección única para cada grado
INSERT INTO seccion (id_grado, nombre_seccion, activa) VALUES
(4, 'Única', TRUE),   -- 1er grado
(5, 'Única', TRUE),   -- 2do grado
(6, 'Única', TRUE),   -- 3er grado
(7, 'Única', TRUE),   -- 4to grado
(8, 'Única', TRUE),   -- 5to grado
(9, 'Única', TRUE);   -- 6to grado

-- Secundaria: Algunas con múltiples secciones
INSERT INTO seccion (id_grado, nombre_seccion, activa) VALUES
(10, 'Única', TRUE),  -- 1er año
(11, 'Única', TRUE),  -- 2do año
(12, 'A', TRUE),      -- 3er año A
(12, 'B', TRUE),      -- 3er año B
(13, 'Única', TRUE),  -- 4to año
(14, 'Única', TRUE);  -- 5to año

-- =====================================================
-- VISTAS ÚTILES
-- =====================================================

-- Vista: Información completa de secciones
CREATE OR REPLACE VIEW vista_secciones_completa AS
SELECT 
    s.id_seccion,
    s.nombre_seccion,
    g.id_grado,
    g.nombre_grado,
    e.id_etapa,
    e.nombre_etapa,
    CONCAT(e.nombre_etapa, ' - ', g.nombre_grado, ' - Sección ', s.nombre_seccion) AS nombre_completo,
    s.capacidad_maxima,
    s.activa,
    COUNT(est.id_estudiante) AS total_estudiantes,
    SUM(CASE WHEN est.genero = 'M' THEN 1 ELSE 0 END) AS estudiantes_masculinos,
    SUM(CASE WHEN est.genero = 'F' THEN 1 ELSE 0 END) AS estudiantes_femeninos
FROM seccion s
JOIN grado g ON s.id_grado = g.id_grado
JOIN etapa e ON g.id_etapa = e.id_etapa
LEFT JOIN estudiante est ON s.id_seccion = est.id_seccion AND est.activo = TRUE
GROUP BY s.id_seccion, s.nombre_seccion, g.id_grado, g.nombre_grado, e.id_etapa, e.nombre_etapa, s.capacidad_maxima, s.activa;

-- Vista: Estudiantes con información completa
CREATE OR REPLACE VIEW vista_estudiantes_completa AS
SELECT 
    est.id_estudiante,
    est.cedula,
    est.nombre,
    est.apellido,
    CONCAT(est.nombre, ' ', est.apellido) AS nombre_completo,
    est.genero,
    est.activo,
    s.id_seccion,
    s.nombre_seccion,
    g.id_grado,
    g.nombre_grado,
    e.id_etapa,
    e.nombre_etapa,
    CONCAT(e.nombre_etapa, ' - ', g.nombre_grado, ' - Sección ', s.nombre_seccion) AS seccion_completa
FROM estudiante est
JOIN seccion s ON est.id_seccion = s.id_seccion
JOIN grado g ON s.id_grado = g.id_grado
JOIN etapa e ON g.id_etapa = e.id_etapa;

-- =====================================================
-- FIN DEL ESQUEMA V2
-- =====================================================
