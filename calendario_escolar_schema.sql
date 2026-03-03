-- Tabla para calendario escolar (días sin clases)
-- Esta tabla almacena los días no laborables que no deben contarse en el cálculo de asistencia

CREATE TABLE IF NOT EXISTS calendario_escolar (
    id_calendario INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    tipo ENUM('feriado', 'vacaciones', 'suspension', 'otro') NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fecha (fecha),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ejemplos de días no laborables comunes en Venezuela
INSERT INTO calendario_escolar (fecha, tipo, descripcion) VALUES
('2026-01-01', 'feriado', 'Año Nuevo'),
('2026-01-06', 'feriado', 'Día de Reyes'),
('2026-02-16', 'feriado', 'Carnaval'),
('2026-02-17', 'feriado', 'Carnaval'),
('2026-04-03', 'feriado', 'Jueves Santo'),
('2026-04-04', 'feriado', 'Viernes Santo'),
('2026-04-19', 'feriado', 'Declaración de la Independencia'),
('2026-05-01', 'feriado', 'Día del Trabajador'),
('2026-06-24', 'feriado', 'Batalla de Carabobo'),
('2026-07-05', 'feriado', 'Día de la Independencia'),
('2026-07-24', 'feriado', 'Natalicio del Libertador'),
('2026-10-12', 'feriado', 'Día de la Resistencia Indígena'),
('2026-12-24', 'feriado', 'Nochebuena'),
('2026-12-25', 'feriado', 'Navidad'),
('2026-12-31', 'feriado', 'Fin de Año')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- Vacaciones escolares típicas (ajustar según calendario escolar)
-- Vacaciones de Semana Santa
INSERT INTO calendario_escolar (fecha, tipo, descripcion)
SELECT DATE_ADD('2026-04-03', INTERVAL n DAY), 'vacaciones', 'Vacaciones de Semana Santa'
FROM (SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6) AS numbers
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- Vacaciones de mitad de año (ejemplo: del 1 al 31 de agosto)
-- Ajustar según el calendario escolar real
INSERT INTO calendario_escolar (fecha, tipo, descripcion)
SELECT DATE_ADD('2026-08-01', INTERVAL n DAY), 'vacaciones', 'Vacaciones de mitad de año'
FROM (
    SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION
    SELECT 10 UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION
    SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION SELECT 25 UNION SELECT 26 UNION SELECT 27 UNION SELECT 28 UNION SELECT 29 UNION SELECT 30
) AS numbers
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- Vacaciones de Navidad (ejemplo: del 15 de diciembre al 10 de enero)
-- Ajustar según el calendario escolar real
INSERT INTO calendario_escolar (fecha, tipo, descripcion)
SELECT DATE_ADD('2026-12-15', INTERVAL n DAY), 'vacaciones', 'Vacaciones de Navidad'
FROM (
    SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION
    SELECT 10 UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION
    SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION SELECT 25 UNION SELECT 26
) AS numbers
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);
