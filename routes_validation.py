from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from models import db, AnioEscolar, AsistenciaEstudiante, Estudiante, Inscripcion, Seccion
from routes import admin_required
from utils.academic_year import current_academic_year

validation_bp = Blueprint('validation', __name__, url_prefix='/admin')


@validation_bp.route('/validacion-matricula')
@login_required
@admin_required
def validacion_matricula():
    current_year = current_academic_year()
    years = []
    for year in AnioEscolar.query.order_by(AnioEscolar.id_anio_escolar).all():
        years.append({
            'nombre': year.nombre,
            'es_actual': year.es_actual,
            'secciones': Seccion.query.filter_by(id_anio_escolar=year.id_anio_escolar).count(),
            'inscripciones': Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar).count(),
            'activos': Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar, estado='activo').count(),
            'graduados': Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar, estado='graduado').count(),
            'asistencias': AsistenciaEstudiante.query.join(
                Inscripcion, AsistenciaEstudiante.id_inscripcion == Inscripcion.id_inscripcion
            ).filter(Inscripcion.id_anio_escolar == year.id_anio_escolar).count(),
        })

    section_rows = db.session.query(
        Seccion.id_seccion,
        Seccion.nombre_seccion,
        Seccion.id_grado,
        func.count(Inscripcion.id_inscripcion),
    ).outerjoin(
        Inscripcion, db.and_(
            Seccion.id_seccion == Inscripcion.id_seccion,
            Inscripcion.estado == 'activo',
        )
    ).filter(
        Seccion.id_anio_escolar == current_year.id_anio_escolar,
        Seccion.activa == True,
    ).group_by(Seccion.id_seccion, Seccion.nombre_seccion, Seccion.id_grado).order_by(Seccion.id_seccion).all()

    integrity = {
        'asistencias_sin_inscripcion': AsistenciaEstudiante.query.filter_by(id_inscripcion=None).count(),
        'estudiantes_activos_sin_inscripcion': Estudiante.query.filter_by(activo=True).outerjoin(
            Inscripcion, db.and_(
                Estudiante.id_estudiante == Inscripcion.id_estudiante,
                Inscripcion.id_anio_escolar == current_year.id_anio_escolar,
                Inscripcion.estado == 'activo',
            )
        ).filter(Inscripcion.id_inscripcion.is_(None)).count(),
        'periodos_actuales': AnioEscolar.query.filter_by(es_actual=True).count(),
    }

    return render_template(
        'enhancement_validation.html',
        current_year=current_year,
        years=years,
        section_rows=section_rows,
        integrity=integrity,
        total_asistencias=AsistenciaEstudiante.query.count(),
    )
