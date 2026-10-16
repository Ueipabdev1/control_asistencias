import os
from pathlib import Path

from sqlalchemy import text

from dev.database import DEVELOPMENT_DATABASE, TEST_DATABASE, database_settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "migrations" / "add_academic_year_enrollment.sql"


def apply_schema():
    from models import db

    for statement in SCHEMA_PATH.read_text(encoding="utf-8").split(";"):
        if statement.strip():
            db.session.connection().exec_driver_sql(statement)
    db.session.commit()


def _constraint_exists(table, constraint):
    from models import db

    return db.session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = :table AND CONSTRAINT_NAME = :constraint"
        ),
        {"table": table, "constraint": constraint},
    ).scalar() > 0


def _drop_constraint_if_exists(table, constraint):
    from models import db

    if _constraint_exists(table, constraint):
        db.session.connection().exec_driver_sql(f"ALTER TABLE `{table}` DROP CONSTRAINT `{constraint}`")


def _add_constraint_if_missing(table, constraint, definition):
    from models import db

    if not _constraint_exists(table, constraint):
        db.session.connection().exec_driver_sql(f"ALTER TABLE `{table}` ADD CONSTRAINT `{constraint}` {definition}")


def backfill():
    from models import AnioEscolar, AsistenciaEstudiante, Estudiante, Inscripcion, Seccion, db

    year = AnioEscolar.query.filter_by(nombre="2025-2026").one()
    Seccion.query.filter(Seccion.id_anio_escolar.is_(None)).update(
        {Seccion.id_anio_escolar: year.id_anio_escolar},
        synchronize_session=False,
    )
    db.session.flush()

    for estudiante in Estudiante.query.all():
        enrollment = Inscripcion.query.filter_by(
            id_estudiante=estudiante.id_estudiante,
            id_anio_escolar=year.id_anio_escolar,
        ).first()
        if not enrollment:
            db.session.add(Inscripcion(
                id_estudiante=estudiante.id_estudiante,
                id_seccion=estudiante.id_seccion,
                id_anio_escolar=year.id_anio_escolar,
                estado="activo" if estudiante.activo else "retirado",
                origen="legacy",
            ))
    db.session.flush()

    enrollments = {
        enrollment.id_estudiante: enrollment
        for enrollment in Inscripcion.query.filter_by(id_anio_escolar=year.id_anio_escolar).all()
    }
    for asistencia in AsistenciaEstudiante.query.filter(AsistenciaEstudiante.id_inscripcion.is_(None)).all():
        enrollment = enrollments.get(asistencia.id_estudiante)
        if not enrollment:
            raise RuntimeError(f"Missing backfill enrollment for student {asistencia.id_estudiante}")
        asistencia.id_inscripcion = enrollment.id_inscripcion
    db.session.flush()

    db.session.connection().exec_driver_sql("ALTER TABLE `seccion` MODIFY `id_anio_escolar` INT(11) NOT NULL")
    db.session.connection().exec_driver_sql("ALTER TABLE `asistencia_estudiante` MODIFY `id_inscripcion` INT(11) NOT NULL")
    _add_constraint_if_missing(
        "seccion",
        "fk_seccion_anio",
        "FOREIGN KEY (`id_anio_escolar`) REFERENCES `anio_escolar` (`id_anio_escolar`) ON DELETE RESTRICT",
    )
    _drop_constraint_if_exists("seccion", "unique_seccion_grado")
    _add_constraint_if_missing(
        "seccion",
        "unique_seccion_anio_grado_nombre",
        "UNIQUE (`id_anio_escolar`, `id_grado`, `nombre_seccion`)",
    )
    _add_constraint_if_missing(
        "asistencia_estudiante",
        "fk_asistencia_inscripcion_estudiante",
        "FOREIGN KEY (`id_estudiante`, `id_inscripcion`) "
        "REFERENCES `inscripcion` (`id_estudiante`, `id_inscripcion`) ON DELETE RESTRICT",
    )
    db.session.commit()

    assert Seccion.query.filter(Seccion.id_anio_escolar.is_(None)).count() == 0
    assert AsistenciaEstudiante.query.filter(AsistenciaEstudiante.id_inscripcion.is_(None)).count() == 0
    assert Inscripcion.query.count() == Estudiante.query.count()


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    database_settings(database_url, (DEVELOPMENT_DATABASE, TEST_DATABASE))

    from app import app

    with app.app_context():
        apply_schema()
        backfill()
        print("Academic-year schema and 2025-2026 backfill completed")


if __name__ == "__main__":
    main()
