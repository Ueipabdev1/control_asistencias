# 🔄 Guía de Migración a Sistema V2 - Asistencia Individual

## 📋 Resumen de Cambios

El sistema ha sido refactorizado para pasar de un **control de asistencia por conteo de género** a un **sistema de asistencia individual por estudiante**.

### Cambios Principales:

1. **Nueva estructura de base de datos normalizada:**
   - `Etapa` → `Grado` → `Sección` → `Estudiante`
   - Separación clara entre grado (1er grado, 2do grado) y sección (A, B, C, Única)

2. **Nuevas tablas:**
   - `grado`: Grados dentro de cada etapa
   - `seccion`: Secciones dentro de cada grado (refactorizada)
   - `estudiante`: Información individual de cada estudiante
   - `asistencia_estudiante`: Registro de asistencia individual

3. **Tablas legacy (mantenidas para compatibilidad):**
   - `matricula_legacy`: Antigua tabla de matrícula
   - `asistencia_legacy`: Antigua tabla de asistencia por género

---

## 🚀 Pasos de Migración

### 1. Backup de Base de Datos Actual

**IMPORTANTE:** Antes de cualquier cambio, haz un backup completo de tu base de datos.

```bash
# Backup completo
mysqldump -u root -p control_asistencias > backup_control_asistencias_$(date +%Y%m%d).sql

# O desde MariaDB
mariadb-dump -u root -p control_asistencias > backup_control_asistencias_$(date +%Y%m%d).sql
```

El backup del esquema también está en: `backups/database_schema_v1_backup.sql`

---

### 2. Instalar Nuevas Dependencias

```bash
pip install -r requirements.txt
```

Nuevas dependencias agregadas:
- `pandas==2.0.3` - Para procesar archivos Excel
- `openpyxl==3.1.2` - Para leer archivos .xlsx
- `xlrd==2.0.1` - Para leer archivos .xls

---

### 3. Ejecutar Nuevo Esquema de Base de Datos

**Opción A: Instalación Limpia (Recomendada para desarrollo)**

```bash
# Conectar a MariaDB/MySQL
mysql -u root -p

# Dentro de MySQL/MariaDB
DROP DATABASE IF EXISTS control_asistencias;
SOURCE database_schema_v2.sql;
```

**Opción B: Migración con Datos Existentes**

Si tienes datos importantes que quieres mantener, usa el script de migración:

```bash
mysql -u root -p control_asistencias < migrations/migrate_to_v2.sql
```

---

### 4. Verificar Estructura de Base de Datos

```sql
USE control_asistencias;

-- Verificar nuevas tablas
SHOW TABLES;

-- Verificar estructura de tabla grado
DESCRIBE grado;

-- Verificar estructura de tabla seccion
DESCRIBE seccion;

-- Verificar estructura de tabla estudiante
DESCRIBE estudiante;

-- Verificar estructura de tabla asistencia_estudiante
DESCRIBE asistencia_estudiante;

-- Verificar datos iniciales
SELECT * FROM etapa;
SELECT * FROM grado;
SELECT * FROM seccion;
```

---

### 5. Iniciar Aplicación

```bash
python app.py
```

Deberías ver:
```
✅ Conexión a MariaDB establecida correctamente
✅ Tablas verificadas/creadas
 * Running on http://127.0.0.1:5000
```

---

## 📊 Estructura de la Nueva Base de Datos

### Jerarquía:

```
Etapa (Maternal, Primaria, Secundaria)
  └── Grado (1er grado, 2do grado, 1er año, etc.)
      └── Sección (A, B, C, Única)
          └── Estudiante (Individual)
              └── AsistenciaEstudiante (Por día)
```

### Ejemplo de Datos:

**Etapas:**
- Maternal
- Primaria
- Secundaria

**Grados (Primaria):**
- 1er grado
- 2do grado
- 3er grado
- 4to grado
- 5to grado
- 6to grado

**Secciones (3er año Secundaria):**
- 3er año - Sección A
- 3er año - Sección B

**Estudiantes (3er año A):**
- Juan Pérez (V12345678) - Masculino
- María González (V87654321) - Femenino

---

## 📁 Carga de Estudiantes desde Excel

### Formato del Archivo Excel

El archivo Excel debe tener las siguientes columnas (exactamente con estos nombres):

| Grado | Sección | Nombre | Apellido | Cédula de identidad | Género |
|-------|---------|--------|----------|---------------------|--------|
| 1er grado | Única | Juan | Pérez | V12345678 | M |
| 3er año | A | María | González | V87654321 | F |
| 3er año | B | Pedro | Ramírez | V11223344 | M |

**Notas importantes:**
- **Grado:** Debe coincidir con los grados en la base de datos (ej: "1er grado", "3er año")
- **Sección:** Debe coincidir con las secciones existentes (ej: "A", "B", "Única")
- **Género:** Solo acepta "M" (Masculino) o "F" (Femenino)
- **Cédula:** Debe ser única por estudiante

### Cargar Estudiantes vía API

**Endpoint:** `POST /api/estudiantes/cargar-excel`

```bash
curl -X POST http://localhost:5000/api/estudiantes/cargar-excel \
  -H "Content-Type: multipart/form-data" \
  -F "archivo=@lista_estudiantes.xlsx" \
  -F "sobrescribir=false"
```

**Parámetros:**
- `archivo`: Archivo Excel (.xlsx o .xls)
- `sobrescribir`: `true` para actualizar estudiantes existentes, `false` para omitirlos

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Archivo procesado correctamente",
  "total_filas": 150,
  "procesados": 145,
  "actualizados": 0,
  "duplicados": 5,
  "errores": 0,
  "detalle": {
    "procesados": [...],
    "duplicados": [...],
    "errores": []
  }
}
```

---

## 🔌 Nuevos Endpoints API

### Gestión de Estudiantes

#### 1. Cargar estudiantes desde Excel
```
POST /api/estudiantes/cargar-excel
```

#### 2. Obtener estudiantes de una sección
```
GET /api/estudiantes/seccion/{id_seccion}
```

#### 3. Obtener información de un estudiante
```
GET /api/estudiantes/{id_estudiante}
```

#### 4. Actualizar estudiante
```
PUT /api/estudiantes/{id_estudiante}
```

#### 5. Eliminar (desactivar) estudiante
```
DELETE /api/estudiantes/{id_estudiante}
```

#### 6. Estadísticas de estudiantes
```
GET /api/estudiantes/estadisticas
```

### Asistencia Individual

#### 1. Registrar asistencia
```
POST /api/asistencia-individual/registrar
Body: {
  "fecha": "2026-02-03",
  "asistencias": [
    {"id_estudiante": 1, "presente": true, "observaciones": ""},
    {"id_estudiante": 2, "presente": false, "observaciones": "Justificado"}
  ]
}
```

#### 2. Obtener asistencia de una sección
```
GET /api/asistencia-individual/{fecha}/{id_seccion}
```

#### 3. Estadísticas de asistencia
```
GET /api/asistencia-individual/estadisticas/{id_seccion}?fecha_inicio=2026-02-01&fecha_fin=2026-02-28
```

---

## 🔧 Configuración en Producción (Railway)

### 1. Actualizar Base de Datos en Railway

1. Conectar a la base de datos de Railway
2. Ejecutar `database_schema_v2.sql`
3. Verificar que todas las tablas se crearon correctamente

### 2. Variables de Entorno

Asegúrate de que `DATABASE_URL` esté configurada en Railway:

```
DATABASE_URL=mysql+pymysql://usuario:contraseña@host:puerto/control_asistencias?charset=utf8mb4
```

### 3. Desplegar Cambios

```bash
git add .
git commit -m "Migración a sistema V2 - Asistencia individual"
git push
```

---

## 📝 Notas Importantes

### Compatibilidad con Datos Antiguos

- Las tablas antiguas se renombraron a `*_legacy` para mantener datos históricos
- El modelo `Asistencia` ahora apunta a `asistencia_legacy`
- El modelo `Matricula` se mantiene sin cambios temporalmente

### Próximos Pasos

1. **Crear interfaz web** para carga de Excel
2. **Refactorizar interfaz de asistencia** con checkboxes individuales
3. **Actualizar reportes** para trabajar con asistencia individual
4. **Migrar datos legacy** si es necesario

### Solución de Problemas

**Error: "Tabla no encontrada"**
- Verifica que ejecutaste `database_schema_v2.sql`
- Revisa que la conexión a la base de datos sea correcta

**Error al cargar Excel: "No se encontró sección"**
- Verifica que los nombres de grado y sección en el Excel coincidan con la BD
- Revisa que las secciones estén creadas en la base de datos

**Error: "Cédula duplicada"**
- El estudiante ya existe en la base de datos
- Usa `sobrescribir=true` para actualizar o elimina el duplicado

---

## 📞 Soporte

Para cualquier problema durante la migración, revisa:
1. Logs de la aplicación
2. Logs de la base de datos
3. Archivo de backup creado

---

**Fecha de Migración:** 2026-02-03  
**Versión:** 2.0  
**Autor:** Sistema de Control de Asistencias
