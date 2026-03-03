-- =====================================================
-- Migración V1 → V2: Control de Asistencias
-- Fecha: 2026-03-03
-- =====================================================
-- IMPORTANTE: Ejecutar backup ANTES de esta migración
-- Las tablas V1 (secciones, profesor_secciones, matricula, asistencia) NO se eliminan
-- =====================================================

SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. ALTER TABLE etapa — agregar columna activa
-- =====================================================
ALTER TABLE `etapa`
    ADD COLUMN IF NOT EXISTS `activa` BOOLEAN DEFAULT TRUE;

-- =====================================================
-- 2. ALTER TABLE usuario — agregar columna activo
-- =====================================================
ALTER TABLE `usuario`
    ADD COLUMN IF NOT EXISTS `activo` BOOLEAN DEFAULT TRUE;

-- =====================================================
-- 3. CREATE TABLE grado
-- =====================================================
CREATE TABLE IF NOT EXISTS `grado` (
    `id_grado` INT(11) NOT NULL AUTO_INCREMENT,
    `id_etapa` INT(11) NOT NULL,
    `nombre_grado` VARCHAR(100) NOT NULL,
    `orden` INT(11) NOT NULL COMMENT 'Orden del grado dentro de la etapa',
    `descripcion` VARCHAR(255) DEFAULT NULL,
    `activo` BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (`id_grado`),
    UNIQUE KEY `unique_grado_etapa` (`id_etapa`, `nombre_grado`),
    CONSTRAINT `fk_grado_etapa` FOREIGN KEY (`id_etapa`) REFERENCES `etapa` (`id_etapa`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed data: grados mapeados a etapas
-- Etapa 1 (Maternal): 3 niveles
-- Etapa 2 (Primaria): 6 grados
-- Etapa 3 (Secundaria): 5 años
INSERT IGNORE INTO `grado` (`id_grado`, `id_etapa`, `nombre_grado`, `orden`, `descripcion`) VALUES
    (1,  1, 'Nivel 1 maternal',       1, 'Primer nivel de maternal'),
    (2,  1, 'Nivel 2 maternal',       2, 'Segundo nivel de maternal'),
    (3,  1, 'Nivel 3 maternal',       3, 'Tercer nivel de maternal'),
    (4,  2, '1er grado primaria',     1, 'Primer grado de primaria'),
    (5,  2, '2do grado primaria',     2, 'Segundo grado de primaria'),
    (6,  2, '3er grado primaria',     3, 'Tercer grado de primaria'),
    (7,  2, '4to grado primaria',     4, 'Cuarto grado de primaria'),
    (8,  2, '5to grado primaria',     5, 'Quinto grado de primaria'),
    (9,  2, '6to grado primaria',     6, 'Sexto grado de primaria'),
    (10, 3, '1er año secundaria',     1, 'Primer año de secundaria'),
    (11, 3, '2do año secundaria',     2, 'Segundo año de secundaria'),
    (12, 3, '3er año secundaria',     3, 'Tercer año de secundaria'),
    (13, 3, '4to año secundaria',     4, 'Cuarto año de secundaria'),
    (14, 3, '5to año secundaria',     5, 'Quinto año de secundaria');

-- =====================================================
-- 4. CREATE TABLE seccion (nueva, singular)
-- =====================================================
-- IDs 1-15 mapean 1:1 con secciones V1
CREATE TABLE IF NOT EXISTS `seccion` (
    `id_seccion` INT(11) NOT NULL AUTO_INCREMENT,
    `id_grado` INT(11) NOT NULL,
    `nombre_seccion` VARCHAR(50) NOT NULL,
    `activa` BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (`id_seccion`),
    CONSTRAINT `fk_seccion_grado` FOREIGN KEY (`id_grado`) REFERENCES `grado` (`id_grado`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed data: secciones mapeadas 1:1 con secciones V1
-- Sección única por grado (excepto 3er año que tiene A y B)
INSERT IGNORE INTO `seccion` (`id_seccion`, `id_grado`, `nombre_seccion`) VALUES
    (1,  1,  'Única'),
    (2,  2,  'Única'),
    (3,  3,  'Única'),
    (4,  4,  'Única'),
    (5,  5,  'Única'),
    (6,  6,  'Única'),
    (7,  7,  'Única'),
    (8,  8,  'Única'),
    (9,  9,  'Única'),
    (10, 10, 'Única'),
    (11, 11, 'Única'),
    (12, 12, 'A'),
    (13, 12, 'B'),
    (14, 13, 'Única'),
    (15, 14, 'Única');

-- =====================================================
-- 5. CREATE TABLE profesor_seccion (singular, V2)
-- =====================================================
CREATE TABLE IF NOT EXISTS `profesor_seccion` (
    `id_profesor_seccion` INT(11) NOT NULL AUTO_INCREMENT,
    `id_profesor` INT(11) NOT NULL,
    `id_seccion` INT(11) NOT NULL,
    `fecha_asignacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_profesor_seccion`),
    UNIQUE KEY `unique_profesor_seccion` (`id_profesor`, `id_seccion`),
    CONSTRAINT `fk_profsec_profesor` FOREIGN KEY (`id_profesor`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE,
    CONSTRAINT `fk_profsec_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migrar datos desde profesor_secciones V1 (IDs 1:1)
INSERT IGNORE INTO `profesor_seccion` (`id_profesor`, `id_seccion`, `fecha_asignacion`)
    SELECT `id_profesor`, `id_seccion`, CURRENT_TIMESTAMP
    FROM `profesor_secciones`;

-- =====================================================
-- 6. CREATE TABLE estudiante (vacía, lista para carga)
-- =====================================================
CREATE TABLE IF NOT EXISTS `estudiante` (
    `id_estudiante` INT(11) NOT NULL AUTO_INCREMENT,
    `cedula` VARCHAR(20) NOT NULL,
    `nombre` VARCHAR(100) NOT NULL,
    `apellido` VARCHAR(100) NOT NULL,
    `genero` ENUM('M', 'F') NOT NULL COMMENT 'M=Masculino, F=Femenino',
    `id_seccion` INT(11) NOT NULL,
    `activo` BOOLEAN DEFAULT TRUE COMMENT 'Estudiante activo en el sistema',
    `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_estudiante`),
    UNIQUE KEY `unique_cedula` (`cedula`),
    INDEX `idx_cedula` (`cedula`),
    CONSTRAINT `fk_estudiante_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 7. CREATE TABLE asistencia_estudiante (vacía)
-- =====================================================
CREATE TABLE IF NOT EXISTS `asistencia_estudiante` (
    `id_asistencia_estudiante` INT(11) NOT NULL AUTO_INCREMENT,
    `id_estudiante` INT(11) NOT NULL,
    `fecha` DATE NOT NULL,
    `presente` BOOLEAN DEFAULT FALSE NOT NULL COMMENT 'TRUE=Presente, FALSE=Ausente',
    `observaciones` TEXT DEFAULT NULL COMMENT 'Observaciones opcionales',
    `id_usuario` INT(11) DEFAULT NULL COMMENT 'Usuario que registró',
    `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_asistencia_estudiante`),
    UNIQUE KEY `unique_asistencia_estudiante` (`id_estudiante`, `fecha`),
    INDEX `idx_fecha_presente` (`fecha`, `presente`),
    CONSTRAINT `fk_asistest_estudiante` FOREIGN KEY (`id_estudiante`) REFERENCES `estudiante` (`id_estudiante`) ON DELETE CASCADE,
    CONSTRAINT `fk_asistest_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 8. CREATE TABLE asistencia_legacy
-- =====================================================
CREATE TABLE IF NOT EXISTS `asistencia_legacy` (
    `id_asistencia` INT(11) NOT NULL AUTO_INCREMENT,
    `id_seccion_legacy` INT(11) NOT NULL COMMENT 'Referencia a secciones antiguas',
    `id_usuario` INT(11) DEFAULT NULL,
    `fecha` DATE NOT NULL,
    `asistentes_h` INT(11) DEFAULT 0,
    `asistentes_m` INT(11) DEFAULT 0,
    PRIMARY KEY (`id_asistencia`),
    UNIQUE KEY `unique_asistencia_legacy` (`id_seccion_legacy`, `fecha`),
    INDEX `idx_fecha_legacy` (`fecha`),
    CONSTRAINT `fk_asistlegacy_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Copiar datos desde asistencia V1
INSERT IGNORE INTO `asistencia_legacy` (`id_asistencia`, `id_seccion_legacy`, `id_usuario`, `fecha`, `asistentes_h`, `asistentes_m`)
    SELECT `id_asistencia`, `id_seccion`, `id_usuario`, `fecha`, `asistentes_h`, `asistentes_m`
    FROM `asistencia`;

-- =====================================================
-- 9. CREATE TABLE observacion_seccion
-- =====================================================
CREATE TABLE IF NOT EXISTS `observacion_seccion` (
    `id_observacion` INT(11) NOT NULL AUTO_INCREMENT,
    `id_seccion` INT(11) NOT NULL,
    `fecha` DATE NOT NULL,
    `observaciones` TEXT DEFAULT NULL COMMENT 'Observaciones generales de la clase',
    `id_usuario` INT(11) DEFAULT NULL COMMENT 'Usuario que registró la observación',
    `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_observacion`),
    UNIQUE KEY `unique_observacion_seccion` (`id_seccion`, `fecha`),
    CONSTRAINT `fk_obs_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`) ON DELETE CASCADE,
    CONSTRAINT `fk_obs_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 10. VIEWS útiles
-- =====================================================
CREATE OR REPLACE VIEW `vista_secciones_completa` AS
SELECT
    s.id_seccion,
    s.nombre_seccion,
    g.id_grado,
    g.nombre_grado,
    e.id_etapa,
    e.nombre_etapa,
    CONCAT(g.nombre_grado, ' ', s.nombre_seccion) AS nombre_completo
FROM `seccion` s
JOIN `grado` g ON s.id_grado = g.id_grado
JOIN `etapa` e ON g.id_etapa = e.id_etapa
WHERE s.activa = TRUE AND g.activo = TRUE AND e.activa = TRUE;

CREATE OR REPLACE VIEW `vista_estudiantes_completa` AS
SELECT
    est.id_estudiante,
    est.cedula,
    est.nombre,
    est.apellido,
    est.genero,
    est.activo,
    s.id_seccion,
    s.nombre_seccion,
    g.id_grado,
    g.nombre_grado,
    e.id_etapa,
    e.nombre_etapa,
    CONCAT(g.nombre_grado, ' ', s.nombre_seccion) AS seccion_completa
FROM `estudiante` est
JOIN `seccion` s ON est.id_seccion = s.id_seccion
JOIN `grado` g ON s.id_grado = g.id_grado
JOIN `etapa` e ON g.id_etapa = e.id_etapa;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- FIN DE MIGRACIÓN
-- Tablas V1 preservadas: secciones, profesor_secciones, matricula, asistencia
-- =====================================================
