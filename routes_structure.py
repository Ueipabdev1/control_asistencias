from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from models import db, AnioEscolar, Etapa, Grado, Inscripcion, ObservacionSeccion, Seccion
from routes import admin_required
from utils.academic_year import current_academic_year

structure_bp = Blueprint('structure', __name__, url_prefix='/admin')


def _structure_url():
    return redirect(url_for('structure.gestion_estructura'))


def _normalized_section(value):
    value = (value or '').strip()
    if value.upper() in ('U', 'UNICA', 'ÚNICA'):
        return 'Única'
    return value.upper()


def _valid_order(value):
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


@structure_bp.route('/estructura')
@login_required
@admin_required
def gestion_estructura():
    year = current_academic_year()
    etapas = Etapa.query.order_by(Etapa.id_etapa).all()
    grados = Grado.query.order_by(Grado.id_etapa, Grado.orden, Grado.nombre_grado).all()
    secciones = Seccion.query.filter_by(
        id_anio_escolar=year.id_anio_escolar,
    ).order_by(Seccion.id_grado, Seccion.nombre_seccion, Seccion.id_seccion).all()
    return render_template(
        'gestion_estructura.html',
        current_year=year,
        etapas=etapas,
        grados=grados,
        secciones=secciones,
    )


@structure_bp.route('/estructura/grados', methods=['POST'])
@login_required
@admin_required
def crear_grado():
    try:
        id_etapa = request.form.get('id_etapa', type=int)
        nombre = request.form.get('nombre_grado', '').strip()
        orden = request.form.get('orden', type=int)
        descripcion = request.form.get('descripcion', '').strip()
        if not Etapa.query.get(id_etapa):
            raise ValueError('Selecciona una etapa válida')
        if not nombre:
            raise ValueError('El nombre del grado es obligatorio')
        if not _valid_order(orden):
            raise ValueError('El orden debe ser un número mayor que cero')
        duplicado = Grado.query.filter(
            Grado.id_etapa == id_etapa,
            func.lower(Grado.nombre_grado) == nombre.lower(),
        ).first()
        if duplicado:
            raise ValueError('Ya existe un grado con ese nombre en la etapa')

        db.session.add(Grado(
            id_etapa=id_etapa,
            nombre_grado=nombre,
            orden=orden,
            descripcion=descripcion or None,
            activo=bool(request.form.get('activo')),
        ))
        db.session.commit()
        flash(f'Grado {nombre} creado correctamente', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return _structure_url()


@structure_bp.route('/estructura/grados/<int:id_grado>/editar', methods=['POST'])
@login_required
@admin_required
def editar_grado(id_grado):
    try:
        grado = Grado.query.get_or_404(id_grado)
        nombre = request.form.get('nombre_grado', '').strip()
        orden = request.form.get('orden', type=int)
        descripcion = request.form.get('descripcion', '').strip()
        activo = bool(request.form.get('activo'))
        if not nombre:
            raise ValueError('El nombre del grado es obligatorio')
        if not _valid_order(orden):
            raise ValueError('El orden debe ser un número mayor que cero')

        secciones = Seccion.query.filter_by(id_grado=id_grado).all()
        if nombre != grado.nombre_grado and secciones:
            raise ValueError('No se puede renombrar un grado que ya tiene secciones')
        duplicado = Grado.query.filter(
            Grado.id_etapa == grado.id_etapa,
            Grado.id_grado != id_grado,
            func.lower(Grado.nombre_grado) == nombre.lower(),
        ).first()
        if duplicado:
            raise ValueError('Ya existe otro grado con ese nombre en la etapa')
        if not activo and any(seccion.activa for seccion in secciones):
            raise ValueError('No se puede desactivar un grado con secciones activas')

        grado.nombre_grado = nombre
        grado.orden = orden
        grado.descripcion = descripcion or None
        grado.activo = activo
        db.session.commit()
        flash(f'Grado {nombre} actualizado correctamente', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return _structure_url()


@structure_bp.route('/estructura/secciones', methods=['POST'])
@login_required
@admin_required
def crear_seccion():
    try:
        year = current_academic_year()
        id_grado = request.form.get('id_grado', type=int)
        nombre = _normalized_section(request.form.get('nombre_seccion'))
        activa = bool(request.form.get('activa'))
        grado = Grado.query.get(id_grado)
        if not grado or not grado.activo:
            raise ValueError('Selecciona un grado activo')
        if not nombre:
            raise ValueError('La sección es obligatoria')
        if len(nombre) > 50:
            raise ValueError('El nombre de sección es demasiado largo')
        duplicada = Seccion.query.filter(
            Seccion.id_grado == id_grado,
            Seccion.id_anio_escolar == year.id_anio_escolar,
            func.lower(Seccion.nombre_seccion) == nombre.lower(),
        ).first()
        if duplicada:
            raise ValueError('Ya existe esa sección para el grado en el período actual')

        db.session.add(Seccion(
            id_grado=id_grado,
            id_anio_escolar=year.id_anio_escolar,
            nombre_seccion=nombre,
            activa=activa,
        ))
        db.session.commit()
        flash(f'Sección {nombre} creada para {grado.nombre_grado}', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return _structure_url()


@structure_bp.route('/estructura/secciones/<int:id_seccion>/editar', methods=['POST'])
@login_required
@admin_required
def editar_seccion(id_seccion):
    try:
        year = current_academic_year()
        seccion = Seccion.query.get_or_404(id_seccion)
        if seccion.id_anio_escolar != year.id_anio_escolar:
            raise ValueError('Las secciones históricas son de solo lectura')

        nombre = _normalized_section(request.form.get('nombre_seccion'))
        activa = bool(request.form.get('activa'))
        if not nombre:
            raise ValueError('La sección es obligatoria')
        if len(nombre) > 50:
            raise ValueError('El nombre de sección es demasiado largo')

        dependencias = Inscripcion.query.filter_by(id_seccion=id_seccion).count()
        dependencias += ObservacionSeccion.query.filter_by(id_seccion=id_seccion).count()
        if nombre != seccion.nombre_seccion and dependencias:
            raise ValueError('No se puede renombrar una sección con inscripciones u observaciones')
        duplicada = Seccion.query.filter(
            Seccion.id_seccion != id_seccion,
            Seccion.id_grado == seccion.id_grado,
            Seccion.id_anio_escolar == year.id_anio_escolar,
            func.lower(Seccion.nombre_seccion) == nombre.lower(),
        ).first()
        if duplicada:
            raise ValueError('Ya existe otra sección con ese nombre para el grado')
        if not activa and Inscripcion.query.filter_by(
            id_seccion=id_seccion,
            estado='activo',
        ).count():
            raise ValueError('No se puede desactivar una sección con estudiantes activos')

        seccion.nombre_seccion = nombre
        seccion.activa = activa
        db.session.commit()
        flash(f'Sección {nombre} actualizada correctamente', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    return _structure_url()
