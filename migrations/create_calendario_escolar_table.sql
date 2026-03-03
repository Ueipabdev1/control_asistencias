-- =====================================================
-- Migración: Crear tabla calendario_escolar
-- Descripción: Tabla para gestionar días sin clases (sistema antiguo)
-- Fecha: 2026-03-03
-- =====================================================

USE control_asistencias;

-- Crear tabla calendario_escolar
CREATE TABLE IF NOT EXISTS calendario_escolar (
    id_calendario INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    tipo ENUM('feriado', 'vacaciones', 'suspension', 'otro') NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fecha (fecha),
    INDEX idx_tipo (tipo),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
