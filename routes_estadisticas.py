"""
Rutas y endpoints para estadísticas basadas en asistencia individual
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_, case
from functools import wraps

from models import db, Etapa, Grado, Seccion, Estudiante, AsistenciaEstudiante, Usuario

# Blueprint para estadísticas
estadisticas_bp = Blueprint('estadisticas', __name__, url_prefix='/admin')

# Decorador para verificar que es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from flask import redirect, url_for, flash
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.rol != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@estadisticas_bp.route('/estadisticas')
@login_required
@admin_required
def obtener_estadisticas():
    """API para obtener estadísticas detalladas basadas en asistencia individual"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        etapa = request.args.get('etapa', '')
        seccion_id = request.args.get('seccion', '')
        
        # Convertir fechas
        if fecha_inicio:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        else:
            fecha_inicio = datetime.now().date()
            
        if fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        else:
            fecha_fin = datetime.now().date()
        
        # Query base para estudiantes con filtros
        estudiantes_query = db.session.query(Estudiante).join(
            Seccion, Estudiante.id_seccion == Seccion.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(Estudiante.activo == True)
        
        if etapa:
            estudiantes_query = estudiantes_query.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            estudiantes_query = estudiantes_query.filter(Seccion.id_seccion == int(seccion_id))
        
        # Total de estudiantes matriculados
        total_estudiantes = estudiantes_query.count()
        
        # Query base para asistencias con filtros
        asistencias_query = db.session.query(AsistenciaEstudiante).join(
            Estudiante, AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante
        ).join(
            Seccion, Estudiante.id_seccion == Seccion.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(
            and_(
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin,
                Estudiante.activo == True
            )
        )
        
        if etapa:
            asistencias_query = asistencias_query.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            asistencias_query = asistencias_query.filter(Seccion.id_seccion == int(seccion_id))
        
        # Total de registros de asistencia
        total_asistencias = asistencias_query.count()
        
        # Total de asistentes (presentes)
        total_asistentes = asistencias_query.filter(AsistenciaEstudiante.presente == True).count()
        
        # Calcular días analizados: contar fechas únicas con asistencias registradas
        dias_con_asistencias = db.session.query(
            func.count(func.distinct(AsistenciaEstudiante.fecha))
        ).join(
            Estudiante, AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante
        ).join(
            Seccion, Estudiante.id_seccion == Seccion.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(
            and_(
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin,
                Estudiante.activo == True
            )
        )
        
        if etapa:
            dias_con_asistencias = dias_con_asistencias.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            dias_con_asistencias = dias_con_asistencias.filter(Seccion.id_seccion == int(seccion_id))
        
        dias_analizados = dias_con_asistencias.scalar() or 0
        
        # Si no hay asistencias registradas, usar 1 para evitar división por cero
        if dias_analizados == 0:
            dias_analizados = 1
        
        # Calcular porcentaje de asistencia
        porcentaje_total = round((total_asistentes / (total_estudiantes * dias_analizados) * 100) if total_estudiantes > 0 and dias_analizados > 0 else 0, 1)
        
        # ===== ESTADÍSTICAS POR GÉNERO =====
        # Contar estudiantes por género
        estudiantes_por_genero = db.session.query(
            Estudiante.genero,
            func.count(Estudiante.id_estudiante).label('total')
        ).join(
            Seccion, Estudiante.id_seccion == Seccion.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(Estudiante.activo == True)
        
        if etapa:
            estudiantes_por_genero = estudiantes_por_genero.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            estudiantes_por_genero = estudiantes_por_genero.filter(Seccion.id_seccion == int(seccion_id))
        
        estudiantes_por_genero = estudiantes_por_genero.group_by(Estudiante.genero).all()
        
        matricula_h = 0
        matricula_m = 0
        for genero, total in estudiantes_por_genero:
            if genero == 'M':
                matricula_h = total
            elif genero == 'F':
                matricula_m = total
        
        # Contar asistentes por género
        asistentes_por_genero = db.session.query(
            Estudiante.genero,
            func.count(AsistenciaEstudiante.id_asistencia).label('total')
        ).join(
            AsistenciaEstudiante, Estudiante.id_estudiante == AsistenciaEstudiante.id_estudiante
        ).join(
            Seccion, Estudiante.id_seccion == Seccion.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(
            and_(
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin,
                AsistenciaEstudiante.presente == True,
                Estudiante.activo == True
            )
        )
        
        if etapa:
            asistentes_por_genero = asistentes_por_genero.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            asistentes_por_genero = asistentes_por_genero.filter(Seccion.id_seccion == int(seccion_id))
        
        asistentes_por_genero = asistentes_por_genero.group_by(Estudiante.genero).all()
        
        total_h = 0
        total_m = 0
        for genero, total in asistentes_por_genero:
            if genero == 'M':
                total_h = total
            elif genero == 'F':
                total_m = total
        
        genero_data = {
            'masculino': {
                'total': total_h,
                'matricula': matricula_h,
                'porcentaje': round((total_h / (matricula_h * dias_analizados) * 100) if matricula_h and dias_analizados else 0, 1)
            },
            'femenino': {
                'total': total_m,
                'matricula': matricula_m,
                'porcentaje': round((total_m / (matricula_m * dias_analizados) * 100) if matricula_m and dias_analizados else 0, 1)
            }
        }
        
        # ===== ESTADÍSTICAS POR SECCIÓN =====
        stats_seccion = db.session.query(
            Grado.nombre_grado,
            Seccion.nombre_seccion,
            func.count(func.distinct(Estudiante.id_estudiante)).label('total_estudiantes'),
            func.sum(case((AsistenciaEstudiante.presente == True, 1), else_=0)).label('total_asistentes')
        ).join(
            Estudiante, Seccion.id_seccion == Estudiante.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).outerjoin(
            AsistenciaEstudiante, and_(
                AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante,
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin
            )
        ).filter(Estudiante.activo == True)
        
        if etapa:
            stats_seccion = stats_seccion.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            stats_seccion = stats_seccion.filter(Seccion.id_seccion == int(seccion_id))
        
        stats_seccion = stats_seccion.group_by(Grado.nombre_grado, Seccion.nombre_seccion).all()
        
        seccion_data = {}
        for stat in stats_seccion:
            nombre_completo = f"{stat.nombre_grado} {stat.nombre_seccion}"
            total_esperado = stat.total_estudiantes * dias_analizados
            porcentaje = round((stat.total_asistentes / total_esperado * 100) if total_esperado > 0 else 0, 1)
            seccion_data[nombre_completo] = {
                'total': int(stat.total_asistentes or 0),
                'matricula': stat.total_estudiantes or 0,
                'porcentaje': porcentaje
            }
        
        # ===== ESTADÍSTICAS POR ETAPA =====
        stats_etapa = db.session.query(
            Etapa.nombre_etapa,
            func.count(func.distinct(Estudiante.id_estudiante)).label('total_estudiantes'),
            func.sum(case((AsistenciaEstudiante.presente == True, 1), else_=0)).label('total_asistentes')
        ).join(
            Grado, Etapa.id_etapa == Grado.id_etapa
        ).join(
            Seccion, Grado.id_grado == Seccion.id_grado
        ).join(
            Estudiante, Seccion.id_seccion == Estudiante.id_seccion
        ).outerjoin(
            AsistenciaEstudiante, and_(
                AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante,
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin
            )
        ).filter(Estudiante.activo == True).group_by(Etapa.nombre_etapa).all()
        
        etapa_data = {}
        for stat in stats_etapa:
            total_esperado = stat.total_estudiantes * dias_analizados
            porcentaje = round((stat.total_asistentes / total_esperado * 100) if total_esperado > 0 else 0, 1)
            etapa_data[stat.nombre_etapa] = {
                'total': int(stat.total_asistentes or 0),
                'matricula': stat.total_estudiantes or 0,
                'porcentaje': porcentaje
            }
        
        # ===== TENDENCIA TEMPORAL =====
        tendencia_query = db.session.query(
            AsistenciaEstudiante.fecha,
            func.count(func.distinct(Estudiante.id_estudiante)).label('total_estudiantes'),
            func.sum(case((AsistenciaEstudiante.presente == True, 1), else_=0)).label('total_asistentes')
        ).join(
            Estudiante, AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante
        ).join(
            Seccion, Estudiante.id_seccion == Seccion.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(
            and_(
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin,
                Estudiante.activo == True
            )
        )
        
        if etapa:
            tendencia_query = tendencia_query.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            tendencia_query = tendencia_query.filter(Seccion.id_seccion == int(seccion_id))
        
        tendencia_query = tendencia_query.group_by(AsistenciaEstudiante.fecha).order_by(AsistenciaEstudiante.fecha)
        
        tendencia_data = []
        for item in tendencia_query.all():
            total_esperado = item.total_estudiantes or 0
            porcentaje = round((item.total_asistentes / total_esperado * 100) if total_esperado > 0 else 0, 1)
            
            tendencia_data.append({
                'periodo': str(item.fecha),
                'total_asistentes': int(item.total_asistentes or 0),
                'total_esperado': int(total_esperado),
                'porcentaje': porcentaje
            })
        
        # Contar secciones únicas con asistencias en el rango
        secciones_con_asistencias = db.session.query(
            func.count(func.distinct(Seccion.id_seccion))
        ).join(
            Estudiante, Seccion.id_seccion == Estudiante.id_seccion
        ).join(
            AsistenciaEstudiante, Estudiante.id_estudiante == AsistenciaEstudiante.id_estudiante
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(
            and_(
                AsistenciaEstudiante.fecha >= fecha_inicio,
                AsistenciaEstudiante.fecha <= fecha_fin,
                Estudiante.activo == True
            )
        )
        
        if etapa:
            secciones_con_asistencias = secciones_con_asistencias.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            secciones_con_asistencias = secciones_con_asistencias.filter(Seccion.id_seccion == int(seccion_id))
        
        total_secciones = secciones_con_asistencias.scalar() or 0
        
        return jsonify({
            'success': True,
            'estadisticas_generales': {
                'total_estudiantes': total_estudiantes,
                'total_asistencias': total_asistencias,
                'total_asistentes': total_asistentes,
                'porcentaje_total': porcentaje_total,
                'dias_analizados': dias_analizados,
                'total_secciones': total_secciones
            },
            'por_genero': genero_data,
            'por_seccion': seccion_data,
            'por_etapa': etapa_data,
            'tendencia_temporal': tendencia_data,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat()
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error al obtener estadísticas: {str(e)}'})
