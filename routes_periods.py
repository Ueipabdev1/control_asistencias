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
from dev.draft_roster import (
    DraftApprovalError,
    delete_teacher_assignment,
    edit_student,
    load_draft,
    require_activation_ready,
    save_section,
    save_teacher_assignment,
    set_teacher_email,
    validate_draft,
)
from dev.migration_packet import load_packet
from models import db, AnioEscolar, AsistenciaEstudiante, Grado, Inscripcion, Seccion, Usuario
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
        'validated': False,
        'errors': [],
        'fingerprint': None,
        'manifest': None,
        'counts': None,
    }
    try:
        packet = load_draft(DEFAULT_PACKET_DIRECTORY)
    except Exception as exc:
        review['errors'].append(str(exc))
        return review

    if packet.manifest.get('academic_period') != year.nombre:
        return review

    readiness = packet.manifest.get('readiness') or {}
    review.update({
        'available': True,
        'validated': readiness.get('strict_ready') is True,
        'fingerprint': packet_fingerprint(packet),
        'manifest': packet.manifest,
        'counts': _packet_counts(packet),
    })
    try:
        load_packet(DEFAULT_PACKET_DIRECTORY)
        context = preflight_packet(packet)
        if context['target_year'].id_anio_escolar != year.id_anio_escolar:
            raise RuntimeError('The packet target does not match this academic period')
        require_activation_ready(packet)
        review['counts'] = context['counts']
        review['ready'] = True
    except Exception as exc:
        review['errors'].append(str(exc))
    return review


def _draft_target(id_anio_escolar):
    target_year = db.session.get(AnioEscolar, id_anio_escolar)
    if not target_year:
        abort(404)
    current_year = current_academic_year()
    if target_year.es_actual or target_year.fecha_inicio != current_year.fecha_fin + timedelta(days=1):
        abort(400, description='Solo se puede editar el sucesor planificado del período actual')
    packet = load_draft(DEFAULT_PACKET_DIRECTORY)
    if packet.manifest.get('academic_period') != target_year.nombre:
        abort(409, description='El borrador no corresponde al período seleccionado')
    return target_year, packet


def _destination(value):
    grade, separator, section = (value or '').partition('|')
    if not separator or not grade or not section:
        raise ValueError('Selecciona una sección de destino válida')
    return grade, section


def _draft_redirect(target_year):
    return redirect(url_for('periods.gestion_borrador', id_anio_escolar=target_year.id_anio_escolar))


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


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador')
@login_required
@admin_required
def gestion_borrador(id_anio_escolar):
    _require_management_enabled()
    target_year, packet = _draft_target(id_anio_escolar)
    readiness = packet.manifest.get('readiness') or {}
    teacher_profiles = {}
    for row in packet.teacher_sections:
        profile = teacher_profiles.setdefault(row['teacher_profile_id'], {
            'teacher_name': row['teacher_name'],
            'work_email': row['work_email'],
            'assignments': 0,
        })
        profile['assignments'] += 1
    grades = Grado.query.filter_by(activo=True).order_by(Grado.orden, Grado.nombre_grado).all()
    professors = Usuario.query.filter_by(rol='profesor', activo=True).order_by(
        Usuario.apellido,
        Usuario.nombre,
    ).all()
    return render_template(
        'gestion_borrador_matricula.html',
        year=target_year,
        packet=packet,
        counts=_packet_counts(packet),
        fingerprint=packet_fingerprint(packet),
        readiness=readiness,
        blockers=readiness.get('blockers') or {},
        teacher_profiles=teacher_profiles,
        grades=grades,
        professors=professors,
        csrf_token=_csrf_token(),
    )


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador/estudiantes/<source_student_id>', methods=['POST'])
@login_required
@admin_required
def editar_estudiante_borrador(id_anio_escolar, source_student_id):
    _require_management_enabled()
    _validate_csrf()
    target_year, packet = _draft_target(id_anio_escolar)
    try:
        status = request.form.get('status', '')
        target_grade = section = ''
        if status == 'continuing':
            target_grade, section = _destination(request.form.get('destination'))
        edit_student(
            DEFAULT_PACKET_DIRECTORY,
            packet,
            request.form.get('packet_fingerprint'),
            source_student_id,
            status,
            target_grade,
            section,
            request.form.get('review_required') == '1',
        )
        flash('Decisión del estudiante actualizada en el borrador', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return _draft_redirect(target_year)


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador/secciones/guardar', methods=['POST'])
@login_required
@admin_required
def guardar_seccion_borrador(id_anio_escolar):
    _require_management_enabled()
    _validate_csrf()
    target_year, packet = _draft_target(id_anio_escolar)
    try:
        save_section(
            DEFAULT_PACKET_DIRECTORY,
            packet,
            request.form.get('packet_fingerprint'),
            request.form.get('original_grade', ''),
            request.form.get('original_section', ''),
            request.form.get('grade', ''),
            request.form.get('section', ''),
            request.form.get('group_label', ''),
            request.form.get('active') == '1',
        )
        flash('Sección actualizada en el borrador', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return _draft_redirect(target_year)


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador/profesores/<teacher_profile_id>/correo', methods=['POST'])
@login_required
@admin_required
def guardar_correo_profesor_borrador(id_anio_escolar, teacher_profile_id):
    _require_management_enabled()
    _validate_csrf()
    target_year, packet = _draft_target(id_anio_escolar)
    try:
        set_teacher_email(
            DEFAULT_PACKET_DIRECTORY,
            packet,
            request.form.get('packet_fingerprint'),
            teacher_profile_id,
            request.form.get('work_email', ''),
        )
        flash('Correo docente actualizado en todas sus asignaciones del borrador', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return _draft_redirect(target_year)


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador/asignaciones/guardar', methods=['POST'])
@login_required
@admin_required
def guardar_asignacion_borrador(id_anio_escolar):
    _require_management_enabled()
    _validate_csrf()
    target_year, packet = _draft_target(id_anio_escolar)
    try:
        grade, section = _destination(request.form.get('destination'))
        save_teacher_assignment(
            DEFAULT_PACKET_DIRECTORY,
            packet,
            request.form.get('packet_fingerprint'),
            request.form.get('original_teacher_profile_id', ''),
            request.form.get('original_grade', ''),
            request.form.get('original_section', ''),
            request.form.get('teacher_profile_id', ''),
            grade,
            section,
        )
        flash('Asignación docente actualizada en el borrador', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return _draft_redirect(target_year)


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador/asignaciones/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_asignacion_borrador(id_anio_escolar):
    _require_management_enabled()
    _validate_csrf()
    target_year, packet = _draft_target(id_anio_escolar)
    try:
        delete_teacher_assignment(
            DEFAULT_PACKET_DIRECTORY,
            packet,
            request.form.get('packet_fingerprint'),
            request.form.get('teacher_profile_id', ''),
            request.form.get('grade', ''),
            request.form.get('section', ''),
        )
        flash('Asignación docente eliminada del borrador', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return _draft_redirect(target_year)


@period_bp.route('/periodos/<int:id_anio_escolar>/borrador/validar', methods=['POST'])
@login_required
@admin_required
def validar_borrador(id_anio_escolar):
    _require_management_enabled()
    _validate_csrf()
    target_year, packet = _draft_target(id_anio_escolar)
    try:
        from flask_login import current_user
        validate_draft(
            DEFAULT_PACKET_DIRECTORY,
            packet,
            request.form.get('packet_fingerprint'),
            current_user.email,
        )
        flash('Borrador validado. Ya puede revisarse para la activación confirmada', 'success')
    except DraftApprovalError as exc:
        flash('La validación sigue bloqueada: ' + '; '.join(exc.errors), 'danger')
    except Exception as exc:
        flash(str(exc), 'danger')
    return _draft_redirect(target_year)


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
            raise ValueError('No hay un borrador para este período')
        if request.form.get('packet_fingerprint') != packet_fingerprint(packet):
            raise ValueError('El paquete cambió desde la revisión; vuelve a validarlo')
        if request.form.get('confirmacion') != target_year.nombre:
            raise ValueError(f'Escribe {target_year.nombre} para confirmar la activación')
        context = preflight_packet(packet)
        if context['target_year'].id_anio_escolar != target_year.id_anio_escolar:
            raise ValueError('El paquete no corresponde al período seleccionado')
        require_activation_ready(packet)
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
