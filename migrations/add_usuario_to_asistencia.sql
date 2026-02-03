-- Migración: Agregar campo id_usuario a la tabla asistencia
-- Fecha: 2026-02-03
-- Descripción: Agregar columna para registrar qué usuario creó cada asistencia

ALTER TABLE asistencia 
ADD COLUMN id_usuario INT(11) NULL COMMENT 'Usuario que registró la asistencia' AFTER id_seccion,
ADD CONSTRAINT fk_asistencia_usuario 
    FOREIGN KEY (id_usuario) 
    REFERENCES usuario(id_usuario) 
    ON DELETE SET NULL;

-- Crear índice para mejorar el rendimiento de las consultas
CREATE INDEX idx_asistencia_usuario ON asistencia(id_usuario);
