-- Current as-is schema baseline for isolated development and testing.
-- Schema only: no table data, routines, events, triggers, or database-selection directives.
/*M!999999\- enable the sandbox mode */

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;
DROP TABLE IF EXISTS `asistencia`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `asistencia` (
  `id_asistencia` int(11) NOT NULL AUTO_INCREMENT,
  `id_seccion` int(11) NOT NULL,
  `id_usuario` int(11) DEFAULT NULL COMMENT 'Usuario que registró la asistencia',
  `fecha` date NOT NULL,
  `asistentes_h` int(11) DEFAULT 0 COMMENT 'Estudiantes hombres presentes',
  `asistentes_m` int(11) DEFAULT 0 COMMENT 'Estudiantes mujeres presentes',
  PRIMARY KEY (`id_asistencia`),
  UNIQUE KEY `unique_asistencia` (`id_seccion`,`fecha`),
  KEY `idx_fecha` (`fecha`),
  KEY `idx_asistencia_usuario` (`id_usuario`),
  CONSTRAINT `asistencia_ibfk_1` FOREIGN KEY (`id_seccion`) REFERENCES `secciones` (`id_seccion`) ON DELETE CASCADE,
  CONSTRAINT `fk_asistencia_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `asistencia_estudiante`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `asistencia_estudiante` (
  `id_asistencia_estudiante` int(11) NOT NULL AUTO_INCREMENT,
  `id_estudiante` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `bloque` enum('completo','bloque_1','bloque_2','bloque_3','bloque_4') NOT NULL DEFAULT 'completo' COMMENT 'Bloque de clase: completo=todo el dia',
  `presente` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'TRUE=Presente, FALSE=Ausente',
  `observaciones` text DEFAULT NULL COMMENT 'Observaciones opcionales',
  `id_usuario` int(11) DEFAULT NULL COMMENT 'Usuario que registró',
  `fecha_registro` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_asistencia_estudiante`),
  UNIQUE KEY `unique_asistencia_estudiante_bloque` (`id_estudiante`,`fecha`,`bloque`),
  KEY `idx_fecha_presente` (`fecha`,`presente`),
  KEY `fk_asistest_usuario` (`id_usuario`),
  CONSTRAINT `fk_asistest_estudiante` FOREIGN KEY (`id_estudiante`) REFERENCES `estudiante` (`id_estudiante`) ON DELETE CASCADE,
  CONSTRAINT `fk_asistest_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=39010 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `asistencia_legacy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `asistencia_legacy` (
  `id_asistencia` int(11) NOT NULL AUTO_INCREMENT,
  `id_seccion_legacy` int(11) NOT NULL COMMENT 'Referencia a secciones antiguas',
  `id_usuario` int(11) DEFAULT NULL,
  `fecha` date NOT NULL,
  `asistentes_h` int(11) DEFAULT 0,
  `asistentes_m` int(11) DEFAULT 0,
  PRIMARY KEY (`id_asistencia`),
  UNIQUE KEY `unique_asistencia_legacy` (`id_seccion_legacy`,`fecha`),
  KEY `idx_fecha_legacy` (`fecha`),
  KEY `fk_asistlegacy_usuario` (`id_usuario`),
  CONSTRAINT `fk_asistlegacy_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `calendario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `calendario` (
  `id_calendario` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` date NOT NULL,
  `tipo_dia` enum('habil','feriado','suspension','fin_semana') NOT NULL DEFAULT 'habil',
  `descripcion` varchar(255) DEFAULT NULL COMMENT 'Descripción del día (nombre del feriado, motivo de suspensión, etc.)',
  `es_laborable` tinyint(1) DEFAULT 1 COMMENT 'Indica si es un día laborable para el personal',
  `observaciones` text DEFAULT NULL COMMENT 'Observaciones adicionales',
  `fecha_creacion` timestamp NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_calendario`),
  UNIQUE KEY `fecha` (`fecha`),
  KEY `idx_fecha` (`fecha`),
  KEY `idx_tipo_dia` (`tipo_dia`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `calendario_escolar`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `calendario_escolar` (
  `id_calendario` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` date NOT NULL,
  `tipo` enum('feriado','vacaciones','suspension','otro') NOT NULL,
  `descripcion` varchar(255) NOT NULL,
  `activo` tinyint(1) DEFAULT 1,
  `fecha_creacion` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_calendario`),
  UNIQUE KEY `fecha` (`fecha`),
  KEY `idx_fecha` (`fecha`),
  KEY `idx_tipo` (`tipo`),
  KEY `idx_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `estudiante`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `estudiante` (
  `id_estudiante` int(11) NOT NULL AUTO_INCREMENT,
  `cedula` varchar(20) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `genero` enum('M','F') NOT NULL COMMENT 'M=Masculino, F=Femenino',
  `id_seccion` int(11) NOT NULL,
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Estudiante activo en el sistema',
  `fecha_registro` timestamp NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_estudiante`),
  UNIQUE KEY `unique_cedula` (`cedula`),
  KEY `idx_cedula` (`cedula`),
  KEY `fk_estudiante_seccion` (`id_seccion`),
  CONSTRAINT `fk_estudiante_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`)
) ENGINE=InnoDB AUTO_INCREMENT=228 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `etapa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `etapa` (
  `id_etapa` int(11) NOT NULL AUTO_INCREMENT,
  `nombre_etapa` varchar(50) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activa` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_etapa`),
  UNIQUE KEY `nombre_etapa` (`nombre_etapa`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `grado`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `grado` (
  `id_grado` int(11) NOT NULL AUTO_INCREMENT,
  `id_etapa` int(11) NOT NULL,
  `nombre_grado` varchar(100) NOT NULL,
  `orden` int(11) NOT NULL COMMENT 'Orden del grado dentro de la etapa',
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_grado`),
  UNIQUE KEY `unique_grado_etapa` (`id_etapa`,`nombre_grado`),
  CONSTRAINT `fk_grado_etapa` FOREIGN KEY (`id_etapa`) REFERENCES `etapa` (`id_etapa`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `matricula`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `matricula` (
  `id_matricula` int(11) NOT NULL AUTO_INCREMENT,
  `id_seccion` int(11) NOT NULL,
  `num_estudiantes_h` int(11) DEFAULT 0 COMMENT 'Número de estudiantes hombres',
  `num_estudiantes_m` int(11) DEFAULT 0 COMMENT 'Número de estudiantes mujeres',
  `fecha_actualizacion` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_matricula`),
  UNIQUE KEY `unique_seccion` (`id_seccion`),
  CONSTRAINT `matricula_ibfk_1` FOREIGN KEY (`id_seccion`) REFERENCES `secciones` (`id_seccion`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `observacion_seccion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `observacion_seccion` (
  `id_observacion` int(11) NOT NULL AUTO_INCREMENT,
  `id_seccion` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `observaciones` text DEFAULT NULL COMMENT 'Observaciones generales de la clase',
  `id_usuario` int(11) DEFAULT NULL COMMENT 'Usuario que registró la observación',
  `fecha_registro` timestamp NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_observacion`),
  UNIQUE KEY `unique_observacion_seccion` (`id_seccion`,`fecha`),
  KEY `fk_obs_usuario` (`id_usuario`),
  CONSTRAINT `fk_obs_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`) ON DELETE CASCADE,
  CONSTRAINT `fk_obs_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=1254 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `profesor_seccion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `profesor_seccion` (
  `id_profesor_seccion` int(11) NOT NULL AUTO_INCREMENT,
  `id_profesor` int(11) NOT NULL,
  `id_seccion` int(11) NOT NULL,
  `fecha_asignacion` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_profesor_seccion`),
  UNIQUE KEY `unique_profesor_seccion` (`id_profesor`,`id_seccion`),
  KEY `fk_profsec_seccion` (`id_seccion`),
  CONSTRAINT `fk_profsec_profesor` FOREIGN KEY (`id_profesor`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE,
  CONSTRAINT `fk_profsec_seccion` FOREIGN KEY (`id_seccion`) REFERENCES `seccion` (`id_seccion`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `profesor_secciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `profesor_secciones` (
  `id_profesor_seccion` int(11) NOT NULL AUTO_INCREMENT,
  `id_profesor` int(11) NOT NULL,
  `id_seccion` int(11) NOT NULL,
  PRIMARY KEY (`id_profesor_seccion`),
  UNIQUE KEY `unique_profesor_seccion` (`id_profesor`,`id_seccion`),
  KEY `id_seccion` (`id_seccion`),
  CONSTRAINT `profesor_secciones_ibfk_1` FOREIGN KEY (`id_profesor`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE,
  CONSTRAINT `profesor_secciones_ibfk_2` FOREIGN KEY (`id_seccion`) REFERENCES `secciones` (`id_seccion`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `seccion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `seccion` (
  `id_seccion` int(11) NOT NULL AUTO_INCREMENT,
  `id_grado` int(11) NOT NULL,
  `nombre_seccion` varchar(50) NOT NULL,
  `activa` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_seccion`),
  KEY `fk_seccion_grado` (`id_grado`),
  CONSTRAINT `fk_seccion_grado` FOREIGN KEY (`id_grado`) REFERENCES `grado` (`id_grado`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `secciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `secciones` (
  `id_seccion` int(11) NOT NULL AUTO_INCREMENT,
  `nombre_seccion` varchar(50) NOT NULL,
  `id_etapa` int(11) NOT NULL,
  PRIMARY KEY (`id_seccion`),
  KEY `idx_etapa` (`id_etapa`),
  CONSTRAINT `secciones_ibfk_1` FOREIGN KEY (`id_etapa`) REFERENCES `etapa` (`id_etapa`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `usuario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario` (
  `id_usuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `contraseña` varchar(255) NOT NULL,
  `rol` enum('administrador','profesor') NOT NULL,
  `fecha_creacion` timestamp NULL DEFAULT current_timestamp(),
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_rol` (`rol`)
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `vista_estudiantes_completa`;
/*!50001 DROP VIEW IF EXISTS `vista_estudiantes_completa`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `vista_estudiantes_completa` AS SELECT
 1 AS `id_estudiante`,
  1 AS `cedula`,
  1 AS `nombre`,
  1 AS `apellido`,
  1 AS `genero`,
  1 AS `activo`,
  1 AS `id_seccion`,
  1 AS `nombre_seccion`,
  1 AS `id_grado`,
  1 AS `nombre_grado`,
  1 AS `id_etapa`,
  1 AS `nombre_etapa`,
  1 AS `seccion_completa` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `vista_secciones_completa`;
/*!50001 DROP VIEW IF EXISTS `vista_secciones_completa`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `vista_secciones_completa` AS SELECT
 1 AS `id_seccion`,
  1 AS `nombre_seccion`,
  1 AS `id_grado`,
  1 AS `nombre_grado`,
  1 AS `id_etapa`,
  1 AS `nombre_etapa`,
  1 AS `nombre_completo` */;
SET character_set_client = @saved_cs_client;
/*!50001 DROP VIEW IF EXISTS `vista_estudiantes_completa`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=CURRENT_USER SQL SECURITY DEFINER */
/*!50001 VIEW `vista_estudiantes_completa` AS select `est`.`id_estudiante` AS `id_estudiante`,`est`.`cedula` AS `cedula`,`est`.`nombre` AS `nombre`,`est`.`apellido` AS `apellido`,`est`.`genero` AS `genero`,`est`.`activo` AS `activo`,`s`.`id_seccion` AS `id_seccion`,`s`.`nombre_seccion` AS `nombre_seccion`,`g`.`id_grado` AS `id_grado`,`g`.`nombre_grado` AS `nombre_grado`,`e`.`id_etapa` AS `id_etapa`,`e`.`nombre_etapa` AS `nombre_etapa`,concat(`g`.`nombre_grado`,' ',`s`.`nombre_seccion`) AS `seccion_completa` from (((`estudiante` `est` join `seccion` `s` on(`est`.`id_seccion` = `s`.`id_seccion`)) join `grado` `g` on(`s`.`id_grado` = `g`.`id_grado`)) join `etapa` `e` on(`g`.`id_etapa` = `e`.`id_etapa`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `vista_secciones_completa`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=CURRENT_USER SQL SECURITY DEFINER */
/*!50001 VIEW `vista_secciones_completa` AS select `s`.`id_seccion` AS `id_seccion`,`s`.`nombre_seccion` AS `nombre_seccion`,`g`.`id_grado` AS `id_grado`,`g`.`nombre_grado` AS `nombre_grado`,`e`.`id_etapa` AS `id_etapa`,`e`.`nombre_etapa` AS `nombre_etapa`,concat(`g`.`nombre_grado`,' ',`s`.`nombre_seccion`) AS `nombre_completo` from ((`seccion` `s` join `grado` `g` on(`s`.`id_grado` = `g`.`id_grado`)) join `etapa` `e` on(`g`.`id_etapa` = `e`.`id_etapa`)) where `s`.`activa` = 1 and `g`.`activo` = 1 and `e`.`activa` = 1 */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;
