# 📚 Sistema de Control de Asistencias V2 - Asistencia Individual

Sistema de gestión de asistencias educativas con registro individual por estudiante.

## 🆕 Novedades en V2

### Cambios Principales

1. **Estructura de Base de Datos Normalizada**
   - Separación clara: Etapa → Grado → Sección → Estudiante
   - Soporte para múltiples secciones por grado (ej: 3er año A, 3er año B)

2. **Asistencia Individual**
   - Registro de asistencia por estudiante (no por conteo de género)
   - Historial completo de asistencia por estudiante
   - Observaciones opcionales por registro

3. **Carga de Estudiantes desde Excel**
   - Importación masiva de estudiantes desde archivos Excel
   - Validación automática de datos
   - Detección de duplicados

4. **Nuevas APIs REST**
   - Endpoints para gestión de estudiantes
   - Endpoints para asistencia individual
   - Estadísticas detalladas por estudiante y sección

## 🚀 Inicio Rápido

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Base de Datos

```bash
# Conectar a MariaDB/MySQL
mysql -u root -p

# Ejecutar esquema V2
SOURCE database_schema_v2.sql
```

### 3. Iniciar Aplicación

```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

## 📁 Estructura del Proyecto

```
control_asistencias/
├── app.py                          # Aplicación principal Flask
├── models.py                       # Modelos de base de datos (SQLAlchemy)
├── extensions.py                   # Extensiones compartidas (bcrypt, login_manager)
├── routes.py                       # Rutas principales (legacy)
├── routes_estudiantes.py           # Rutas para estudiantes y asistencia individual
├── database_schema_v2.sql          # Esquema de base de datos V2
├── requirements.txt                # Dependencias Python
├── MIGRACION_V2.md                # Guía de migración
│
├── backups/
│   └── database_schema_v1_backup.sql  # Backup del esquema anterior
│
├── utils/
│   └── excel_processor.py          # Utilidad para procesar archivos Excel
│
├── data_estudiantes_akademia/      # Directorio para archivos Excel
│   └── lista_de_estudiantes.xls
│
├── templates/                      # Plantillas HTML
└── static/                         # Archivos estáticos (CSS, JS, imágenes)
```

## 📊 Modelo de Datos

### Jerarquía

```
Etapa (Maternal, Primaria, Secundaria)
  └── Grado (1er grado, 2do grado, 1er año, etc.)
      └── Sección (A, B, C, Única)
          └── Estudiante
              └── AsistenciaEstudiante (por fecha)
```

### Tablas Principales

- **etapa**: Etapas educativas
- **grado**: Grados dentro de cada etapa
- **seccion**: Secciones dentro de cada grado
- **estudiante**: Información individual de estudiantes
- **asistencia_estudiante**: Registro de asistencia individual
- **usuario**: Administradores y profesores
- **profesor_seccion**: Asignación de profesores a secciones

## 📤 Carga de Estudiantes desde Excel

### Formato del Archivo

El archivo Excel debe contener las siguientes columnas:

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| Grado | Nombre del grado | "1er grado", "3er año" |
| Sección | Letra de la sección | "A", "B", "Única" |
| Nombre | Nombre del estudiante | "Juan" |
| Apellido | Apellido del estudiante | "Pérez" |
| Cédula de identidad | Cédula única | "V12345678" |
| Género | M o F | "M", "F" |

### Ejemplo de Archivo Excel

| Grado | Sección | Nombre | Apellido | Cédula de identidad | Género |
|-------|---------|--------|----------|---------------------|--------|
| 1er grado | Única | Juan | Pérez | V12345678 | M |
| 1er grado | Única | María | González | V87654321 | F |
| 3er año | A | Pedro | Ramírez | V11223344 | M |
| 3er año | B | Ana | Martínez | V55667788 | F |

### Cargar Archivo

**Via API:**

```bash
curl -X POST http://localhost:5000/api/estudiantes/cargar-excel \
  -F "archivo=@lista_estudiantes.xlsx" \
  -F "sobrescribir=false"
```

**Via Interfaz Web:**
- Ir a "Gestión de Matrícula"
- Hacer clic en "Cargar Estudiantes desde Excel"
- Seleccionar archivo
- Hacer clic en "Subir"

## 🔌 API Endpoints

### Estudiantes

#### Cargar desde Excel
```
POST /api/estudiantes/cargar-excel
Content-Type: multipart/form-data
Body: archivo (file), sobrescribir (boolean)
```

#### Obtener estudiantes de una sección
```
GET /api/estudiantes/seccion/{id_seccion}
Response: { seccion: {...}, estudiantes: [...] }
```

#### Obtener estudiante específico
```
GET /api/estudiantes/{id_estudiante}
Response: { id_estudiante, cedula, nombre, apellido, ... }
```

#### Actualizar estudiante
```
PUT /api/estudiantes/{id_estudiante}
Body: { nombre, apellido, cedula, genero, id_seccion, activo }
```

#### Eliminar estudiante
```
DELETE /api/estudiantes/{id_estudiante}
Response: { success: true, message: "..." }
```

#### Estadísticas
```
GET /api/estudiantes/estadisticas
Response: { total_estudiantes, por_genero, por_seccion }
```

### Asistencia Individual

#### Registrar asistencia
```
POST /api/asistencia-individual/registrar
Body: {
  "fecha": "2026-02-03",
  "asistencias": [
    { "id_estudiante": 1, "presente": true, "observaciones": "" },
    { "id_estudiante": 2, "presente": false, "observaciones": "Justificado" }
  ]
}
```

#### Obtener asistencia de sección
```
GET /api/asistencia-individual/{fecha}/{id_seccion}
Response: {
  fecha, seccion, total_estudiantes, total_presentes,
  porcentaje_asistencia, estudiantes: [...]
}
```

#### Estadísticas de asistencia
```
GET /api/asistencia-individual/estadisticas/{id_seccion}
Query: fecha_inicio, fecha_fin
Response: { total_registros, total_presentes, porcentaje_asistencia }
```

## 🔐 Autenticación

El sistema usa Flask-Login para autenticación.

### Roles

- **Administrador**: Acceso completo al sistema
- **Profesor**: Acceso a sus secciones asignadas

### Endpoints Protegidos

- Todos los endpoints requieren autenticación (`@login_required`)
- Endpoints de administración requieren rol de administrador (`@admin_required`)

## 🛠️ Desarrollo

### Ejecutar en Modo Debug

```bash
python app.py
```

### Crear Migraciones

```bash
# Generar nueva migración
flask db migrate -m "Descripción del cambio"

# Aplicar migración
flask db upgrade
```

### Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=.
```

## 🚀 Despliegue en Producción

### Railway

1. Conectar repositorio a Railway
2. Configurar variable de entorno `DATABASE_URL`
3. Ejecutar `database_schema_v2.sql` en la base de datos
4. Desplegar

### Variables de Entorno

```env
SECRET_KEY=tu_clave_secreta_segura
DATABASE_URL=mysql+pymysql://usuario:contraseña@host:puerto/control_asistencias?charset=utf8mb4
```

## 📝 Migración desde V1

Si tienes datos en el sistema anterior, consulta `MIGRACION_V2.md` para instrucciones detalladas de migración.

## 🐛 Solución de Problemas

### Error: "Tabla no encontrada"

**Solución:** Ejecuta `database_schema_v2.sql` en tu base de datos.

### Error: "No se encontró sección" al cargar Excel

**Solución:** Verifica que los nombres de grado y sección en el Excel coincidan exactamente con los de la base de datos.

### Error: "Cédula duplicada"

**Solución:** El estudiante ya existe. Usa `sobrescribir=true` para actualizar o elimina el duplicado.

### Error de conexión a base de datos

**Solución:** 
1. Verifica que MariaDB/MySQL esté ejecutándose
2. Revisa las credenciales en la variable `DATABASE_URL`
3. Verifica que la base de datos `control_asistencias` exista

## 📚 Documentación Adicional

- `MIGRACION_V2.md` - Guía completa de migración
- `database_schema_v2.sql` - Esquema de base de datos con comentarios
- `backups/database_schema_v1_backup.sql` - Backup del esquema anterior

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📄 Licencia

Este proyecto es de uso interno para la institución educativa.

## 📞 Contacto

Para soporte o consultas, contacta al equipo de desarrollo.

---

**Versión:** 2.0  
**Fecha:** Febrero 2026  
**Estado:** Producción
