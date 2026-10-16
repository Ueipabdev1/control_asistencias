CREATE TABLE IF NOT EXISTS `anio_escolar` (
    `id_anio_escolar` INT(11) NOT NULL AUTO_INCREMENT,
    `nombre` VARCHAR(9) NOT NULL,
    `codigo` VARCHAR(4) NOT NULL,
    `fecha_inicio` DATE NOT NULL,
    `fecha_fin` DATE NOT NULL,
    `es_actual` BOOLEAN NOT NULL DEFAULT FALSE,
    `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_anio_escolar`),
    UNIQUE KEY `unique_anio_escolar_nombre` (`nombre`),
    UNIQUE KEY `unique_anio_escolar_codigo` (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `anio_escolar` (`id_anio_escolar`, `nombre`, `codigo`, `fecha_inicio`, `fecha_fin`, `es_actual`) VALUES
    (1, '2025-2026', '2526', '2025-09-01', '2026-08-31', TRUE),
    (2, '2026-2027', '2627', '2026-09-01', '2027-08-31', FALSE);

ALTER TABLE `seccion`
    ADD COLUMN IF NOT EXISTS `id_anio_escolar` INT(11) NULL;

ALTER TABLE `asistencia_estudiante`
    ADD COLUMN IF NOT EXISTS `id_inscripcion` INT(11) NULL;

CREATE TABLE IF NOT EXISTS `inscripcion` (
    `id_inscripcion` INT(11) NOT NULL AUTO_INCREMENT,
    `id_estudiante` INT(11) NOT NULL,
    `id_seccion` INT(11) NOT NULL,
    `id_anio_escolar` INT(11) NOT NULL,
    `estado` ENUM('activo', 'promovido', 'graduado', 'retirado', 'inactivo') NOT NULL DEFAULT 'activo',
    `origen` VARCHAR(50) DEFAULT NULL,
    `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_inscripcion`),
    UNIQUE KEY `unique_inscripcion_estudiante_anio` (`id_estudiante`, `id_anio_escolar`),
    UNIQUE KEY `unique_inscripcion_estudiante` (`id_estudiante`, `id_inscripcion`),
    KEY `idx_inscripcion_anio_seccion_estado` (`id_anio_escolar`, `id_seccion`, `estado`),
    KEY `idx_inscripcion_seccion` (`id_seccion`),
    CONSTRAINT `fk_inscripcion_estudiante` FOREIGN KEY (`id_estudiante`) REFERENCES `estudiante` (`id_estudiante`) ON DELETE RESTRICT,
    CONSTRAINT `fk_inscripcion_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`) ON DELETE RESTRICT,
    CONSTRAINT `fk_inscripcion_anio` FOREIGN KEY (`id_anio_escolar`) REFERENCES `anio_escolar` (`id_anio_escolar`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX IF NOT EXISTS `idx_asistencia_inscripcion` ON `asistencia_estudiante` (`id_inscripcion`);
