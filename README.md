# Sistema de Control de Asistencias

Una aplicación web moderna desarrollada con Flask para gestionar la asistencia de estudiantes en instituciones educativas.

## Características

- Interfaz moderna y responsiva con Bootstrap 5
- Sistema de autenticación con roles (Administrador/Profesor)
- Gestión de asistencia por secciones y etapas educativas (Maternal, Primaria, Secundaria)
- Registro de asistencia diferenciado por género
- Dashboard administrativo con estadísticas
- Gestión de matrícula por sección
- Asignación de profesores a secciones
- Base de datos MariaDB/MySQL

## Requisitos

- Python 3.10+
- MariaDB/MySQL
- Nginx (para producción)

## Instalación Local

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Ueipabdev1/control_asistencias.git
   cd control_asistencias
   ```

2. **Crear un entorno virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar la base de datos:**
   ```bash
   # Crear la base de datos en MariaDB
   mysql -u root -p < database_schema.sql

   # (Opcional) Cargar datos de prueba
   mysql -u root -p control_asistencias < seed_data.sql
   ```

5. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con las credenciales de la base de datos
   ```

6. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```

7. **Abrir en el navegador:**
   ```
   http://localhost:5000
   ```

## Despliegue en Producción (UEIPAB)

La aplicación está desplegada en el servidor de desarrollo de UEIPAB.

### URL de Producción
```
https://dev.ueipab.edu.ve/control_asistencias/
```

### Configuración del Servidor

| Componente | Configuración |
|------------|---------------|
| Puerto | 5006 |
| Servicio | `control_asistencias.service` |
| Base de datos | `control_asistencias` (MariaDB) |
| Usuario DB | `control_asist` |
| Servidor web | Nginx reverse proxy |

### Comandos Útiles

```bash
# Estado del servicio
sudo systemctl status control_asistencias

# Reiniciar servicio
sudo systemctl restart control_asistencias

# Ver logs
sudo journalctl -u control_asistencias -f

# Probar configuración de Nginx
sudo nginx -t && sudo systemctl reload nginx
```

## Estructura del Proyecto

```
control_asistencias/
├── app.py                  # Aplicación principal Flask
├── models.py               # Modelos SQLAlchemy
├── routes.py               # Rutas y endpoints API
├── requirements.txt        # Dependencias Python
├── database_schema.sql     # Esquema de la base de datos
├── seed_data.sql           # Datos de prueba
├── .env                    # Variables de entorno (no versionado)
├── .env.example            # Ejemplo de configuración
├── git_credentials.json    # Credenciales Git (no versionado)
├── templates/
│   ├── base.html           # Plantilla base
│   ├── login.html          # Página de inicio de sesión
│   ├── registro.html       # Registro de usuarios
│   ├── index.html          # Dashboard principal (profesores)
│   ├── admin_dashboard.html    # Dashboard administrativo
│   ├── gestion_matricula.html  # Gestión de matrículas
│   └── gestion_profesores.html # Gestión de profesores
└── README.md
```

## Archivos Sensibles (No Versionados)

Los siguientes archivos contienen información sensible y están excluidos del repositorio:

| Archivo | Descripción |
|---------|-------------|
| `.env` | Variables de entorno (credenciales BD, SECRET_KEY) |
| `git_credentials.json` | Token de acceso GitHub para push/pull |

Estos archivos existen solo en el servidor de producción.

## Tecnologías Utilizadas

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt
- **Frontend:** HTML5, CSS3, JavaScript (jQuery), Bootstrap 5
- **Base de datos:** MariaDB/MySQL
- **Servidor:** Gunicorn + Nginx
- **Iconos:** Font Awesome

## API Endpoints

### Autenticación
- `GET/POST /auth/login` - Inicio de sesión
- `GET /auth/logout` - Cerrar sesión
- `GET/POST /auth/registro` - Registro de usuarios

### Principal
- `GET /` - Dashboard principal
- `GET /secciones` - Lista de secciones con matrícula
- `POST /guardar_asistencia` - Guardar registro de asistencia

### Administración
- `GET /admin/dashboard` - Dashboard administrativo
- `GET /admin/estadisticas` - Estadísticas de asistencia
- `GET /admin/gestion-matricula` - Gestión de matrícula
- `GET /admin/gestion-profesores` - Gestión de profesores

### API
- `POST /api/usuario` - Crear usuario
- `GET /api/profesores/asignaciones` - Lista de profesores con asignaciones
- `POST /api/profesor/asignar-secciones` - Asignar secciones a profesor
- `POST /api/matricula` - Guardar matrícula
- `GET /api/matriculas` - Lista de matrículas

## Usuarios de Prueba

Si se cargaron los datos de prueba (`seed_data.sql`):

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | admin@ueipab.edu | password123 |
| Administrador | maria.gonzalez@ueipab.edu | password123 |
| Profesor | ana.martinez@ueipab.edu | password123 |

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
