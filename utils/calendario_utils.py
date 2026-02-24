"""
Utilidades para trabajar con el calendario escolar
Funciones helper para cálculos de asistencia excluyendo días no laborables
"""

from datetime import datetime, timedelta, date
from models import CalendarioEscolar, db
from sqlalchemy import extract


def contar_dias_laborables(fecha_inicio, fecha_fin, excluir_fines_semana=True):
    """
    Cuenta los días laborables entre dos fechas, excluyendo días no laborables
    
    Args:
        fecha_inicio: Fecha de inicio (date o datetime)
        fecha_fin: Fecha de fin (date o datetime)
        excluir_fines_semana: Si True, excluye sábados y domingos (default: True)
    
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
        # Verificar si es día laborable
        es_fin_semana = fecha_actual.weekday() >= 5  # 5=sábado, 6=domingo
        es_no_laborable = fecha_actual in fechas_no_laborables
        
        if excluir_fines_semana:
            if not es_fin_semana and not es_no_laborable:
                dias_laborables += 1
        else:
            if not es_no_laborable:
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
        list: Lista de objetos CalendarioEscolar
    """
    dias = CalendarioEscolar.query.filter(
        extract('year', CalendarioEscolar.fecha) == año,
        extract('month', CalendarioEscolar.fecha) == mes,
        CalendarioEscolar.activo == True
    ).order_by(CalendarioEscolar.fecha).all()
    
    return dias


def obtener_dias_no_laborables_rango(fecha_inicio, fecha_fin):
    """
    Obtiene todos los días no laborables en un rango de fechas
    
    Args:
        fecha_inicio: Fecha de inicio (date o datetime)
        fecha_fin: Fecha de fin (date o datetime)
    
    Returns:
        list: Lista de objetos CalendarioEscolar
    """
    # Convertir a date si es datetime
    if isinstance(fecha_inicio, datetime):
        fecha_inicio = fecha_inicio.date()
    if isinstance(fecha_fin, datetime):
        fecha_fin = fecha_fin.date()
    
    dias = CalendarioEscolar.query.filter(
        CalendarioEscolar.fecha >= fecha_inicio,
        CalendarioEscolar.fecha <= fecha_fin,
        CalendarioEscolar.activo == True
    ).order_by(CalendarioEscolar.fecha).all()
    
    return dias


def es_dia_laborable(fecha):
    """
    Verifica si una fecha específica es día laborable
    
    Args:
        fecha: Fecha a verificar (date o datetime)
    
    Returns:
        tuple: (es_laborable: bool, motivo: str o None)
    """
    # Convertir a date si es datetime
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    
    # Verificar si es fin de semana
    if fecha.weekday() >= 5:
        return False, "Fin de semana"
    
    # Verificar si está en calendario escolar
    dia_no_laborable = CalendarioEscolar.query.filter_by(
        fecha=fecha,
        activo=True
    ).first()
    
    if dia_no_laborable:
        return False, f"{dia_no_laborable.tipo.title()}: {dia_no_laborable.descripcion}"
    
    return True, None


def obtener_fechas_laborables_mes(año, mes):
    """
    Obtiene todas las fechas laborables de un mes
    
    Args:
        año: Año (int)
        mes: Mes (int, 1-12)
    
    Returns:
        list: Lista de objetos date con fechas laborables
    """
    # Obtener primer y último día del mes
    primer_dia = date(año, mes, 1)
    if mes == 12:
        ultimo_dia = date(año + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(año, mes + 1, 1) - timedelta(days=1)
    
    # Obtener días no laborables del mes
    dias_no_laborables = obtener_dias_no_laborables_mes(año, mes)
    fechas_no_laborables = {d.fecha for d in dias_no_laborables}
    
    # Generar lista de fechas laborables
    fechas_laborables = []
    fecha_actual = primer_dia
    
    while fecha_actual <= ultimo_dia:
        # Excluir fines de semana y días no laborables
        if fecha_actual.weekday() < 5 and fecha_actual not in fechas_no_laborables:
            fechas_laborables.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    return fechas_laborables


def calcular_dias_laborables_por_mes(fecha_inicio, fecha_fin):
    """
    Calcula los días laborables agrupados por mes
    
    Args:
        fecha_inicio: Fecha de inicio (date o datetime)
        fecha_fin: Fecha de fin (date o datetime)
    
    Returns:
        dict: Diccionario con formato {(año, mes): dias_laborables}
    """
    # Convertir a date si es datetime
    if isinstance(fecha_inicio, datetime):
        fecha_inicio = fecha_inicio.date()
    if isinstance(fecha_fin, datetime):
        fecha_fin = fecha_fin.date()
    
    resultado = {}
    fecha_actual = fecha_inicio
    
    while fecha_actual <= fecha_fin:
        año = fecha_actual.year
        mes = fecha_actual.month
        
        # Calcular último día del mes o fecha_fin
        if mes == 12:
            ultimo_dia_mes = date(año + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia_mes = date(año, mes + 1, 1) - timedelta(days=1)
        
        fin_periodo = min(ultimo_dia_mes, fecha_fin)
        
        # Contar días laborables del mes
        dias = contar_dias_laborables(fecha_actual, fin_periodo)
        resultado[(año, mes)] = dias
        
        # Avanzar al siguiente mes
        if mes == 12:
            fecha_actual = date(año + 1, 1, 1)
        else:
            fecha_actual = date(año, mes + 1, 1)
    
    return resultado


def obtener_estadisticas_calendario(año, mes):
    """
    Obtiene estadísticas del calendario para un mes específico
    
    Args:
        año: Año (int)
        mes: Mes (int, 1-12)
    
    Returns:
        dict: Diccionario con estadísticas del mes
    """
    # Obtener primer y último día del mes
    primer_dia = date(año, mes, 1)
    if mes == 12:
        ultimo_dia = date(año + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(año, mes + 1, 1) - timedelta(days=1)
    
    # Calcular días totales
    dias_totales = (ultimo_dia - primer_dia).days + 1
    
    # Contar días laborables
    dias_laborables = contar_dias_laborables(primer_dia, ultimo_dia)
    
    # Obtener días no laborables
    dias_no_laborables = obtener_dias_no_laborables_mes(año, mes)
    
    # Contar por tipo
    tipos_count = {}
    for dia in dias_no_laborables:
        tipos_count[dia.tipo] = tipos_count.get(dia.tipo, 0) + 1
    
    # Contar fines de semana
    fines_semana = 0
    fecha_actual = primer_dia
    while fecha_actual <= ultimo_dia:
        if fecha_actual.weekday() >= 5:
            fines_semana += 1
        fecha_actual += timedelta(days=1)
    
    return {
        'año': año,
        'mes': mes,
        'dias_totales': dias_totales,
        'dias_laborables': dias_laborables,
        'fines_semana': fines_semana,
        'dias_no_laborables': len(dias_no_laborables),
        'tipos_no_laborables': tipos_count
    }
