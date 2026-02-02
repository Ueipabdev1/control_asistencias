# Guía de Migración de Base de Datos MariaDB a Railway

Esta guía te ayudará a migrar tu base de datos MariaDB local a Railway MySQL.

## 📋 Opciones de Migración

Railway usa MySQL (compatible con MariaDB), así que puedes migrar tus datos fácilmente.

### **Opción 1: Usar los Scripts SQL (Recomendado para Nuevo Despliegue)**

Si estás desplegando por primera vez y solo necesitas la estructura y datos de prueba:

#### Pasos:

1. **Conectar a Railway MySQL usando Railway CLI:**
```bash
# Instalar Railway CLI
npm i -g @railway/cli

# Iniciar sesión
railway login

# Vincular tu proyecto
railway link

# Conectar a MySQL
railway connect MySQL
```

2. **Ejecutar los scripts SQL:**
```sql
-- Crear la estructura de la base de datos
source database_schema.sql;

-- Insertar datos de prueba
source seed_data.sql;
```

3. **Salir:**
```sql
exit;
```

---

### **Opción 2: Exportar e Importar Datos Existentes**

Si ya tienes datos reales en tu MariaDB local que quieres migrar:

#### **Paso 1: Exportar desde MariaDB Local**

**Método A: Usando mysqldump (Línea de Comandos)**

```bash
# Exportar toda la base de datos
mysqldump -u root -p control_asistencias > backup_control_asistencias.sql

# Si quieres exportar sin los datos de prueba, solo la estructura:
mysqldump -u root -p --no-data control_asistencias > estructura_control_asistencias.sql

# Si quieres exportar solo los datos (sin estructura):
mysqldump -u root -p --no-create-info control_asistencias > datos_control_asistencias.sql
```

**Método B: Usando HeidiSQL o MySQL Workbench**

1. Abre HeidiSQL o MySQL Workbench
2. Conecta a tu base de datos local
3. Selecciona la base de datos `control_asistencias`
4. Menú: **Herramientas** → **Exportar base de datos como SQL**
5. Selecciona:
   - ✅ Estructura de tablas
   - ✅ Datos
   - ✅ DROP TABLE IF EXISTS (opcional)
6. Guarda como `backup_control_asistencias.sql`

#### **Paso 2: Importar a Railway MySQL**

**Método A: Usando Railway CLI (Recomendado)**

```bash
# Conectar a Railway MySQL
railway connect MySQL

# Una vez dentro del cliente MySQL:
source backup_control_asistencias.sql;

# Verificar que se importó correctamente
SHOW TABLES;
SELECT COUNT(*) FROM usuario;

# Salir
exit;
```

**Método B: Usando MySQL Workbench o DBeaver**

1. **Obtener credenciales de Railway:**
   - Ve a tu proyecto en Railway
   - Haz clic en el servicio MySQL
   - Ve a la pestaña **"Variables"**
   - Copia:
     - `MYSQL_HOST`
     - `MYSQL_PORT`
     - `MYSQL_USER`
     - `MYSQL_PASSWORD`
     - `MYSQL_DATABASE`

2. **Conectar con MySQL Workbench:**
   - Abre MySQL Workbench
   - Nueva conexión:
     - **Hostname:** `MYSQL_HOST` (ej: containers-us-west-123.railway.app)
     - **Port:** `MYSQL_PORT` (ej: 6789)
     - **Username:** `MYSQL_USER` (generalmente "root")
     - **Password:** `MYSQL_PASSWORD`
     - **Default Schema:** `MYSQL_DATABASE` (generalmente "railway")
   - Haz clic en **"Test Connection"**
   - Si funciona, haz clic en **"OK"**

3. **Importar el archivo SQL:**
   - Menú: **Server** → **Data Import**
   - Selecciona **"Import from Self-Contained File"**
   - Busca tu archivo `backup_control_asistencias.sql`
   - En **"Default Target Schema"**, selecciona `railway`
   - Haz clic en **"Start Import"**

**Método C: Usando DBeaver**

1. **Nueva conexión:**
   - Tipo: MySQL
   - Host: `MYSQL_HOST`
   - Puerto: `MYSQL_PORT`
   - Base de datos: `MYSQL_DATABASE`
   - Usuario: `MYSQL_USER`
   - Contraseña: `MYSQL_PASSWORD`
   - Probar conexión

2. **Importar:**
   - Clic derecho en la base de datos
   - **Tools** → **Execute SQL Script**
   - Selecciona `backup_control_asistencias.sql`
   - Ejecutar

---

### **Opción 3: Migración Selectiva (Solo Datos Importantes)**

Si quieres migrar solo ciertos datos (por ejemplo, usuarios reales pero no datos de prueba):

#### **1. Exportar tablas específicas:**

```bash
# Exportar solo la tabla de usuarios
mysqldump -u root -p control_asistencias usuario > usuarios.sql

# Exportar varias tablas
mysqldump -u root -p control_asistencias usuario etapa seccion > tablas_importantes.sql
```

#### **2. Importar a Railway:**

```bash
railway connect MySQL
source usuarios.sql;
exit;
```

---

## 🔄 Script de Migración Automatizada

He aquí un script que puedes usar para automatizar la migración:

### **migrate_to_railway.sh** (Linux/Mac)

```bash
#!/bin/bash

echo "🚀 Migración de Base de Datos a Railway"
echo "========================================"

# Exportar base de datos local
echo "📦 Exportando base de datos local..."
mysqldump -u root -p control_asistencias > backup_$(date +%Y%m%d_%H%M%S).sql

# Conectar a Railway y importar
echo "☁️  Conectando a Railway..."
railway connect MySQL < backup_*.sql

echo "✅ Migración completada!"
```

### **migrate_to_railway.bat** (Windows)

```batch
@echo off
echo Migracion de Base de Datos a Railway
echo =====================================

REM Exportar base de datos local
echo Exportando base de datos local...
mysqldump -u root -p control_asistencias > backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql

echo Migracion completada!
echo Ahora ejecuta: railway connect MySQL
echo Y luego: source backup_YYYYMMDD.sql
```

---

## ✅ Verificación Post-Migración

Después de importar, verifica que todo esté correcto:

```sql
-- Conectar a Railway MySQL
railway connect MySQL

-- Verificar tablas
SHOW TABLES;

-- Verificar cantidad de registros
SELECT 'usuarios' as tabla, COUNT(*) as registros FROM usuario
UNION ALL
SELECT 'secciones', COUNT(*) FROM seccion
UNION ALL
SELECT 'matriculas', COUNT(*) FROM matricula
UNION ALL
SELECT 'asistencias', COUNT(*) FROM asistencia;

-- Verificar un usuario de prueba
SELECT * FROM usuario WHERE nombre_usuario = 'admin';

-- Salir
exit;
```

---

## 🔧 Solución de Problemas

### Error: "Access denied"
- Verifica que las credenciales de Railway sean correctas
- Asegúrate de estar usando el puerto correcto

### Error: "Table already exists"
- Agrega `DROP TABLE IF EXISTS` antes de cada `CREATE TABLE`
- O elimina las tablas existentes primero:
```sql
DROP DATABASE IF EXISTS railway;
CREATE DATABASE railway;
USE railway;
```

### Error: "Unknown database"
- Asegúrate de seleccionar la base de datos correcta:
```sql
USE railway;
```

### Los datos no aparecen
- Verifica que el archivo SQL se haya importado completamente
- Revisa los logs de Railway para errores
- Asegúrate de que el charset sea compatible (utf8mb4)

---

## 📊 Comparación de Métodos

| Método | Velocidad | Dificultad | Recomendado Para |
|--------|-----------|------------|------------------|
| Scripts SQL originales | ⚡⚡⚡ Rápido | ⭐ Fácil | Nuevo despliegue |
| Railway CLI | ⚡⚡ Medio | ⭐⭐ Medio | Migración completa |
| MySQL Workbench | ⚡ Lento | ⭐⭐⭐ Fácil | Usuarios con GUI |
| DBeaver | ⚡ Lento | ⭐⭐⭐ Fácil | Usuarios con GUI |

---

## 🎯 Recomendación

Para tu primer despliegue en Railway:

1. **Usa los scripts SQL originales** (`database_schema.sql` y `seed_data.sql`)
2. Esto te dará una base de datos limpia con datos de prueba
3. Después puedes agregar datos reales desde el panel administrativo

Si ya tienes datos importantes en local:

1. **Exporta con mysqldump**
2. **Importa usando Railway CLI**
3. **Verifica** que todo esté correcto

---

## 🔐 Seguridad

**Importante:**
- No subas archivos SQL con datos sensibles a GitHub
- Cambia las contraseñas por defecto después de la migración
- Usa variables de entorno para credenciales
- Haz backups regulares de tu base de datos en Railway

---

## 📞 Ayuda Adicional

Si tienes problemas:
1. Revisa los logs en Railway
2. Verifica la conexión con: `railway connect MySQL`
3. Consulta la [documentación de Railway](https://docs.railway.app/databases/mysql)

---

**¡Listo!** Tu base de datos MariaDB está ahora en Railway MySQL. 🎉
