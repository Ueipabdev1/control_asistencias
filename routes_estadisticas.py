from collections import defaultdict
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy.orm import selectinload

from models import db, Etapa, Grado, Seccion, AsistenciaEstudiante, Inscripcion
from utils.academic_year import HISTORICAL_STATUSES, academic_year_for_date

estadisticas_bp = Blueprint('estadisticas', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import redirect, url_for, flash
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.rol != 'administrador':
            flash('No tienes permiso para acceder a esta página', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def _enrollment_options():
    return (
        selectinload(Inscripcion.estudiante),
        selectinload(Inscripcion.seccion).selectinload(Seccion.grado).selectinload(Grado.etapa),
    )


def _filtered_data(fecha_inicio, fecha_fin, etapa, seccion_id, bloque_filter=None):
    year = academic_year_for_date(fecha_inicio)
    if academic_year_for_date(fecha_fin).id_anio_escolar != year.id_anio_escolar:
        raise ValueError('El rango de fechas debe pertenecer al mismo período académico')

    enrollments_query = Inscripcion.query.options(*_enrollment_options()).join(
        Seccion, Inscripcion.id_seccion == Seccion.id_seccion
    ).join(
        Grado, Seccion.id_grado == Grado.id_grado
    ).join(
        Etapa, Grado.id_etapa == Etapa.id_etapa
    ).filter(
        Inscripcion.id_anio_escolar == year.id_anio_escolar,
        Inscripcion.estado.in_(HISTORICAL_STATUSES),
    )
    if etapa:
        enrollments_query = enrollments_query.filter(Etapa.nombre_etapa == etapa)
    if seccion_id:
        enrollments_query = enrollments_query.filter(Seccion.id_seccion == seccion_id)
    enrollments = enrollments_query.all()

    attendance_query = AsistenciaEstudiante.query.join(
        Inscripcion, AsistenciaEstudiante.id_inscripcion == Inscripcion.id_inscripcion
    ).join(
        Seccion, Inscripcion.id_seccion == Seccion.id_seccion
    ).join(
        Grado, Seccion.id_grado == Grado.id_grado
    ).join(
        Etapa, Grado.id_etapa == Etapa.id_etapa
    ).filter(
        AsistenciaEstudiante.fecha >= fecha_inicio,
        AsistenciaEstudiante.fecha <= fecha_fin,
        Inscripcion.id_anio_escolar == year.id_anio_escolar,
        Inscripcion.estado.in_(HISTORICAL_STATUSES),
    )
    if etapa:
        attendance_query = attendance_query.filter(Etapa.nombre_etapa == etapa)
    if seccion_id:
        attendance_query = attendance_query.filter(Seccion.id_seccion == seccion_id)
    if bloque_filter:
        attendance_query = attendance_query.filter(AsistenciaEstudiante.bloque == bloque_filter)
    attendance_query = attendance_query.options(
        selectinload(AsistenciaEstudiante.inscripcion).selectinload(Inscripcion.estudiante),
        selectinload(AsistenciaEstudiante.inscripcion).selectinload(Inscripcion.seccion).selectinload(Seccion.grado).selectinload(Grado.etapa),
    )
    return enrollments, attendance_query.all()


def _percentage(total, expected):
    return round(total / expected * 100, 1) if expected else 0


def _names(enrollments):
    sections = {}
    stages = {}
    for enrollment in enrollments:
        section = enrollment.seccion
        sections[section.id_seccion] = f"{section.grado.nombre_grado} {section.nombre_seccion}"
        stages[section.grado.etapa.nombre_etapa] = section.grado.etapa.nombre_etapa
    return sections, stages


def _normal_stats(enrollments, attendance):
    present = [record for record in attendance if record.presente]
    total_estudiantes = len(enrollments)
    dias_analizados = len({record.fecha for record in attendance}) or 1

    genero_data = {}
    for genero, key in [('M', 'masculino'), ('F', 'femenino')]:
        matricula = sum(enrollment.genero == genero for enrollment in enrollments)
        total = sum(record.inscripcion.genero == genero for record in present)
        genero_data[key] = {
            'total': total,
            'matricula': matricula,
            'porcentaje': _percentage(total, matricula * dias_analizados),
        }

    section_names, stage_names = _names(enrollments)
    seccion_data = {}
    for section_id, nombre in section_names.items():
        matricula = sum(enrollment.id_seccion == section_id for enrollment in enrollments)
        total = sum(record.inscripcion.id_seccion == section_id for record in present)
        seccion_data[nombre] = {
            'total': total,
            'matricula': matricula,
            'porcentaje': _percentage(total, matricula * dias_analizados),
        }

    etapa_data = {}
    for nombre in stage_names:
        matricula = sum(enrollment.seccion.grado.etapa.nombre_etapa == nombre for enrollment in enrollments)
        total = sum(record.inscripcion.seccion.grado.etapa.nombre_etapa == nombre for record in present)
        etapa_data[nombre] = {
            'total': total,
            'matricula': matricula,
            'porcentaje': _percentage(total, matricula * dias_analizados),
        }

    grouped = defaultdict(lambda: {'students': set(), 'presentes': 0})
    for record in attendance:
        grouped[record.fecha]['students'].add(record.id_estudiante)
        grouped[record.fecha]['presentes'] += int(record.presente)
    tendencia_data = []
    for fecha in sorted(grouped):
        values = grouped[fecha]
        expected = len(values['students'])
        tendencia_data.append({
            'periodo': str(fecha),
            'total_asistentes': values['presentes'],
            'total_esperado': expected,
            'porcentaje': _percentage(values['presentes'], expected),
        })

    return {
        'estadisticas_generales': {
            'total_estudiantes': total_estudiantes,
            'total_asistencias': len(attendance),
            'total_asistentes': len(present),
            'porcentaje_total': _percentage(len(present), total_estudiantes * dias_analizados),
            'dias_analizados': dias_analizados,
            'total_secciones': len({record.inscripcion.id_seccion for record in attendance}),
        },
        'por_genero': genero_data,
        'por_seccion': seccion_data,
        'por_etapa': etapa_data,
        'tendencia_temporal': tendencia_data,
    }


def _complete_day_stats(enrollments, attendance):
    grouped = defaultdict(list)
    for record in attendance:
        grouped[(record.id_estudiante, record.fecha)].append(record)

    presentes = set()
    for (student_id, fecha), records in grouped.items():
        complete = [record for record in records if record.bloque == 'completo']
        if complete:
            if complete[0].presente:
                presentes.add((student_id, fecha))
        else:
            present_count = sum(record.presente for record in records)
            if present_count > len(records) / 2:
                presentes.add((student_id, fecha))

    enrollment_info = {enrollment.id_estudiante: enrollment for enrollment in enrollments}
    total_estudiantes = len(enrollments)
    dias_analizados = len(grouped) and len({fecha for _, fecha in grouped}) or 1
    total_asistentes = len(presentes)

    genero_data = {}
    for genero, key in [('M', 'masculino'), ('F', 'femenino')]:
        matricula = sum(enrollment.genero == genero for enrollment in enrollments)
        total = sum(
            student_id in enrollment_info and enrollment_info[student_id].genero == genero
            for student_id, _ in presentes
        )
        genero_data[key] = {
            'total': total,
            'matricula': matricula,
            'porcentaje': _percentage(total, matricula * dias_analizados),
        }

    section_names, stage_names = _names(enrollments)
    seccion_data = {}
    for section_id, nombre in section_names.items():
        matricula = sum(enrollment.id_seccion == section_id for enrollment in enrollments)
        total = sum(
            student_id in enrollment_info and enrollment_info[student_id].id_seccion == section_id
            for student_id, _ in presentes
        )
        seccion_data[nombre] = {
            'total': total,
            'matricula': matricula,
            'porcentaje': _percentage(total, matricula * dias_analizados),
        }

    etapa_data = {}
    for nombre in stage_names:
        matricula = sum(enrollment.seccion.grado.etapa.nombre_etapa == nombre for enrollment in enrollments)
        total = sum(
            student_id in enrollment_info and enrollment_info[student_id].seccion.grado.etapa.nombre_etapa == nombre
            for student_id, _ in presentes
        )
        etapa_data[nombre] = {
            'total': total,
            'matricula': matricula,
            'porcentaje': _percentage(total, matricula * dias_analizados),
        }

    by_date = defaultdict(int)
    for _, fecha in presentes:
        by_date[fecha] += 1
    tendencia_data = []
    for fecha in sorted({fecha for _, fecha in grouped}):
        total = by_date[fecha]
        tendencia_data.append({
            'periodo': str(fecha),
            'total_asistentes': total,
            'total_esperado': total_estudiantes,
            'porcentaje': _percentage(total, total_estudiantes),
        })

    present_sections = {
        enrollment_info[student_id].id_seccion
        for student_id, _ in presentes
        if student_id in enrollment_info
    }
    return {
        'estadisticas_generales': {
            'total_estudiantes': total_estudiantes,
            'total_asistencias': total_asistentes,
            'total_asistentes': total_asistentes,
            'porcentaje_total': _percentage(total_asistentes, total_estudiantes * dias_analizados),
            'dias_analizados': dias_analizados,
            'total_secciones': len(present_sections) or len(section_names),
        },
        'por_genero': genero_data,
        'por_seccion': seccion_data,
        'por_etapa': etapa_data,
        'tendencia_temporal': tendencia_data,
    }


@estadisticas_bp.route('/estadisticas')
@login_required
@admin_required
def obtener_estadisticas():
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        etapa = request.args.get('etapa', '')
        seccion_id = request.args.get('seccion', '')
        bloque = request.args.get('bloque', '')

        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date() if fecha_inicio else datetime.now().date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date() if fecha_fin else datetime.now().date()
        seccion_id = int(seccion_id) if seccion_id else None
        usar_dia_completo = bloque == 'completo'
        bloque_filter = bloque if bloque in ('bloque_1', 'bloque_2', 'bloque_3', 'bloque_4') else None

        enrollments, attendance = _filtered_data(
            fecha_inicio,
            fecha_fin,
            etapa,
            seccion_id,
            bloque_filter,
        )
        if usar_dia_completo:
            resultado = _complete_day_stats(enrollments, attendance)
        else:
            resultado = _normal_stats(enrollments, attendance)
        resultado.update({
            'success': True,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
        })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
