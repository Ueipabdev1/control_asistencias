# Módulo de Calendario Escolar

## Descripción

El módulo de **Calendario** permite llevar un recuento detallado de los días hábiles, feriados, suspensiones de clases y fines de semana del año escolar. Este módulo es exclusivo para administradores.

## Características

### 1. Tipos de Días
- **Hábil**: Días normales de clases
- **Feriado**: Días festivos nacionales o institucionales
- **Suspensión**: Días con suspensión de actividades escolares
- **Fin de Semana**: Sábados y domingos

### 2. Funcionalidades

#### Gestión de Días
- **Agregar días**: Registrar nuevos días especiales en el calendario
- **Editar días**: Modificar información de días existentes
- **Eliminar días**: Remover días del calendario
- **Filtros**: Buscar por mes, año y tipo de día

#### Información Detallada
Cada día en el calendario puede incluir:
- Fecha
- Tipo de día (hábil, feriado, suspensión, fin de semana)
- Descripción (nombre del feriado, motivo de suspensión, etc.)
- Indicador de día laborable para el personal
- Observaciones adicionales

#### Estadísticas
El módulo muestra estadísticas en tiempo real:
- Total de días hábiles
- Total de feriados
- Total de suspensiones
- Total de fines de semana
- Días laborables para el personal

### 3. Interfaz de Usuario

La interfaz incluye:
- **Dashboard de estadísticas**: Tarjetas visuales con contadores
- **Tabla de calendario**: Lista detallada de todos los días registrados
- **Filtros avanzados**: Por mes, año y tipo de día
- **Modal de edición**: Formulario intuitivo para agregar/editar días
- **Badges de colores**: Identificación visual rápida del tipo de día
  - Verde: Días hábiles
  - Rojo: Feriados
  - Amarillo: Suspensiones
  - Gris: Fines de semana

## Instalación

### 1. Ejecutar Migración de Base de Datos

```bash
mysql -u root -p control_asistencias < migrations/create_calendario_table.sql
```

O desde MySQL/MariaDB:

```sql
source /var/www/dev/control_asistencias/migrations/create_calendario_table.sql;
```

### 2. Reiniciar la Aplicación

```bash
# Si está usando el servidor de desarrollo
python app.py

# Si está usando un servidor de producción, reinicie el servicio correspondiente
```

## Uso

### Acceso al Módulo

1. Iniciar sesión como **administrador**
2. En el menú lateral, hacer clic en **"Calendario Escolar"** (sección Administración)

### Agregar un Día

1. Hacer clic en el botón **"Agregar Día"**
2. Completar el formulario:
   - Seleccionar la fecha
   - Elegir el tipo de día
   - Agregar descripción (opcional)
   - Marcar si es laborable para el personal
   - Agregar observaciones (opcional)
3. Hacer clic en **"Guardar"**

### Editar un Día

1. Localizar el día en la tabla
2. Hacer clic en el botón de **editar** (icono de lápiz)
3. Modificar los campos necesarios
4. Hacer clic en **"Guardar"**

### Eliminar un Día

1. Localizar el día en la tabla
2. Hacer clic en el botón de **eliminar** (icono de papelera)
3. Confirmar la eliminación

### Filtrar Días

Utilizar los selectores en la parte superior de la tabla:
- **Mes**: Filtrar por mes específico
- **Año**: Filtrar por año (rango de 2 años atrás a 5 años adelante)
- **Tipo de Día**: Filtrar por tipo específico

## API Endpoints

El módulo expone los siguientes endpoints (solo para administradores):

### GET `/admin/calendario`
Página principal del calendario

### GET `/admin/calendario/obtener`
Obtener días del calendario con filtros opcionales

**Parámetros de consulta:**
- `mes` (opcional): Número del mes (1-12)
- `anio` (opcional): Año
- `tipo_dia` (opcional): Tipo de día (habil, feriado, suspension, fin_semana)

**Respuesta:**
```json
{
  "success": true,
  "dias": [
    {
      "id_calendario": 1,
      "fecha": "2026-01-01",
      "tipo_dia": "feriado",
      "descripcion": "Año Nuevo",
      "es_laborable": false,
      "observaciones": null
    }
  ]
}
```

### POST `/admin/calendario/agregar`
Agregar un nuevo día al calendario

**Body:**
```json
{
  "fecha": "2026-01-01",
  "tipo_dia": "feriado",
  "descripcion": "Año Nuevo",
  "es_laborable": false,
  "observaciones": ""
}
```

### PUT `/admin/calendario/editar/<id_calendario>`
Editar un día existente

**Body:**
```json
{
  "tipo_dia": "feriado",
  "descripcion": "Año Nuevo",
  "es_laborable": false,
  "observaciones": "Feriado nacional"
}
```

### DELETE `/admin/calendario/eliminar/<id_calendario>`
Eliminar un día del calendario

### GET `/admin/calendario/estadisticas`
Obtener estadísticas del calendario

**Parámetros de consulta:**
- `mes` (opcional): Número del mes
- `anio` (requerido): Año

**Respuesta:**
```json
{
  "success": true,
  "estadisticas": {
    "total_dias": 10,
    "dias_habiles": 5,
    "feriados": 3,
    "suspensiones": 1,
    "fines_semana": 1,
    "dias_laborables": 7
  }
}
```

## Modelo de Datos

### Tabla: `calendario`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_calendario | INT | ID único (PK) |
| fecha | DATE | Fecha del día |
| tipo_dia | ENUM | Tipo: habil, feriado, suspension, fin_semana |
| descripcion | VARCHAR(255) | Descripción del día |
| es_laborable | BOOLEAN | Si es laborable para el personal |
| observaciones | TEXT | Observaciones adicionales |
| fecha_creacion | TIMESTAMP | Fecha de creación del registro |
| fecha_actualizacion | TIMESTAMP | Última actualización |

## Datos Iniciales

La migración incluye feriados nacionales de Venezuela para 2026:
- Año Nuevo (1 de enero)
- Declaración de la Independencia (19 de abril)
- Día del Trabajador (1 de mayo)
- Batalla de Carabobo (24 de junio)
- Día de la Independencia (5 de julio)
- Natalicio del Libertador (24 de julio)
- Día de la Resistencia Indígena (12 de octubre)
- Nochebuena (24 de diciembre)
- Navidad (25 de diciembre)
- Fin de Año (31 de diciembre)

## Casos de Uso

### 1. Planificación del Año Escolar
Registrar todos los feriados y suspensiones programadas al inicio del año escolar para una mejor planificación.

### 2. Cálculo de Días Hábiles
Utilizar las estadísticas para calcular el total de días hábiles disponibles para clases.

### 3. Gestión de Personal
Diferenciar entre días no laborables para estudiantes pero laborables para el personal administrativo.

### 4. Reportes
Generar reportes de asistencia considerando solo los días hábiles registrados en el calendario.

## Notas Importantes

- Solo los **administradores** tienen acceso a este módulo
- Cada fecha solo puede tener un registro en el calendario
- Los fines de semana pueden registrarse manualmente si se requiere documentación especial
- El campo `es_laborable` permite diferenciar días no escolares pero laborables para el personal

## Futuras Mejoras

- Importación masiva de días desde archivo CSV/Excel
- Generación automática de fines de semana
- Integración con el módulo de asistencias para validar fechas
- Exportación de calendario a formatos PDF/Excel
- Vista de calendario mensual visual
- Notificaciones de próximos feriados
