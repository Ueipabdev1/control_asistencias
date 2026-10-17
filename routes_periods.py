from datetime import datetime, timedelta
import secrets

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_required

from dev.apply_migration_packet import (
    DEFAULT_PACKET_DIRECTORY,
    apply_packet,
    packet_fingerprint,
    preflight_packet,
)
from dev.database import DEVELOPMENT_DATABASE, TEST_DATABASE, database_settings
from dev.migration_packet import load_packet
from models import db, AnioEscolar, AsistenciaEstudiante, Inscripcion, Seccion
from routes import admin_required
from utils.academic_year import current_academic_year

period_bp = Blueprint('periods', __name__, url_prefix='/admin')
CSRF_SESSION_KEY = 'academic_period_csrf_token'


def _csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _validate_csrf():
    expected = session.get(CSRF_SESSION_KEY, '')
    supplied = request.form.get('csrf_token', '')
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(400, description='Invalid academic-period form token')


def _require_management_enabled():
    if not current_app.config.get('ACADEMIC_PERIOD_ADMIN_ENABLED'):
        abort(403, description='Academic-period management is not enabled in this environment')
    database_settings(str(db.engine.url), (DEVELOPMENT_DATABASE, TEST_DATABASE))


def _period_state(year, current_year):
    if year.es_actual:
        return 'Actual', 'success'
    if year.fecha_fin < current_year.fecha_inicio:
        return 'Histórico', 'secondary'
    if year.fecha_inicio > current_year.fecha_fin:
        return 'Planificado', 'info'
    return 'Conflicto', 'danger'


def _packet_counts(packet):
    return {
        'students': len(packet.students),
        'continuing': sum(row['status'] == 'continuing' for row in packet.students),
        'graduated': sum(row['status'] == 'graduated' for row in packet.students),
        'retired': sum(row['status'] == 'retired' for row in packet.students),
        'sections': len(packet.sections),
        'teacher_assignments': len(packet.teacher_sections),
    }


def _packet_review(year, state):
    if state != 'Planificado':
        return None
    review = {
        'available': False,
        'ready': False,
        'errors': [],
        'fingerprint': None,
        'manifest': None,
        'counts': None,
    }
    try:
        packet = load_packet(DEFAULT_PACKET_DIRECTORY)
    except Exception as exc:
        review['errors'].append(str(exc))
        return review

    if packet.manifest.get('academic_period') != year.nombre:
        return review

    review.update({
        'available': True,
        'fingerprint': packet_fingerprint(packet),
        'manifest': packet.manifest,
        'counts': _packet_counts(packet),
    })
    try:
        context = preflight_packet(packet)
        if context['target_year'].id_anio_escolar != year.id_anio_escolar:
            raise RuntimeError('The packet target does not match this academic period')
        review['counts'] = context['counts']
        review['ready'] = True
    except Exception as exc:
        review['errors'].append(str(exc))
    return review


def _form_date(field):
    try:
        return datetime.strptime(request.form.get(field, ''), '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('Usa fechas válidas en formato YYYY-MM-DD') from exc


@period_bp.route('/periodos')
@login_required
@admin_required
def gestion_periodos():
    current_year = current_academic_year()
    years = []
    for year in AnioEscolar.query.order_by(AnioEscolar.fecha_inicio, AnioEscolar.id_anio_escolar).all():
        state, color = _period_state(year, current_year)
        years.append({
            'id': year.id_anio_escolar,
            'nombre': year.nombre,
            'codigo': year.codigo,
            'fecha_inicio': year.fecha_inicio,
            'fecha_fin': year.fecha_fin,
            'es_actual': year.es_actual,
            'state': state,
            'color': color,
            'secciones': Seccion.query.filter_by(id_anio_escolar=year.id_anio_escolar).count(),
            'inscripciones': Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar).count(),
            'activos': Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar, estado='activo').count(),
            'graduados': Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar, estado='graduado').count(),
            'asistencias': AsistenciaEstudiante.query.join(
                Inscripcion,
                AsistenciaEstudiante.id_inscripcion == Inscripcion.id_inscripcion,
            ).filter(Inscripcion.id_anio_escolar == year.id_anio_escolar).count(),
            'review': _packet_review(year, state),
        })

    management_enabled = bool(current_app.config.get('ACADEMIC_PERIOD_ADMIN_ENABLED'))
    return render_template(
        'gestion_periodos.html',
        current_year=current_year,
        years=years,
        management_enabled=management_enabled,
        csrf_token=_csrf_token() if management_enabled else None,
    )


@period_bp.route('/periodos', methods=['POST'])
@login_required
@admin_required
def crear_periodo():
    _require_management_enabled()
    _validate_csrf()
    try:
        fecha_inicio = _form_date('fecha_inicio')
        fecha_fin = _form_date('fecha_fin')
        if fecha_fin.year != fecha_inicio.year + 1 or fecha_fin <= fecha_inicio:
            raise ValueError('El período debe tener años consecutivos y fechas válidas')
        nombre = f'{fecha_inicio.year}-{fecha_fin.year}'
        codigo = f'{str(fecha_inicio.year)[2:]}{str(fecha_fin.year)[2:]}'
        latest = AnioEscolar.query.order_by(AnioEscolar.fecha_fin.desc(), AnioEscolar.id_anio_escolar.desc()).first()
        if latest and fecha_inicio != latest.fecha_fin + timedelta(days=1):
            raise ValueError(f'El nuevo período debe iniciar el día después de {latest.nombre}')
        if AnioEscolar.query.filter((AnioEscolar.nombre == nombre) | (AnioEscolar.codigo == codigo)).first():
            raise ValueError(f'Ya existe un período con el nombre o código {nombre}')

        db.session.add(AnioEscolar(
            nombre=nombre,
            codigo=codigo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            es_actual=False,
        ))
        db.session.commit()
        flash(f'Período {nombre} creado como planificado', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('periods.gestion_periodos'))


@period_bp.route('/periodos/<int:id_anio_escolar>/activar', methods=['POST'])
@login_required
@admin_required
def activar_periodo(id_anio_escolar):
    _require_management_enabled()
    _validate_csrf()
    target_year = db.session.get(AnioEscolar, id_anio_escolar)
    if not target_year:
        abort(404)
    try:
        packet = load_packet(DEFAULT_PACKET_DIRECTORY)
        if packet.manifest.get('academic_period') != target_year.nombre:
            raise ValueError('No hay un paquete aprobado para este período')
        if request.form.get('packet_fingerprint') != packet_fingerprint(packet):
            raise ValueError('El paquete cambió desde la revisión; vuelve a validarlo')
        if request.form.get('confirmacion') != target_year.nombre:
            raise ValueError(f'Escribe {target_year.nombre} para confirmar la activación')
        context = preflight_packet(packet)
        if context['target_year'].id_anio_escolar != target_year.id_anio_escolar:
            raise ValueError('El paquete no corresponde al período seleccionado')
        result = apply_packet(packet)
        flash(
            f"Período {target_year.nombre} activado: {result['continuing']} promovidos, "
            f"{result['graduated']} graduados y {result['attendance_preserved']} asistencias preservadas",
            'success',
        )
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return redirect(url_for('periods.gestion_periodos'))
