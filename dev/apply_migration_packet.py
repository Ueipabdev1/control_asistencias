import os
from pathlib import Path

from dev.build_synthetic_packet import OUTPUT_DIRECTORY
from dev.database import DEVELOPMENT_DATABASE, TEST_DATABASE, database_settings
from dev.migration_packet import load_packet, validate_local_teacher_links
from utils.academic_year import current_academic_year

DEFAULT_PACKET_DIRECTORY = Path(OUTPUT_DIRECTORY)


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def packet_fingerprint(packet):
    import hashlib
    import json

    canonical = json.dumps(packet.manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def preflight_packet(packet):
    from datetime import timedelta

    from models import AnioEscolar, Estudiante, Grado, Inscripcion

    target_year = AnioEscolar.query.filter_by(nombre=packet.manifest["academic_period"]).first()
    _require(target_year is not None, f"Target academic year {packet.manifest['academic_period']} does not exist")
    source_year = current_academic_year()
    _require(source_year.id_anio_escolar != target_year.id_anio_escolar, f"Academic year {target_year.nombre} is already current")
    _require(not target_year.es_actual, f"Refusing to apply packet over current year {target_year.nombre}")
    _require(
        target_year.fecha_inicio == source_year.fecha_fin + timedelta(days=1),
        f"Target year {target_year.nombre} must start immediately after {source_year.nombre}",
    )
    _require(
        Inscripcion.query.filter_by(id_anio_escolar=target_year.id_anio_escolar).count() == 0,
        f"Target year {target_year.nombre} already has enrollments",
    )
    _require(
        not any(row["status"] == "new_intake" for row in packet.students),
        "New-intake creation requires a separately approved roster",
    )

    validate_local_teacher_links(packet.teacher_sections)

    grades = {}
    for row in packet.sections:
        if row["grade"] not in grades:
            matches = Grado.query.filter_by(nombre_grado=row["grade"]).all()
            _require(len(matches) == 1, f"Expected one grade named {row['grade']}, found {len(matches)}")
            grades[row["grade"]] = matches[0]

    students_by_match_key = {}
    source_enrollments = {}
    for row in packet.students:
        _require(row["match_key"] not in students_by_match_key, f"Duplicate packet match key {row['match_key']}")
        matches = Estudiante.query.filter_by(cedula=row["match_key"]).all()
        _require(len(matches) == 1, f"{row['source_student_id']}: expected one local student, found {len(matches)}")
        estudiante = matches[0]
        source_enrollment = Inscripcion.query.filter_by(
            id_estudiante=estudiante.id_estudiante,
            id_anio_escolar=source_year.id_anio_escolar,
        ).first()
        _require(source_enrollment is not None, f"{row['source_student_id']}: missing source-year enrollment")
        _require(
            source_enrollment.estado == "activo" and estudiante.activo,
            f"{row['source_student_id']}: student is not active in source year",
        )
        students_by_match_key[row["match_key"]] = estudiante
        source_enrollments[estudiante.id_estudiante] = source_enrollment

    active_source_enrollments = Inscripcion.query.filter_by(
        id_anio_escolar=source_year.id_anio_escolar,
        estado="activo",
    ).all()
    missing_student_ids = [
        enrollment.id_estudiante
        for enrollment in active_source_enrollments
        if enrollment.id_estudiante not in source_enrollments
    ]
    _require(
        not missing_student_ids,
        f"Packet is missing {len(missing_student_ids)} active source students: {missing_student_ids}",
    )

    return {
        "source_year": source_year,
        "target_year": target_year,
        "grades": grades,
        "students_by_match_key": students_by_match_key,
        "source_enrollments": source_enrollments,
        "counts": {
            "students": len(packet.students),
            "continuing": sum(row["status"] == "continuing" for row in packet.students),
            "graduated": sum(row["status"] == "graduated" for row in packet.students),
            "retired": sum(row["status"] == "retired" for row in packet.students),
            "sections": len(packet.sections),
            "teacher_assignments": len(packet.teacher_sections),
        },
    }


def apply_packet(packet):
    from models import (
        AnioEscolar,
        AsistenciaEstudiante,
        Estudiante,
        Inscripcion,
        ProfesorSeccion,
        Seccion,
        Usuario,
        db,
    )

    context = preflight_packet(packet)
    source_year = context["source_year"]
    target_year = context["target_year"]
    students_by_match_key = context["students_by_match_key"]
    source_enrollments = context["source_enrollments"]
    counts = context["counts"]

    attendance_links = {
        asistencia.id_asistencia_estudiante: asistencia.id_inscripcion
        for asistencia in AsistenciaEstudiante.query.all()
    }
    student_count = Estudiante.query.count()
    attendance_count = AsistenciaEstudiante.query.count()

    try:
        sections = {}
        for row in packet.sections:
            grade = context["grades"][row["grade"]]
            section = Seccion.query.filter_by(
                id_grado=grade.id_grado,
                id_anio_escolar=target_year.id_anio_escolar,
                nombre_seccion=row["section"],
            ).first()
            if not section:
                section = Seccion(
                    id_grado=grade.id_grado,
                    id_anio_escolar=target_year.id_anio_escolar,
                    nombre_seccion=row["section"],
                )
                db.session.add(section)
            section.activa = row["active"].lower() == "true"
            sections[(row["grade"], row["section"])] = section
        db.session.flush()

        for row in packet.students:
            estudiante = students_by_match_key[row["match_key"]]
            source_enrollment = source_enrollments[estudiante.id_estudiante]
            if row["status"] == "continuing":
                target_section = sections[(row["target_grade"], row["section"])]
                enrollment = Inscripcion(
                    id_estudiante=estudiante.id_estudiante,
                    id_seccion=target_section.id_seccion,
                    id_anio_escolar=target_year.id_anio_escolar,
                    estado="activo",
                    origen=row["section_source"],
                )
                db.session.add(enrollment)
                source_enrollment.estado = "promovido"
                estudiante.id_seccion = target_section.id_seccion
                estudiante.activo = True
            elif row["status"] == "graduated":
                source_enrollment.estado = "graduado"
                estudiante.activo = False
            else:
                source_enrollment.estado = "retirado"
                estudiante.activo = False
        db.session.flush()

        for row in packet.teacher_sections:
            target_section = sections[(row["grade"], row["section"])]
            professor = Usuario.query.filter_by(
                email=row["work_email"].lower(),
                rol="profesor",
                activo=True,
            ).one()
            assignment = ProfesorSeccion.query.filter_by(
                id_profesor=professor.id_usuario,
                id_seccion=target_section.id_seccion,
            ).first()
            if not assignment:
                db.session.add(ProfesorSeccion(
                    id_profesor=professor.id_usuario,
                    id_seccion=target_section.id_seccion,
                ))

        Seccion.query.filter_by(id_anio_escolar=source_year.id_anio_escolar).update(
            {Seccion.activa: False},
            synchronize_session=False,
        )
        source_year.es_actual = False
        target_year.es_actual = True
        db.session.flush()

        _require(Estudiante.query.count() == student_count, "Student count changed during rollover")
        _require(AsistenciaEstudiante.query.count() == attendance_count, "Attendance count changed during rollover")
        _require(
            Inscripcion.query.filter_by(
                id_anio_escolar=target_year.id_anio_escolar,
                estado="activo",
            ).count() == counts["continuing"],
            "Target active enrollment count does not match the packet",
        )
        _require(
            Inscripcion.query.filter_by(
                id_anio_escolar=source_year.id_anio_escolar,
                estado="activo",
            ).count() == 0,
            "Source year still has active enrollments",
        )
        _require(AnioEscolar.query.filter_by(es_actual=True).count() == 1, "Expected exactly one current academic year")
        for asistencia in AsistenciaEstudiante.query.all():
            _require(
                attendance_links[asistencia.id_asistencia_estudiante] == asistencia.id_inscripcion,
                f"Attendance {asistencia.id_asistencia_estudiante} changed enrollment",
            )
        for row in packet.students:
            estudiante = students_by_match_key[row["match_key"]]
            source_enrollment = source_enrollments[estudiante.id_estudiante]
            target_enrollments = Inscripcion.query.filter_by(
                id_estudiante=estudiante.id_estudiante,
                id_anio_escolar=target_year.id_anio_escolar,
            ).all()
            if row["status"] == "continuing":
                _require(
                    len(target_enrollments) == 1 and target_enrollments[0].estado == "activo",
                    f"{row['source_student_id']}: invalid target enrollment",
                )
                _require(source_enrollment.estado == "promovido", f"{row['source_student_id']}: source was not promoted")
            else:
                _require(len(target_enrollments) == 0, f"{row['source_student_id']}: inactive student has target enrollment")
                expected_status = "graduado" if row["status"] == "graduated" else "retirado"
                _require(source_enrollment.estado == expected_status, f"{row['source_student_id']}: invalid source result")
                _require(not estudiante.activo, f"{row['source_student_id']}: inactive student remains active")

        db.session.commit()
        return {
            **counts,
            "attendance_preserved": attendance_count,
        }
    except Exception:
        db.session.rollback()
        raise


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    database_settings(database_url, (DEVELOPMENT_DATABASE, TEST_DATABASE))
    packet = load_packet(DEFAULT_PACKET_DIRECTORY)
    from dev.draft_roster import require_activation_ready
    require_activation_ready(packet)

    from app import app

    with app.app_context():
        result = apply_packet(packet)
    print("Synthetic rollover completed: " + ", ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
