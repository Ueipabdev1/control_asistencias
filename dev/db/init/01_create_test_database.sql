CREATE DATABASE IF NOT EXISTS control_asistencias_test
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON control_asistencias_test.* TO 'asistencias_dev'@'%';
GRANT ALL PRIVILEGES ON control_asistencias_dev.* TO 'asistencias_dev'@'%';
FLUSH PRIVILEGES;
