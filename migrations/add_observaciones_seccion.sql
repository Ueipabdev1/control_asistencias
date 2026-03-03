-- Migración: Agregar tabla de observaciones de sección
-- Fecha: 2026-02-03
-- Descripción: Tabla para almacenar observaciones generales por sección y fecha

CREATE TABLE IF NOT EXISTS observacion_seccion (
    id_observacion INT AUTO_INCREMENT PRIMARY KEY,
    id_seccion INT NOT NULL,
    fecha DATE NOT NULL,
    observaciones TEXT COMMENT 'Observaciones generales de la clase',
    id_usuario INT COMMENT 'Usuario que registró la observación',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Constraint único para evitar duplicados por sección y fecha
    CONSTRAINT unique_observacion_seccion UNIQUE (id_seccion, fecha),
    
    -- Foreign keys
    CONSTRAINT fk_observacion_seccion FOREIGN KEY (id_seccion) 
        REFERENCES seccion(id_seccion) ON DELETE CASCADE,
    CONSTRAINT fk_observacion_usuario FOREIGN KEY (id_usuario) 
        REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    
    -- Índices para mejorar búsquedas
    INDEX idx_observacion_fecha (fecha),
    INDEX idx_observacion_seccion_fecha (id_seccion, fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Observaciones generales de clase por sección y fecha';
