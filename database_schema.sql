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
CREATE TABLE estudiantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    genero ENUM('masculino', 'femenino') NOT NULL DEFAULT 'masculino',
    seccion VARCHAR(5) NOT NULL DEFAULT 'A',
    etapa ENUM('inicial', 'primaria', 'secundaria') NOT NULL DEFAULT 'primaria',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    INDEX idx_codigo (codigo),
    INDEX idx_seccion (seccion),
    INDEX idx_etapa (etapa),
    INDEX idx_genero (genero)
) ENGINE=InnoDB;

-- =====================================================
-- Tabla: asistencias
-- Registra la asistencia diaria de los estudiantes
-- =====================================================
CREATE TABLE asistencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estudiante_id INT NOT NULL,
    fecha DATE NOT NULL,
    presente BOOLEAN NOT NULL DEFAULT FALSE,
    observaciones TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_estudiante_fecha (estudiante_id, fecha),
    INDEX idx_fecha (fecha),
    INDEX idx_presente (presente),
    INDEX idx_estudiante_fecha (estudiante_id, fecha)
) ENGINE=InnoDB;

-- =====================================================
-- Tabla: usuarios (opcional para autenticación)
-- =====================================================
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('profesor', 'admin', 'director') NOT NULL DEFAULT 'profesor',
    nombre_completo VARCHAR(150),
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_rol (rol)
) ENGINE=InnoDB;

-- =====================================================
-- Tabla: configuracion_sistema
-- Configuraciones generales del sistema
-- =====================================================
CREATE TABLE configuracion_sistema (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    descripcion VARCHAR(255),
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================
-- DATOS DE EJEMPLO
-- =====================================================

-- Insertar estudiantes de ejemplo
INSERT INTO estudiantes (nombre, apellido, codigo, genero, seccion, etapa) VALUES
-- Inicial
('Ana', 'García', 'INI001', 'femenino', 'A', 'inicial'),
('Luis', 'Pérez', 'INI002', 'masculino', 'A', 'inicial'),
('María', 'López', 'INI003', 'femenino', 'B', 'inicial'),
('Carlos', 'Ruiz', 'INI004', 'masculino', 'B', 'inicial'),
('Isabella', 'Moreno', 'INI005', 'femenino', 'A', 'inicial'),
('Diego', 'Castillo', 'INI006', 'masculino', 'B', 'inicial'),

-- Primaria
('Juan', 'Martínez', 'PRI001', 'masculino', 'A', 'primaria'),
('Sofia', 'González', 'PRI002', 'femenino', 'A', 'primaria'),
('Diego', 'Rodríguez', 'PRI003', 'masculino', 'B', 'primaria'),
('Valentina', 'Hernández', 'PRI004', 'femenino', 'B', 'primaria'),
('Mateo', 'Silva', 'PRI005', 'masculino', 'C', 'primaria'),
('Isabella', 'Torres', 'PRI006', 'femenino', 'C', 'primaria'),
('Santiago', 'Ramírez', 'PRI007', 'masculino', 'A', 'primaria'),
('Camila', 'Flores', 'PRI008', 'femenino', 'B', 'primaria'),
('Sebastián', 'Vega', 'PRI009', 'masculino', 'C', 'primaria'),
('Lucía', 'Ortega', 'PRI010', 'femenino', 'A', 'primaria'),

-- Secundaria
('Alejandro', 'Morales', 'SEC001', 'masculino', 'A', 'secundaria'),
('Camila', 'Vargas', 'SEC002', 'femenino', 'A', 'secundaria'),
('Sebastián', 'Castro', 'SEC003', 'masculino', 'B', 'secundaria'),
('Gabriela', 'Mendoza', 'SEC004', 'femenino', 'B', 'secundaria'),
('Nicolás', 'Jiménez', 'SEC005', 'masculino', 'C', 'secundaria'),
('Daniela', 'Romero', 'SEC006', 'femenino', 'C', 'secundaria'),
('Andrés', 'Guerrero', 'SEC007', 'masculino', 'A', 'secundaria'),
('Valeria', 'Delgado', 'SEC008', 'femenino', 'B', 'secundaria'),
('Felipe', 'Aguilar', 'SEC009', 'masculino', 'C', 'secundaria'),
('Natalia', 'Herrera', 'SEC010', 'femenino', 'A', 'secundaria');

-- Insertar usuario administrador por defecto
INSERT INTO usuarios (username, email, password_hash, rol, nombre_completo) VALUES
('admin', 'admin@colegio.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5u', 'admin', 'Administrador del Sistema'),
('profesor1', 'profesor1@colegio.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5u', 'profesor', 'María Elena Rodríguez'),
('director', 'director@colegio.edu', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5u', 'director', 'Carlos Alberto Mendoza');

-- Configuraciones del sistema
INSERT INTO configuracion_sistema (clave, valor, descripcion) VALUES
('nombre_institucion', 'Instituto Educativo San José', 'Nombre de la institución educativa'),
('año_lectivo', '2024', 'Año lectivo actual'),
('horario_clases_inicio', '07:00', 'Hora de inicio de clases'),
('horario_clases_fin', '17:00', 'Hora de finalización de clases'),
('dias_laborales', 'lunes,martes,miercoles,jueves,viernes', 'Días de la semana con clases'),
('porcentaje_minimo_asistencia', '75', 'Porcentaje mínimo de asistencia requerido');

-- =====================================================
-- PROCEDIMIENTOS ALMACENADOS
-- =====================================================

DELIMITER //

-- Procedimiento para obtener estadísticas de asistencia por período
CREATE PROCEDURE ObtenerEstadisticasAsistencia(
    IN fecha_inicio DATE,
    IN fecha_fin DATE,
    IN etapa_filtro VARCHAR(20)
)
BEGIN
    DECLARE total_registros INT DEFAULT 0;
    DECLARE presentes INT DEFAULT 0;
    
    -- Estadísticas generales
    SELECT 
        COUNT(*) as total_asistencias,
        SUM(CASE WHEN presente = 1 THEN 1 ELSE 0 END) as total_presentes,
        ROUND((SUM(CASE WHEN presente = 1 THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) as porcentaje_asistencia
    FROM asistencias a
    JOIN estudiantes e ON a.estudiante_id = e.id
    WHERE a.fecha BETWEEN fecha_inicio AND fecha_fin
    AND (etapa_filtro IS NULL OR e.etapa = etapa_filtro);
    
    -- Estadísticas por género
    SELECT 
        e.genero,
        COUNT(*) as total,
        SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) as presentes,
        ROUND((SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) as porcentaje
    FROM asistencias a
    JOIN estudiantes e ON a.estudiante_id = e.id
    WHERE a.fecha BETWEEN fecha_inicio AND fecha_fin
    AND (etapa_filtro IS NULL OR e.etapa = etapa_filtro)
    GROUP BY e.genero;
    
    -- Estadísticas por sección
    SELECT 
        e.seccion,
        COUNT(*) as total,
        SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) as presentes,
        ROUND((SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) as porcentaje
    FROM asistencias a
    JOIN estudiantes e ON a.estudiante_id = e.id
    WHERE a.fecha BETWEEN fecha_inicio AND fecha_fin
    AND (etapa_filtro IS NULL OR e.etapa = etapa_filtro)
    GROUP BY e.seccion
    ORDER BY porcentaje DESC;
    
    -- Estadísticas por etapa
    SELECT 
        e.etapa,
        COUNT(*) as total,
        SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) as presentes,
        ROUND((SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) as porcentaje
    FROM asistencias a
    JOIN estudiantes e ON a.estudiante_id = e.id
    WHERE a.fecha BETWEEN fecha_inicio AND fecha_fin
    GROUP BY e.etapa
    ORDER BY porcentaje DESC;
END //

-- Procedimiento para generar datos de asistencia de ejemplo
CREATE PROCEDURE GenerarAsistenciasEjemplo()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE estudiante_id INT;
    DECLARE fecha_actual DATE;
    DECLARE dias_atras INT DEFAULT 30;
    DECLARE probabilidad_asistencia DECIMAL(3,2) DEFAULT 0.85;
    
    DECLARE estudiante_cursor CURSOR FOR 
        SELECT id FROM estudiantes WHERE activo = TRUE;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- Limpiar asistencias existentes (opcional)
    -- DELETE FROM asistencias;
    
    SET fecha_actual = DATE_SUB(CURDATE(), INTERVAL dias_atras DAY);
    
    WHILE fecha_actual <= CURDATE() DO
        -- Solo generar para días de semana (lunes a viernes)
        IF WEEKDAY(fecha_actual) < 5 THEN
            OPEN estudiante_cursor;
            
            estudiante_loop: LOOP
                FETCH estudiante_cursor INTO estudiante_id;
                IF done THEN
                    LEAVE estudiante_loop;
                END IF;
                
                -- Insertar asistencia con probabilidad del 85%
                INSERT IGNORE INTO asistencias (estudiante_id, fecha, presente, observaciones)
                VALUES (
                    estudiante_id, 
                    fecha_actual, 
                    CASE WHEN RAND() < probabilidad_asistencia THEN TRUE ELSE FALSE END,
                    'Registro automático de ejemplo'
                );
            END LOOP;
            
            CLOSE estudiante_cursor;
            SET done = FALSE;
        END IF;
        
        SET fecha_actual = DATE_ADD(fecha_actual, INTERVAL 1 DAY);
    END WHILE;
END //

DELIMITER ;

-- =====================================================
-- VISTAS ÚTILES
-- =====================================================

-- Vista para estadísticas rápidas de estudiantes
CREATE VIEW vista_estudiantes_resumen AS
SELECT 
    etapa,
    seccion,
    genero,
    COUNT(*) as total_estudiantes
FROM estudiantes 
WHERE activo = TRUE
GROUP BY etapa, seccion, genero
ORDER BY etapa, seccion, genero;

-- Vista para asistencia del día actual
CREATE VIEW vista_asistencia_hoy AS
SELECT 
    e.nombre,
    e.apellido,
    e.codigo,
    e.seccion,
    e.etapa,
    e.genero,
    COALESCE(a.presente, FALSE) as presente,
    a.observaciones
FROM estudiantes e
LEFT JOIN asistencias a ON e.id = a.estudiante_id AND a.fecha = CURDATE()
WHERE e.activo = TRUE
ORDER BY e.etapa, e.seccion, e.apellido, e.nombre;

-- Vista para estadísticas mensuales
CREATE VIEW vista_estadisticas_mes_actual AS
SELECT 
    e.etapa,
    e.seccion,
    e.genero,
    COUNT(a.id) as total_registros,
    SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) as total_presentes,
    ROUND((SUM(CASE WHEN a.presente = 1 THEN 1 ELSE 0 END) / COUNT(a.id)) * 100, 2) as porcentaje_asistencia
FROM estudiantes e
JOIN asistencias a ON e.id = a.estudiante_id
WHERE e.activo = TRUE 
AND MONTH(a.fecha) = MONTH(CURDATE()) 
AND YEAR(a.fecha) = YEAR(CURDATE())
GROUP BY e.etapa, e.seccion, e.genero
ORDER BY e.etapa, e.seccion, porcentaje_asistencia DESC;

-- =====================================================
-- EJECUTAR PROCEDIMIENTO PARA GENERAR DATOS DE EJEMPLO
-- =====================================================

-- Descomentar la siguiente línea para generar datos de asistencia de ejemplo
-- CALL GenerarAsistenciasEjemplo();

-- =====================================================
-- CONSULTAS DE VERIFICACIÓN
-- =====================================================

-- Verificar estudiantes creados
SELECT 'Estudiantes por etapa' as consulta;
SELECT etapa, COUNT(*) as total FROM estudiantes GROUP BY etapa;

-- Verificar distribución por género
SELECT 'Distribución por género' as consulta;
SELECT genero, COUNT(*) as total FROM estudiantes GROUP BY genero;

-- Verificar distribución por sección
SELECT 'Distribución por sección' as consulta;
SELECT seccion, COUNT(*) as total FROM estudiantes GROUP BY seccion ORDER BY seccion;

-- =====================================================
-- ÍNDICES ADICIONALES PARA OPTIMIZACIÓN
-- =====================================================

-- Índices compuestos para consultas frecuentes
CREATE INDEX idx_asistencias_fecha_presente ON asistencias(fecha, presente);
CREATE INDEX idx_estudiantes_etapa_seccion ON estudiantes(etapa, seccion);
CREATE INDEX idx_estudiantes_genero_activo ON estudiantes(genero, activo);

-- =====================================================
-- COMENTARIOS FINALES
-- =====================================================

/*
INSTRUCCIONES DE USO:

1. Ejecutar este script en MariaDB/MySQL
2. Verificar que se crearon las tablas correctamente
3. Los datos de ejemplo se insertan automáticamente
4. Para generar asistencias de ejemplo, ejecutar:
   CALL GenerarAsistenciasEjemplo();

CREDENCIALES POR DEFECTO:
- Usuario: admin / Contraseña: admin123
- Usuario: profesor1 / Contraseña: admin123
- Usuario: director / Contraseña: admin123

CONFIGURACIÓN DE FLASK:
Actualizar la cadena de conexión en app.py:
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://usuario:contraseña@localhost/control_asistencias'

DEPENDENCIAS ADICIONALES:
pip install PyMySQL
*/
