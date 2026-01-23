-- =====================================================
-- Script de Datos de Prueba - Control de Asistencias
-- Genera datos para un mes completo (Diciembre 2025)
-- =====================================================

USE control_asistencias;

-- Limpiar datos existentes (mantener estructura)
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE asistencia;
TRUNCATE TABLE profesor_secciones;
TRUNCATE TABLE matricula;
TRUNCATE TABLE usuario;
SET FOREIGN_KEY_CHECKS = 1;

-- Reiniciar AUTO_INCREMENT
ALTER TABLE usuario AUTO_INCREMENT = 1;

-- =====================================================
-- USUARIOS (Administradores y Profesores)
-- =====================================================
-- Contraseña para todos: "password123" (hasheada con bcrypt)
-- Hash bcrypt de "password123": $2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G

INSERT INTO usuario (nombre, apellido, email, contraseña, rol) VALUES
-- Administradores
('Carlos', 'Rodríguez', 'admin@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'administrador'),
('María', 'González', 'maria.gonzalez@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'administrador'),

-- Profesores de Maternal
('Ana', 'Martínez', 'ana.martinez@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Luis', 'Pérez', 'luis.perez@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Carmen', 'Silva', 'carmen.silva@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),

-- Profesores de Primaria
('Roberto', 'Fernández', 'roberto.fernandez@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Patricia', 'López', 'patricia.lopez@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Jorge', 'Ramírez', 'jorge.ramirez@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Elena', 'Torres', 'elena.torres@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Miguel', 'Vargas', 'miguel.vargas@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Sandra', 'Morales', 'sandra.morales@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),

-- Profesores de Secundaria
('Fernando', 'Castro', 'fernando.castro@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Gabriela', 'Mendoza', 'gabriela.mendoza@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Ricardo', 'Herrera', 'ricardo.herrera@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Daniela', 'Ortiz', 'daniela.ortiz@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor'),
('Alberto', 'Ruiz', 'alberto.ruiz@ueipab.edu', '$2b$12$fdxAipue2Wa4it/dGEfiaOo.iVzYwei11nwLNzCxDboGR5dEG4e/G', 'profesor');

-- =====================================================
-- MATRÍCULA POR SECCIÓN
-- =====================================================
INSERT INTO matricula (id_seccion, num_estudiantes_h, num_estudiantes_m) VALUES
-- Maternal (secciones 1-3)
(1, 12, 10),  -- Nivel 1 maternal: 22 estudiantes
(2, 14, 12),  -- Nivel 2 maternal: 26 estudiantes
(3, 11, 13),  -- Nivel 3 maternal: 24 estudiantes

-- Primaria (secciones 4-9)
(4, 15, 14),  -- 1er grado: 29 estudiantes
(5, 16, 15),  -- 2do grado: 31 estudiantes
(6, 14, 16),  -- 3er grado: 30 estudiantes
(7, 17, 13),  -- 4to grado: 30 estudiantes
(8, 15, 15),  -- 5to grado: 30 estudiantes
(9, 16, 14),  -- 6to grado: 30 estudiantes

-- Secundaria (secciones 10-15)
(10, 18, 17), -- 1er año: 35 estudiantes
(11, 19, 16), -- 2do año: 35 estudiantes
(12, 17, 18), -- 3er año A: 35 estudiantes
(13, 16, 19), -- 3er año B: 35 estudiantes
(14, 20, 15), -- 4to año: 35 estudiantes
(15, 18, 17); -- 5to año: 35 estudiantes

-- =====================================================
-- ASIGNACIÓN DE PROFESORES A SECCIONES
-- =====================================================
-- IDs de usuarios: 1-2 (Admins), 3-16 (Profesores)
INSERT INTO profesor_secciones (id_profesor, id_seccion) VALUES
-- Maternal (profesores 3, 4, 5)
(3, 1),  -- Ana Martínez -> Nivel 1 maternal
(4, 2),  -- Luis Pérez -> Nivel 2 maternal
(5, 3),  -- Carmen Silva -> Nivel 3 maternal

-- Primaria (profesores 6-11)
(6, 4),  -- Roberto Fernández -> 1er grado
(7, 5),  -- Patricia López -> 2do grado
(8, 6),  -- Jorge Ramírez -> 3er grado
(9, 7),  -- Elena Torres -> 4to grado
(10, 8), -- Miguel Vargas -> 5to grado
(11, 9), -- Sandra Morales -> 6to grado

-- Secundaria (profesores 12-16)
(12, 10), -- Fernando Castro -> 1er año
(13, 11), -- Gabriela Mendoza -> 2do año
(14, 12), -- Ricardo Herrera -> 3er año A
(15, 13), -- Daniela Ortiz -> 3er año B
(16, 14), -- Alberto Ruiz -> 4to año
(12, 15); -- Fernando Castro -> 5to año (profesor con 2 secciones)

-- =====================================================
-- ASISTENCIAS - DICIEMBRE 2025 (1 mes completo)
-- Días laborables: Lunes a Viernes
-- =====================================================

-- Semana 1: 1-5 Diciembre 2025 (Lunes a Viernes)
INSERT INTO asistencia (id_seccion, fecha, asistentes_h, asistentes_m) VALUES
-- Lunes 1 Diciembre
(1, '2025-12-01', 11, 9), (2, '2025-12-01', 13, 11), (3, '2025-12-01', 10, 12),
(4, '2025-12-01', 14, 13), (5, '2025-12-01', 15, 14), (6, '2025-12-01', 13, 15),
(7, '2025-12-01', 16, 12), (8, '2025-12-01', 14, 14), (9, '2025-12-01', 15, 13),
(10, '2025-12-01', 17, 16), (11, '2025-12-01', 18, 15), (12, '2025-12-01', 16, 17),
(13, '2025-12-01', 15, 18), (14, '2025-12-01', 19, 14), (15, '2025-12-01', 17, 16),

-- Martes 2 Diciembre
(1, '2025-12-02', 12, 10), (2, '2025-12-02', 14, 12), (3, '2025-12-02', 11, 13),
(4, '2025-12-02', 15, 14), (5, '2025-12-02', 16, 15), (6, '2025-12-02', 14, 16),
(7, '2025-12-02', 17, 13), (8, '2025-12-02', 15, 15), (9, '2025-12-02', 16, 14),
(10, '2025-12-02', 18, 17), (11, '2025-12-02', 19, 16), (12, '2025-12-02', 17, 18),
(13, '2025-12-02', 16, 19), (14, '2025-12-02', 20, 15), (15, '2025-12-02', 18, 17),

-- Miércoles 3 Diciembre
(1, '2025-12-03', 11, 10), (2, '2025-12-03', 13, 11), (3, '2025-12-03', 10, 12),
(4, '2025-12-03', 14, 13), (5, '2025-12-03', 15, 14), (6, '2025-12-03', 13, 15),
(7, '2025-12-03', 16, 12), (8, '2025-12-03', 14, 14), (9, '2025-12-03', 15, 13),
(10, '2025-12-03', 17, 16), (11, '2025-12-03', 18, 15), (12, '2025-12-03', 16, 17),
(13, '2025-12-03', 15, 18), (14, '2025-12-03', 19, 14), (15, '2025-12-03', 17, 16),

-- Jueves 4 Diciembre
(1, '2025-12-04', 12, 9), (2, '2025-12-04', 14, 12), (3, '2025-12-04', 11, 13),
(4, '2025-12-04', 15, 14), (5, '2025-12-04', 16, 15), (6, '2025-12-04', 14, 16),
(7, '2025-12-04', 17, 13), (8, '2025-12-04', 15, 15), (9, '2025-12-04', 16, 14),
(10, '2025-12-04', 18, 17), (11, '2025-12-04', 19, 16), (12, '2025-12-04', 17, 18),
(13, '2025-12-04', 16, 19), (14, '2025-12-04', 20, 15), (15, '2025-12-04', 18, 17),

-- Viernes 5 Diciembre
(1, '2025-12-05', 11, 10), (2, '2025-12-05', 13, 12), (3, '2025-12-05', 10, 13),
(4, '2025-12-05', 14, 14), (5, '2025-12-05', 15, 15), (6, '2025-12-05', 13, 16),
(7, '2025-12-05', 16, 13), (8, '2025-12-05', 14, 15), (9, '2025-12-05', 15, 14),
(10, '2025-12-05', 17, 17), (11, '2025-12-05', 18, 16), (12, '2025-12-05', 16, 18),
(13, '2025-12-05', 15, 19), (14, '2025-12-05', 19, 15), (15, '2025-12-05', 17, 17),

-- Semana 2: 8-12 Diciembre 2025
-- Lunes 8 Diciembre
(1, '2025-12-08', 12, 10), (2, '2025-12-08', 14, 12), (3, '2025-12-08', 11, 13),
(4, '2025-12-08', 15, 14), (5, '2025-12-08', 16, 15), (6, '2025-12-08', 14, 16),
(7, '2025-12-08', 17, 13), (8, '2025-12-08', 15, 15), (9, '2025-12-08', 16, 14),
(10, '2025-12-08', 18, 17), (11, '2025-12-08', 19, 16), (12, '2025-12-08', 17, 18),
(13, '2025-12-08', 16, 19), (14, '2025-12-08', 20, 15), (15, '2025-12-08', 18, 17),

-- Martes 9 Diciembre
(1, '2025-12-09', 11, 9), (2, '2025-12-09', 13, 11), (3, '2025-12-09', 10, 12),
(4, '2025-12-09', 14, 13), (5, '2025-12-09', 15, 14), (6, '2025-12-09', 13, 15),
(7, '2025-12-09', 16, 12), (8, '2025-12-09', 14, 14), (9, '2025-12-09', 15, 13),
(10, '2025-12-09', 17, 16), (11, '2025-12-09', 18, 15), (12, '2025-12-09', 16, 17),
(13, '2025-12-09', 15, 18), (14, '2025-12-09', 19, 14), (15, '2025-12-09', 17, 16),

-- Miércoles 10 Diciembre
(1, '2025-12-10', 12, 10), (2, '2025-12-10', 14, 12), (3, '2025-12-10', 11, 13),
(4, '2025-12-10', 15, 14), (5, '2025-12-10', 16, 15), (6, '2025-12-10', 14, 16),
(7, '2025-12-10', 17, 13), (8, '2025-12-10', 15, 15), (9, '2025-12-10', 16, 14),
(10, '2025-12-10', 18, 17), (11, '2025-12-10', 19, 16), (12, '2025-12-10', 17, 18),
(13, '2025-12-10', 16, 19), (14, '2025-12-10', 20, 15), (15, '2025-12-10', 18, 17),

-- Jueves 11 Diciembre
(1, '2025-12-11', 11, 10), (2, '2025-12-11', 13, 12), (3, '2025-12-11', 10, 13),
(4, '2025-12-11', 14, 14), (5, '2025-12-11', 15, 15), (6, '2025-12-11', 13, 16),
(7, '2025-12-11', 16, 13), (8, '2025-12-11', 14, 15), (9, '2025-12-11', 15, 14),
(10, '2025-12-11', 17, 17), (11, '2025-12-11', 18, 16), (12, '2025-12-11', 16, 18),
(13, '2025-12-11', 15, 19), (14, '2025-12-11', 19, 15), (15, '2025-12-11', 17, 17),

-- Viernes 12 Diciembre
(1, '2025-12-12', 12, 9), (2, '2025-12-12', 14, 11), (3, '2025-12-12', 11, 12),
(4, '2025-12-12', 15, 13), (5, '2025-12-12', 16, 14), (6, '2025-12-12', 14, 15),
(7, '2025-12-12', 17, 12), (8, '2025-12-12', 15, 14), (9, '2025-12-12', 16, 13),
(10, '2025-12-12', 18, 16), (11, '2025-12-12', 19, 15), (12, '2025-12-12', 17, 17),
(13, '2025-12-12', 16, 18), (14, '2025-12-12', 20, 14), (15, '2025-12-12', 18, 16),

-- Semana 3: 15-19 Diciembre 2025
-- Lunes 15 Diciembre
(1, '2025-12-15', 11, 10), (2, '2025-12-15', 13, 12), (3, '2025-12-15', 10, 13),
(4, '2025-12-15', 14, 14), (5, '2025-12-15', 15, 15), (6, '2025-12-15', 13, 16),
(7, '2025-12-15', 16, 13), (8, '2025-12-15', 14, 15), (9, '2025-12-15', 15, 14),
(10, '2025-12-15', 17, 17), (11, '2025-12-15', 18, 16), (12, '2025-12-15', 16, 18),
(13, '2025-12-15', 15, 19), (14, '2025-12-15', 19, 15), (15, '2025-12-15', 17, 17),

-- Martes 16 Diciembre
(1, '2025-12-16', 12, 10), (2, '2025-12-16', 14, 12), (3, '2025-12-16', 11, 13),
(4, '2025-12-16', 15, 14), (5, '2025-12-16', 16, 15), (6, '2025-12-16', 14, 16),
(7, '2025-12-16', 17, 13), (8, '2025-12-16', 15, 15), (9, '2025-12-16', 16, 14),
(10, '2025-12-16', 18, 17), (11, '2025-12-16', 19, 16), (12, '2025-12-16', 17, 18),
(13, '2025-12-16', 16, 19), (14, '2025-12-16', 20, 15), (15, '2025-12-16', 18, 17),

-- Miércoles 17 Diciembre
(1, '2025-12-17', 11, 9), (2, '2025-12-17', 13, 11), (3, '2025-12-17', 10, 12),
(4, '2025-12-17', 14, 13), (5, '2025-12-17', 15, 14), (6, '2025-12-17', 13, 15),
(7, '2025-12-17', 16, 12), (8, '2025-12-17', 14, 14), (9, '2025-12-17', 15, 13),
(10, '2025-12-17', 17, 16), (11, '2025-12-17', 18, 15), (12, '2025-12-17', 16, 17),
(13, '2025-12-17', 15, 18), (14, '2025-12-17', 19, 14), (15, '2025-12-17', 17, 16),

-- Jueves 18 Diciembre
(1, '2025-12-18', 12, 10), (2, '2025-12-18', 14, 12), (3, '2025-12-18', 11, 13),
(4, '2025-12-18', 15, 14), (5, '2025-12-18', 16, 15), (6, '2025-12-18', 14, 16),
(7, '2025-12-18', 17, 13), (8, '2025-12-18', 15, 15), (9, '2025-12-18', 16, 14),
(10, '2025-12-18', 18, 17), (11, '2025-12-18', 19, 16), (12, '2025-12-18', 17, 18),
(13, '2025-12-18', 16, 19), (14, '2025-12-18', 20, 15), (15, '2025-12-18', 18, 17),

-- Viernes 19 Diciembre
(1, '2025-12-19', 11, 10), (2, '2025-12-19', 13, 12), (3, '2025-12-19', 10, 13),
(4, '2025-12-19', 14, 14), (5, '2025-12-19', 15, 15), (6, '2025-12-19', 13, 16),
(7, '2025-12-19', 16, 13), (8, '2025-12-19', 14, 15), (9, '2025-12-19', 15, 14),
(10, '2025-12-19', 17, 17), (11, '2025-12-19', 18, 16), (12, '2025-12-19', 16, 18),
(13, '2025-12-19', 15, 19), (14, '2025-12-19', 19, 15), (15, '2025-12-19', 17, 17),

-- Semana 4: 22-26 Diciembre 2025 (Semana de Navidad - asistencia reducida)
-- Lunes 22 Diciembre
(1, '2025-12-22', 10, 8), (2, '2025-12-22', 12, 10), (3, '2025-12-22', 9, 11),
(4, '2025-12-22', 13, 12), (5, '2025-12-22', 14, 13), (6, '2025-12-22', 12, 14),
(7, '2025-12-22', 15, 11), (8, '2025-12-22', 13, 13), (9, '2025-12-22', 14, 12),
(10, '2025-12-22', 16, 15), (11, '2025-12-22', 17, 14), (12, '2025-12-22', 15, 16),
(13, '2025-12-22', 14, 17), (14, '2025-12-22', 18, 13), (15, '2025-12-22', 16, 15),

-- Martes 23 Diciembre
(1, '2025-12-23', 9, 7), (2, '2025-12-23', 11, 9), (3, '2025-12-23', 8, 10),
(4, '2025-12-23', 12, 11), (5, '2025-12-23', 13, 12), (6, '2025-12-23', 11, 13),
(7, '2025-12-23', 14, 10), (8, '2025-12-23', 12, 12), (9, '2025-12-23', 13, 11),
(10, '2025-12-23', 15, 14), (11, '2025-12-23', 16, 13), (12, '2025-12-23', 14, 15),
(13, '2025-12-23', 13, 16), (14, '2025-12-23', 17, 12), (15, '2025-12-23', 15, 14),

-- Miércoles 24 Diciembre (Nochebuena - asistencia muy baja)
(1, '2025-12-24', 6, 5), (2, '2025-12-24', 7, 6), (3, '2025-12-24', 5, 7),
(4, '2025-12-24', 8, 7), (5, '2025-12-24', 9, 8), (6, '2025-12-24', 7, 9),
(7, '2025-12-24', 10, 7), (8, '2025-12-24', 8, 8), (9, '2025-12-24', 9, 7),
(10, '2025-12-24', 11, 10), (11, '2025-12-24', 12, 9), (12, '2025-12-24', 10, 11),
(13, '2025-12-24', 9, 12), (14, '2025-12-24', 13, 8), (15, '2025-12-24', 11, 10),

-- Semana 5: 29-31 Diciembre 2025 (Fin de año - asistencia baja)
-- Lunes 29 Diciembre
(1, '2025-12-29', 8, 7), (2, '2025-12-29', 10, 8), (3, '2025-12-29', 7, 9),
(4, '2025-12-29', 11, 10), (5, '2025-12-29', 12, 11), (6, '2025-12-29', 10, 12),
(7, '2025-12-29', 13, 9), (8, '2025-12-29', 11, 11), (9, '2025-12-29', 12, 10),
(10, '2025-12-29', 14, 13), (11, '2025-12-29', 15, 12), (12, '2025-12-29', 13, 14),
(13, '2025-12-29', 12, 15), (14, '2025-12-29', 16, 11), (15, '2025-12-29', 14, 13),

-- Martes 30 Diciembre
(1, '2025-12-30', 7, 6), (2, '2025-12-30', 9, 7), (3, '2025-12-30', 6, 8),
(4, '2025-12-30', 10, 9), (5, '2025-12-30', 11, 10), (6, '2025-12-30', 9, 11),
(7, '2025-12-30', 12, 8), (8, '2025-12-30', 10, 10), (9, '2025-12-30', 11, 9),
(10, '2025-12-30', 13, 12), (11, '2025-12-30', 14, 11), (12, '2025-12-30', 12, 13),
(13, '2025-12-30', 11, 14), (14, '2025-12-30', 15, 10), (15, '2025-12-30', 13, 12),

-- Miércoles 31 Diciembre (Fin de año - asistencia muy baja)
(1, '2025-12-31', 5, 4), (2, '2025-12-31', 6, 5), (3, '2025-12-31', 4, 6),
(4, '2025-12-31', 7, 6), (5, '2025-12-31', 8, 7), (6, '2025-12-31', 6, 8),
(7, '2025-12-31', 9, 6), (8, '2025-12-31', 7, 7), (9, '2025-12-31', 8, 6),
(10, '2025-12-31', 10, 9), (11, '2025-12-31', 11, 8), (12, '2025-12-31', 9, 10),
(13, '2025-12-31', 8, 11), (14, '2025-12-31', 12, 7), (15, '2025-12-31', 10, 9);

-- =====================================================
-- RESUMEN DE DATOS INSERTADOS
-- =====================================================
SELECT 'RESUMEN DE DATOS INSERTADOS' as '';
SELECT COUNT(*) as 'Total Usuarios', 
       SUM(CASE WHEN rol = 'administrador' THEN 1 ELSE 0 END) as 'Administradores',
       SUM(CASE WHEN rol = 'profesor' THEN 1 ELSE 0 END) as 'Profesores'
FROM usuario;

SELECT COUNT(*) as 'Total Secciones' FROM secciones;
SELECT COUNT(*) as 'Total Matrículas' FROM matricula;
SELECT SUM(num_estudiantes_h + num_estudiantes_m) as 'Total Estudiantes Matriculados' FROM matricula;
SELECT COUNT(*) as 'Total Asignaciones Profesor-Sección' FROM profesor_secciones;
SELECT COUNT(*) as 'Total Registros de Asistencia' FROM asistencia;
SELECT MIN(fecha) as 'Primera Fecha', MAX(fecha) as 'Última Fecha' FROM asistencia;

SELECT 'Script ejecutado exitosamente!' as '';
