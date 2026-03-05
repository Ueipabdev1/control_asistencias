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

def _calcular_presencia_dia_completo(fecha_inicio, fecha_fin, etapa, seccion_id):
    """
    Para el filtro 'Dia Completo', calcula presencia virtual:
    - Si hay registro con bloque='completo', usa ese valor
    - Si solo hay bloques individuales, el estudiante es presente
      si asistio a mas de la mitad de los bloques registrados ese dia
    Retorna un set de tuplas (id_estudiante, fecha) de los que se consideran presentes
    """
    # Obtener todos los registros de asistencia en el rango
    query = db.session.query(
        AsistenciaEstudiante.id_estudiante,
        AsistenciaEstudiante.fecha,
        AsistenciaEstudiante.bloque,
        AsistenciaEstudiante.presente
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
        query = query.filter(Etapa.nombre_etapa == etapa)
    if seccion_id:
        query = query.filter(Seccion.id_seccion == int(seccion_id))

    registros = query.all()

    # Agrupar por (estudiante, fecha)
    from collections import defaultdict
    agrupado = defaultdict(list)
    for r in registros:
        agrupado[(r.id_estudiante, r.fecha)].append((r.bloque, r.presente))

    presentes = set()
    fechas_con_datos = set()

    for (est_id, fecha), bloques in agrupado.items():
        fechas_con_datos.add(fecha)
        # Verificar si hay registro de dia completo
        completo = [b for b in bloques if b[0] == 'completo']
        if completo:
            if completo[0][1]:  # presente en dia completo
                presentes.add((est_id, fecha))
            continue

        # Solo bloques individuales: contar
        total_bloques = len(bloques)
        bloques_presentes = sum(1 for b in bloques if b[1])
        if bloques_presentes > total_bloques / 2:
            presentes.add((est_id, fecha))

    return presentes, fechas_con_datos


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
        bloque = request.args.get('bloque', '')

        # Convertir fechas
        if fecha_inicio:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        else:
            fecha_inicio = datetime.now().date()

        if fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        else:
            fecha_fin = datetime.now().date()

        # Filtro de bloque para queries directas (bloques individuales)
        bloque_filter = None
        usar_dia_completo = False
        if bloque in ('bloque_1', 'bloque_2', 'bloque_3', 'bloque_4'):
            bloque_filter = bloque
        elif bloque == 'completo':
            usar_dia_completo = True

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

        total_estudiantes = estudiantes_query.count()

        # Para dia completo, calcular presencia virtual
        if usar_dia_completo:
            presentes_set, fechas_con_datos = _calcular_presencia_dia_completo(
                fecha_inicio, fecha_fin, etapa, seccion_id
            )
            dias_analizados = len(fechas_con_datos) or 1
            total_asistentes = len(presentes_set)
            total_asistencias = total_asistentes  # cada entrada en presentes_set es un registro virtual

            porcentaje_total = round(
                (total_asistentes / (total_estudiantes * dias_analizados) * 100)
                if total_estudiantes > 0 else 0, 1
            )

            # Obtener info de estudiantes para género y sección
            estudiantes_info = {e.id_estudiante: e for e in estudiantes_query.all()}

            # Estadísticas por género
            total_h = sum(1 for (eid, f) in presentes_set if estudiantes_info.get(eid) and estudiantes_info[eid].genero == 'M')
            total_m = sum(1 for (eid, f) in presentes_set if estudiantes_info.get(eid) and estudiantes_info[eid].genero == 'F')
            matricula_h = sum(1 for e in estudiantes_info.values() if e.genero == 'M')
            matricula_m = sum(1 for e in estudiantes_info.values() if e.genero == 'F')

            genero_data = {
                'masculino': {
                    'total': total_h, 'matricula': matricula_h,
                    'porcentaje': round((total_h / (matricula_h * dias_analizados) * 100) if matricula_h else 0, 1)
                },
                'femenino': {
                    'total': total_m, 'matricula': matricula_m,
                    'porcentaje': round((total_m / (matricula_m * dias_analizados) * 100) if matricula_m else 0, 1)
                }
            }

            # Estadísticas por sección
            seccion_data = {}
            from collections import defaultdict
            seccion_presentes = defaultdict(int)
            seccion_matricula = defaultdict(int)
            seccion_nombres = {}
            for e in estudiantes_info.values():
                sec = e.seccion
                nombre = f"{sec.grado.nombre_grado} {sec.nombre_seccion}" if sec.grado else sec.nombre_seccion
                seccion_nombres[sec.id_seccion] = nombre
                seccion_matricula[sec.id_seccion] += 1
            for (eid, f) in presentes_set:
                e = estudiantes_info.get(eid)
                if e:
                    seccion_presentes[e.id_seccion] += 1
            for sid, nombre in seccion_nombres.items():
                mat = seccion_matricula[sid]
                tot = seccion_presentes.get(sid, 0)
                total_esperado = mat * dias_analizados
                seccion_data[nombre] = {
                    'total': tot, 'matricula': mat,
                    'porcentaje': round((tot / total_esperado * 100) if total_esperado > 0 else 0, 1)
                }

            # Estadísticas por etapa
            etapa_data = {}
            etapa_presentes = defaultdict(int)
            etapa_matricula = defaultdict(int)
            for e in estudiantes_info.values():
                nombre_etapa = e.seccion.grado.etapa.nombre_etapa if e.seccion.grado else 'N/A'
                etapa_matricula[nombre_etapa] += 1
            for (eid, f) in presentes_set:
                e = estudiantes_info.get(eid)
                if e:
                    nombre_etapa = e.seccion.grado.etapa.nombre_etapa if e.seccion.grado else 'N/A'
                    etapa_presentes[nombre_etapa] += 1
            for nombre_etapa in etapa_matricula:
                mat = etapa_matricula[nombre_etapa]
                tot = etapa_presentes.get(nombre_etapa, 0)
                total_esperado = mat * dias_analizados
                etapa_data[nombre_etapa] = {
                    'total': tot, 'matricula': mat,
                    'porcentaje': round((tot / total_esperado * 100) if total_esperado > 0 else 0, 1)
                }

            # Tendencia temporal
            tendencia_por_fecha = defaultdict(lambda: {'presentes': 0, 'estudiantes': set()})
            for (eid, f) in presentes_set:
                tendencia_por_fecha[f]['presentes'] += 1
            # Contar estudiantes por fecha
            for f in fechas_con_datos:
                tendencia_por_fecha[f]['total'] = total_estudiantes
            tendencia_data = []
            for f in sorted(fechas_con_datos):
                tot_est = total_estudiantes
                tot_pres = tendencia_por_fecha[f]['presentes']
                tendencia_data.append({
                    'periodo': str(f),
                    'total_asistentes': tot_pres,
                    'total_esperado': tot_est,
                    'porcentaje': round((tot_pres / tot_est * 100) if tot_est > 0 else 0, 1)
                })

            # Contar secciones con datos
            secciones_con_datos = set()
            for (eid, f) in presentes_set:
                e = estudiantes_info.get(eid)
                if e:
                    secciones_con_datos.add(e.id_seccion)
            total_secciones = len(secciones_con_datos) or len(seccion_nombres)

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

        # ===== FLUJO NORMAL: sin filtro o bloque específico =====

        # Query base para asistencias
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
        if bloque_filter:
            asistencias_query = asistencias_query.filter(AsistenciaEstudiante.bloque == bloque_filter)

        total_asistencias = asistencias_query.count()
        total_asistentes = asistencias_query.filter(AsistenciaEstudiante.presente == True).count()

        # Dias analizados
        dias_query = db.session.query(
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
            dias_query = dias_query.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            dias_query = dias_query.filter(Seccion.id_seccion == int(seccion_id))
        if bloque_filter:
            dias_query = dias_query.filter(AsistenciaEstudiante.bloque == bloque_filter)

        dias_analizados = dias_query.scalar() or 1

        porcentaje_total = round(
            (total_asistentes / (total_estudiantes * dias_analizados) * 100)
            if total_estudiantes > 0 else 0, 1
        )

        # ===== ESTADÍSTICAS POR GÉNERO =====
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

        asistentes_genero_query = db.session.query(
            Estudiante.genero,
            func.count(AsistenciaEstudiante.id_asistencia_estudiante).label('total')
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
            asistentes_genero_query = asistentes_genero_query.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            asistentes_genero_query = asistentes_genero_query.filter(Seccion.id_seccion == int(seccion_id))
        if bloque_filter:
            asistentes_genero_query = asistentes_genero_query.filter(AsistenciaEstudiante.bloque == bloque_filter)

        asistentes_por_genero = asistentes_genero_query.group_by(Estudiante.genero).all()

        total_h = 0
        total_m = 0
        for genero, total in asistentes_por_genero:
            if genero == 'M':
                total_h = total
            elif genero == 'F':
                total_m = total

        genero_data = {
            'masculino': {
                'total': total_h, 'matricula': matricula_h,
                'porcentaje': round((total_h / (matricula_h * dias_analizados) * 100) if matricula_h and dias_analizados else 0, 1)
            },
            'femenino': {
                'total': total_m, 'matricula': matricula_m,
                'porcentaje': round((total_m / (matricula_m * dias_analizados) * 100) if matricula_m and dias_analizados else 0, 1)
            }
        }

        # ===== ESTADÍSTICAS POR SECCIÓN =====
        seccion_join_cond = [
            AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante,
            AsistenciaEstudiante.fecha >= fecha_inicio,
            AsistenciaEstudiante.fecha <= fecha_fin
        ]
        if bloque_filter:
            seccion_join_cond.append(AsistenciaEstudiante.bloque == bloque_filter)

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
            AsistenciaEstudiante, and_(*seccion_join_cond)
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
        etapa_join_cond = [
            AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante,
            AsistenciaEstudiante.fecha >= fecha_inicio,
            AsistenciaEstudiante.fecha <= fecha_fin
        ]
        if bloque_filter:
            etapa_join_cond.append(AsistenciaEstudiante.bloque == bloque_filter)

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
            AsistenciaEstudiante, and_(*etapa_join_cond)
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
        if bloque_filter:
            tendencia_query = tendencia_query.filter(AsistenciaEstudiante.bloque == bloque_filter)

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

        # Contar secciones
        secciones_query = db.session.query(
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
            secciones_query = secciones_query.filter(Etapa.nombre_etapa == etapa)
        if seccion_id:
            secciones_query = secciones_query.filter(Seccion.id_seccion == int(seccion_id))
        if bloque_filter:
            secciones_query = secciones_query.filter(AsistenciaEstudiante.bloque == bloque_filter)

        total_secciones = secciones_query.scalar() or 0

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
