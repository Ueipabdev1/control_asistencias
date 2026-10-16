import os
from pathlib import Path

from dev.build_synthetic_packet import OUTPUT_DIRECTORY
from dev.database import DEVELOPMENT_DATABASE, TEST_DATABASE, database_settings
from dev.migration_packet import load_packet, validate_local_teacher_links
from utils.academic_year import current_academic_year

DEFAULT_PACKET_DIRECTORY = Path(OUTPUT_DIRECTORY)


def apply_packet(packet):
    from models import (
        AnioEscolar,
        AsistenciaEstudiante,
        Estudiante,
        Grado,
        Inscripcion,
        ProfesorSeccion,
        Seccion,
        Usuario,
        db,
    )

    target_year = AnioEscolar.query.filter_by(nombre=packet.manifest["academic_period"]).one()
    source_year = current_academic_year()
    if source_year.id_anio_escolar == target_year.id_anio_escolar:
        raise RuntimeError(f"Academic year {target_year.nombre} is already current")
    if target_year.es_actual:
        raise RuntimeError(f"Refusing to apply packet over current year {target_year.nombre}")
    if Inscripcion.query.filter_by(id_anio_escolar=target_year.id_anio_escolar).count():
        raise RuntimeError(f"Target year {target_year.nombre} already has enrollments")
    if any(row["status"] == "new_intake" for row in packet.students):
        raise RuntimeError("New-intake creation requires a separately approved roster")

    validate_local_teacher_links(packet.teacher_sections)

    students_by_match_key = {}
    source_enrollments = {}
    for row in packet.students:
        matches = Estudiante.query.filter_by(cedula=row["match_key"]).all()
        if len(matches) != 1:
            raise RuntimeError(f"{row['source_student_id']}: expected one local student, found {len(matches)}")
        estudiante = matches[0]
        source_enrollment = Inscripcion.query.filter_by(
            id_estudiante=estudiante.id_estudiante,
            id_anio_escolar=source_year.id_anio_escolar,
        ).first()
        if not source_enrollment:
            raise RuntimeError(f"{row['source_student_id']}: missing source-year enrollment")
        if row["status"] == "continuing" and (source_enrollment.estado != "activo" or not estudiante.activo):
            raise RuntimeError(f"{row['source_student_id']}: continuing student is not active in source year")
        students_by_match_key[row["match_key"]] = estudiante
        source_enrollments[estudiante.id_estudiante] = source_enrollment

    attendance_links = {
        asistencia.id_asistencia_estudiante: asistencia.id_inscripcion
        for asistencia in AsistenciaEstudiante.query.all()
    }
    student_count = Estudiante.query.count()
    attendance_count = AsistenciaEstudiante.query.count()

    try:
        sections = {}
        for row in packet.sections:
            grade = Grado.query.filter_by(nombre_grado=row["grade"]).one()
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
                    activa=True,
                )
                db.session.add(section)
            if section.nombre_seccion != row["section"]:
                raise RuntimeError(f"Section mismatch for {row['grade']} / {row['section']}")
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

        assert Estudiante.query.count() == student_count
        assert AsistenciaEstudiante.query.count() == attendance_count
        assert Inscripcion.query.filter_by(id_anio_escolar=target_year.id_anio_escolar, estado="activo").count() == 28
        assert sum(row["status"] == "graduated" for row in packet.students) == 2
        assert Seccion.query.filter_by(id_anio_escolar=target_year.id_anio_escolar).count() == 15
        for asistencia in AsistenciaEstudiante.query.all():
            assert attendance_links[asistencia.id_asistencia_estudiante] == asistencia.id_inscripcion
        for row in packet.students:
            estudiante = students_by_match_key[row["match_key"]]
            target_enrollments = Inscripcion.query.filter_by(
                id_estudiante=estudiante.id_estudiante,
                id_anio_escolar=target_year.id_anio_escolar,
            ).all()
            if row["status"] == "continuing":
                assert len(target_enrollments) == 1 and target_enrollments[0].estado == "activo"
            else:
                assert len(target_enrollments) == 0

        db.session.commit()
        return {
            "students": len(packet.students),
            "continuing": sum(row["status"] == "continuing" for row in packet.students),
            "graduated": sum(row["status"] == "graduated" for row in packet.students),
            "sections": len(sections),
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

    from app import app

    with app.app_context():
        result = apply_packet(packet)
    print("Synthetic rollover completed: " + ", ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
