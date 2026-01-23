# Guía de Despliegue en Railway

Esta guía te ayudará a desplegar tu aplicación Flask de Control de Asistencias en Railway.

## 📋 Requisitos Previos

1. Cuenta en [Railway.app](https://railway.app)
2. Cuenta en GitHub (para conectar tu repositorio)
3. Git instalado en tu computadora

## 🚀 Pasos para Desplegar

### 1. Preparar el Repositorio Git

Si aún no has inicializado Git en tu proyecto:

```bash
cd c:\Users\danie\Desktop\ueipab\control_asistencias
git init
git add .
git commit -m "Initial commit - Control de Asistencias"
```

### 2. Subir a GitHub

1. Crea un nuevo repositorio en GitHub (https://github.com/new)
2. **NO** inicialices con README, .gitignore o licencia
3. Copia la URL del repositorio
4. Ejecuta los siguientes comandos:

```bash
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git branch -M main
git push -u origin main
```

### 3. Crear Proyecto en Railway

1. Ve a [Railway.app](https://railway.app) e inicia sesión
2. Haz clic en **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**
4. Autoriza Railway para acceder a tus repositorios
5. Selecciona el repositorio `control_asistencias`

### 4. Agregar Base de Datos MySQL

1. En tu proyecto de Railway, haz clic en **"+ New"**
2. Selecciona **"Database"** → **"Add MySQL"**
3. Railway creará automáticamente una base de datos MySQL

### 5. Configurar Variables de Entorno

1. Haz clic en tu servicio web (el que tiene tu código)
2. Ve a la pestaña **"Variables"**
3. Agrega las siguientes variables:

```
SECRET_KEY=genera_una_clave_secreta_aleatoria_aqui
DATABASE_URL=mysql+pymysql://usuario:password@host:puerto/database?charset=utf8mb4
```

**Para obtener DATABASE_URL:**
1. Haz clic en el servicio de MySQL que creaste
2. Ve a la pestaña **"Variables"**
3. Copia los valores de:
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `MYSQL_HOST`
   - `MYSQL_PORT`
   - `MYSQL_DATABASE`

4. Construye la URL así:
```
mysql+pymysql://MYSQL_USER:MYSQL_PASSWORD@MYSQL_HOST:MYSQL_PORT/MYSQL_DATABASE?charset=utf8mb4
```

**Ejemplo:**
```
mysql+pymysql://root:abc123xyz@containers-us-west-123.railway.app:6789/railway?charset=utf8mb4
```

### 6. Crear las Tablas de la Base de Datos

Railway no ejecuta automáticamente scripts SQL. Tienes dos opciones:

#### Opción A: Usar Railway CLI (Recomendado)

1. Instala Railway CLI:
```bash
npm i -g @railway/cli
```

2. Inicia sesión:
```bash
railway login
```

3. Vincula tu proyecto:
```bash
railway link
```

4. Conecta a la base de datos:
```bash
railway connect MySQL
```

5. Una vez conectado, ejecuta los scripts:
```sql
source database_schema.sql;
source seed_data.sql;
```

#### Opción B: Usar un Cliente MySQL

1. Descarga [MySQL Workbench](https://dev.mysql.com/downloads/workbench/) o [DBeaver](https://dbeaver.io/)
2. Conecta usando las credenciales de Railway (MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD)
3. Ejecuta los archivos `database_schema.sql` y `seed_data.sql`

### 7. Desplegar la Aplicación

1. Railway detectará automáticamente que es una aplicación Flask
2. Usará el `Procfile` para iniciar la aplicación con Gunicorn
3. El despliegue comenzará automáticamente
4. Espera a que termine (verás los logs en tiempo real)

### 8. Obtener la URL de tu Aplicación

1. Una vez desplegado, ve a la pestaña **"Settings"**
2. En la sección **"Domains"**, haz clic en **"Generate Domain"**
3. Railway te dará una URL como: `https://tu-proyecto.up.railway.app`

## 🔧 Archivos de Configuración Creados

Los siguientes archivos fueron creados para el despliegue:

- **`Procfile`**: Le dice a Railway cómo iniciar la aplicación
- **`runtime.txt`**: Especifica la versión de Python
- **`requirements.txt`**: Actualizado con `gunicorn` y `cryptography`
- **`.env.example`**: Plantilla de variables de entorno

## 🔐 Seguridad

### Generar SECRET_KEY Segura

Ejecuta este comando en Python para generar una clave secreta:

```python
import secrets
print(secrets.token_hex(32))
```

Copia el resultado y úsalo como valor de `SECRET_KEY` en Railway.

## 📝 Credenciales de Acceso por Defecto

Después de ejecutar `seed_data.sql`, puedes iniciar sesión con:

**Administrador:**
- Usuario: `admin`
- Contraseña: `password123`

**Profesor:**
- Usuario: `profesor1`
- Contraseña: `password123`

**⚠️ IMPORTANTE:** Cambia estas contraseñas inmediatamente en producción.

## 🐛 Solución de Problemas

### Error: "Application failed to respond"
- Verifica que `DATABASE_URL` esté configurada correctamente
- Revisa los logs en Railway para ver errores específicos

### Error: "Table doesn't exist"
- Asegúrate de haber ejecutado `database_schema.sql` en la base de datos de Railway

### Error de conexión a la base de datos
- Verifica que la URL de la base de datos tenga el formato correcto
- Asegúrate de que el servicio MySQL esté ejecutándose en Railway

### La aplicación se despliega pero no funciona
- Revisa los logs en la pestaña "Deployments" de Railway
- Verifica que todas las variables de entorno estén configuradas

## 🔄 Actualizar la Aplicación

Para actualizar tu aplicación después de hacer cambios:

```bash
git add .
git commit -m "Descripción de los cambios"
git push origin main
```

Railway detectará automáticamente el push y redesplegar la aplicación.

## 📊 Monitoreo

Railway proporciona:
- **Logs en tiempo real**: Pestaña "Deployments" → Ver logs
- **Métricas**: CPU, memoria, red
- **Reinicio automático**: Si la aplicación falla

## 💰 Costos

Railway ofrece:
- **Plan gratuito**: $5 USD de crédito mensual
- **Plan Pro**: $20 USD/mes con más recursos

Tu aplicación debería funcionar bien en el plan gratuito para desarrollo y pruebas.

## 🆘 Soporte

Si tienes problemas:
1. Revisa los logs en Railway
2. Consulta la [documentación de Railway](https://docs.railway.app)
3. Únete al [Discord de Railway](https://discord.gg/railway)

---

**¡Listo!** Tu aplicación de Control de Asistencias debería estar funcionando en Railway. 🎉
