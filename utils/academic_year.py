from models import AnioEscolar, Estudiante, Inscripcion, Seccion, db

HISTORICAL_STATUSES = ("activo", "promovido", "graduado")


def current_academic_year():
    years = AnioEscolar.query.filter_by(es_actual=True).all()
    if len(years) != 1:
        raise RuntimeError(f"Expected exactly one current academic year, found {len(years)}")
    return years[0]


def academic_year_for_date(fecha):
    year = AnioEscolar.query.filter(
        AnioEscolar.fecha_inicio <= fecha,
        AnioEscolar.fecha_fin >= fecha,
    ).first()
    if not year:
        raise RuntimeError(f"No academic year contains {fecha}")
    return year


def attendance_write_year(fecha):
    year = academic_year_for_date(fecha)
    current_year = current_academic_year()
    if year.fecha_inicio > current_year.fecha_inicio:
        raise RuntimeError(f"El período {year.nombre} está planificado y no acepta asistencia")
    return year


def enrollment_for_student_date(id_estudiante, fecha, id_seccion=None):
    year = attendance_write_year(fecha)
    query = Inscripcion.query.filter_by(
        id_estudiante=id_estudiante,
        id_anio_escolar=year.id_anio_escolar,
    )
    if id_seccion is not None:
        query = query.filter_by(id_seccion=id_seccion)
    enrollments = query.all()
    if len(enrollments) != 1:
        raise RuntimeError(
            f"Expected one enrollment for student {id_estudiante} on {fecha}, found {len(enrollments)}"
        )
    enrollment = enrollments[0]
    if enrollment.estado in ("retirado", "inactivo"):
        raise RuntimeError(f"Student {id_estudiante} has no active enrollment for attendance writes")
    return enrollment


def sync_current_enrollment(estudiante, seccion, estado="activo", origen="manual"):
    year = current_academic_year()
    enrollment = Inscripcion.query.filter_by(
        id_estudiante=estudiante.id_estudiante,
        id_anio_escolar=year.id_anio_escolar,
    ).first()
    if not enrollment:
        enrollment = Inscripcion(
            id_estudiante=estudiante.id_estudiante,
            id_seccion=seccion.id_seccion,
            id_anio_escolar=year.id_anio_escolar,
        )
        db.session.add(enrollment)
    enrollment.id_seccion = seccion.id_seccion
    enrollment.estado = estado
    enrollment.origen = origen
    estudiante.id_seccion = seccion.id_seccion
    estudiante.activo = estado == "activo"
    return enrollment


def deactivate_current_enrollment(estudiante, estado="retirado"):
    year = current_academic_year()
    enrollment = Inscripcion.query.filter_by(
        id_estudiante=estudiante.id_estudiante,
        id_anio_escolar=year.id_anio_escolar,
    ).first()
    if enrollment:
        enrollment.estado = estado
    estudiante.activo = False
    return enrollment


def section_enrollments(id_seccion, current_only=False):
    query = Inscripcion.query.filter_by(id_seccion=id_seccion)
    if current_only:
        query = query.filter_by(
            id_anio_escolar=current_academic_year().id_anio_escolar,
            estado="activo",
        )
    else:
        query = query.filter(Inscripcion.estado.in_(HISTORICAL_STATUSES))
    return query
