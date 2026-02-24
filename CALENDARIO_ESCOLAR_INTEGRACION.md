# Integración del Calendario Escolar

## Descripción

El módulo de Calendario Escolar permite marcar días no laborables (feriados, vacaciones, suspensiones) que **no deben contarse** en el cálculo de asistencia mensual.

## Funcionalidades

### 1. Gestión de Días No Laborables

- **Agregar días**: Marcar fechas específicas como no laborables
- **Tipos de días**:
  - `feriado`: Días festivos nacionales o regionales
  - `vacaciones`: Períodos vacacionales
  - `suspension`: Suspensiones de clases por eventos especiales
  - `otro`: Otros motivos

### 2. Calendario Visual

- Vista mensual interactiva
- Navegación entre meses
- Indicadores visuales por tipo de día
- Click en días para agregar/ver detalles

### 3. API Endpoints

#### Obtener días no laborables
```
GET /calendario/api/dias-no-laborables
GET /calendario/api/dias-no-laborables?año=2026&mes=2
```

#### Verificar si un día es laborable
```
GET /calendario/api/verificar-dia/<fecha>
Ejemplo: GET /calendario/api/verificar-dia/2026-01-01
```

#### Crear día no laborable
```
POST /calendario/api/dia-no-laborable
Body: {
    "fecha": "2026-01-01",
    "tipo": "feriado",
    "descripcion": "Año Nuevo"
}
```

#### Actualizar día no laborable
```
PUT /calendario/api/dia-no-laborable/<id>
Body: {
    "tipo": "vacaciones",
    "descripcion": "Vacaciones de verano"
}
```

#### Eliminar día no laborable
```
DELETE /calendario/api/dia-no-laborable/<id>
```

## Integración en Cálculos de Asistencia

### Función Helper para Obtener Días Laborables

```python
from models import CalendarioEscolar
from datetime import datetime, timedelta

def contar_dias_laborables(fecha_inicio, fecha_fin):
    """
    Cuenta los días laborables entre dos fechas, excluyendo días no laborables
    
    Args:
        fecha_inicio: Fecha de inicio (date o datetime)
        fecha_fin: Fecha de fin (date o datetime)
    
    Returns:
        int: Número de días laborables
    """
    # Convertir a date si es datetime
    if isinstance(fecha_inicio, datetime):
        fecha_inicio = fecha_inicio.date()
    if isinstance(fecha_fin, datetime):
        fecha_fin = fecha_fin.date()
    
    # Obtener días no laborables en el rango
    dias_no_laborables = CalendarioEscolar.query.filter(
        CalendarioEscolar.fecha >= fecha_inicio,
        CalendarioEscolar.fecha <= fecha_fin,
        CalendarioEscolar.activo == True
    ).all()
    
    # Crear set de fechas no laborables
    fechas_no_laborables = {d.fecha for d in dias_no_laborables}
    
    # Contar días laborables
    dias_laborables = 0
    fecha_actual = fecha_inicio
    
    while fecha_actual <= fecha_fin:
        # Excluir fines de semana (sábado=5, domingo=6)
        if fecha_actual.weekday() < 5 and fecha_actual not in fechas_no_laborables:
            dias_laborables += 1
        fecha_actual += timedelta(days=1)
    
    return dias_laborables

def obtener_dias_no_laborables_mes(año, mes):
    """
    Obtiene todos los días no laborables de un mes específico
    
    Args:
        año: Año (int)
        mes: Mes (int, 1-12)
    
    Returns:
        list: Lista de fechas no laborables
    """
    from sqlalchemy import extract
    
    dias = CalendarioEscolar.query.filter(
        extract('year', CalendarioEscolar.fecha) == año,
        extract('month', CalendarioEscolar.fecha) == mes,
        CalendarioEscolar.activo == True
    ).all()
    
    return [d.fecha for d in dias]
```

### Ejemplo de Uso en Cálculo de Asistencia Mensual

```python
from datetime import date
from models import AsistenciaEstudiante, Estudiante, CalendarioEscolar

def calcular_porcentaje_asistencia_mensual(id_estudiante, año, mes):
    """
    Calcula el porcentaje de asistencia de un estudiante en un mes,
    excluyendo días no laborables
    """
    # Obtener primer y último día del mes
    primer_dia = date(año, mes, 1)
    if mes == 12:
        ultimo_dia = date(año + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(año, mes + 1, 1) - timedelta(days=1)
    
    # Contar días laborables del mes
    dias_laborables = contar_dias_laborables(primer_dia, ultimo_dia)
    
    if dias_laborables == 0:
        return 0
    
    # Contar días que el estudiante asistió
    asistencias = AsistenciaEstudiante.query.filter(
        AsistenciaEstudiante.id_estudiante == id_estudiante,
        AsistenciaEstudiante.fecha >= primer_dia,
        AsistenciaEstudiante.fecha <= ultimo_dia,
        AsistenciaEstudiante.presente == True
    ).count()
    
    # Calcular porcentaje
    porcentaje = (asistencias / dias_laborables) * 100
    
    return round(porcentaje, 2)
```

### Integración en Estadísticas

Modificar `routes_estadisticas.py` para excluir días no laborables:

```python
# En la función obtener_estadisticas()

# Calcular días analizados (excluyendo días no laborables)
dias_analizados = contar_dias_laborables(fecha_inicio, fecha_fin)

# Usar dias_analizados en lugar del cálculo simple de días
```

## Uso desde la Interfaz

1. **Acceder al módulo**: Menú lateral → Administración → Calendario Escolar
2. **Agregar día no laborable**:
   - Click en el botón "Agregar Día No Laborable"
   - O click en un día del calendario
   - Completar formulario (fecha, tipo, descripción)
   - Guardar
3. **Visualizar días marcados**: Los días no laborables aparecen coloreados según su tipo
4. **Eliminar día**: Usar el botón de eliminar en la tabla de días registrados

## Consideraciones

- Los días no laborables se aplican a **todas las secciones** del sistema
- Los fines de semana (sábado y domingo) se excluyen automáticamente en los cálculos
- Los días marcados como inactivos no se cuentan en los cálculos
- El sistema permite marcar días pasados y futuros
- Se recomienda configurar el calendario al inicio del año escolar

## Próximos Pasos de Integración

Para integrar completamente el calendario escolar en los cálculos de asistencia:

1. Modificar `routes_estadisticas.py` para usar `contar_dias_laborables()`
2. Actualizar el dashboard administrativo para mostrar días laborables vs días totales
3. Agregar indicador en el registro de asistencia cuando un día es no laborable
4. Crear reportes que muestren el impacto de días no laborables en la asistencia

## Mantenimiento

- Actualizar el calendario al inicio de cada año escolar
- Revisar y ajustar días de vacaciones según el calendario oficial
- Mantener activos solo los días relevantes para el año en curso
