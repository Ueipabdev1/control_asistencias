-- Script para poblar el campo id_usuario en asistencias existentes
-- Fecha: 2026-02-03
-- Descripción: Asignar el profesor de cada sección a las asistencias que no tienen id_usuario

-- Actualizar asistencias con el profesor asignado a la sección
UPDATE asistencia a
INNER JOIN profesor_secciones ps ON a.id_seccion = ps.id_seccion
SET a.id_usuario = ps.id_profesor
WHERE a.id_usuario IS NULL;

-- Verificar resultados
SELECT 
    COUNT(*) as total_asistencias,
    COUNT(id_usuario) as con_usuario,
    COUNT(*) - COUNT(id_usuario) as sin_usuario
FROM asistencia;
