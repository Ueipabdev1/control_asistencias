-- =====================================================
-- Migración: Crear tabla calendario
-- Descripción: Tabla para gestionar días hábiles, feriados y suspensiones
-- Fecha: 2026-03-03
-- =====================================================

USE control_asistencias;

-- Crear tabla calendario
CREATE TABLE IF NOT EXISTS calendario (
    id_calendario INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    tipo_dia ENUM('habil', 'feriado', 'suspension', 'fin_semana') NOT NULL DEFAULT 'habil',
    descripcion VARCHAR(255) COMMENT 'Descripción del día (nombre del feriado, motivo de suspensión, etc.)',
    es_laborable BOOLEAN DEFAULT TRUE COMMENT 'Indica si es un día laborable para el personal',
    observaciones TEXT COMMENT 'Observaciones adicionales',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fecha (fecha),
    INDEX idx_tipo_dia (tipo_dia)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar algunos feriados nacionales de Venezuela como ejemplo
INSERT INTO calendario (fecha, tipo_dia, descripcion, es_laborable) VALUES
('2026-01-01', 'feriado', 'Año Nuevo', FALSE),
('2026-04-19', 'feriado', 'Declaración de la Independencia', FALSE),
('2026-05-01', 'feriado', 'Día del Trabajador', FALSE),
('2026-06-24', 'feriado', 'Batalla de Carabobo', FALSE),
('2026-07-05', 'feriado', 'Día de la Independencia', FALSE),
('2026-07-24', 'feriado', 'Natalicio del Libertador Simón Bolívar', FALSE),
('2026-10-12', 'feriado', 'Día de la Resistencia Indígena', FALSE),
('2026-12-24', 'feriado', 'Nochebuena', FALSE),
('2026-12-25', 'feriado', 'Navidad', FALSE),
('2026-12-31', 'feriado', 'Fin de Año', FALSE)
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- Comentario sobre uso
-- Para marcar días de suspensión de clases, usar tipo_dia='suspension'
-- Para fines de semana, usar tipo_dia='fin_semana'
-- Para días hábiles normales, usar tipo_dia='habil'
