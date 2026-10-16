import pytest
from sqlalchemy import inspect, text

from models import (
    db,
    AsistenciaEstudiante,
    Estudiante,
    Grado,
    ObservacionSeccion,
    ProfesorSeccion,
    Seccion,
)


def test_application_uses_isolated_test_database(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"].endswith("control_asistencias_test?charset=utf8mb4")
    assert db.session.execute(text("SELECT DATABASE()")).scalar() == "control_asistencias_test"


def test_as_is_schema_and_synthetic_baseline(app):
    tables = set(inspect(db.engine).get_table_names())
    assert {
        "asistencia_estudiante",
        "estudiante",
        "etapa",
        "grado",
        "seccion",
        "secciones",
        "observacion_seccion",
        "profesor_seccion",
    } <= tables
    attendance_columns = {column["name"] for column in inspect(db.engine).get_columns("asistencia_estudiante")}
    assert {"id_estudiante", "fecha", "bloque", "presente"} <= attendance_columns

    assert Grado.query.count() == 14
    assert Seccion.query.count() == 15
    assert Estudiante.query.count() == 30
    assert AsistenciaEstudiante.query.count() == 90
    assert ObservacionSeccion.query.count() == 15
    assert ProfesorSeccion.query.count() == 15
    assert {row[0] for row in db.session.query(AsistenciaEstudiante.bloque).distinct()} == {
        "completo",
        "bloque_1",
        "bloque_2",
    }


def test_login_and_current_sections_endpoint(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "Iniciar" in response.get_data(as_text=True)

    response = client.post("/auth/login", json={"email": "admin@dev.test", "password": "dev-only"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    response = client.get("/secciones")
    assert response.status_code == 200
    sections = response.get_json()
    assert len(sections) == 15
    assert sum(section["total_matricula"] for section in sections) == 30


@pytest.mark.characterization
def test_current_attendance_queries_follow_the_students_current_section(app):
    estudiante = Estudiante.query.filter_by(id_seccion=1).first()
    attendance_ids = [row.id_asistencia_estudiante for row in estudiante.asistencias]

    def attendance_sections():
        return {
            row[0]
            for row in db.session.query(Seccion.id_seccion)
            .join(Estudiante, Estudiante.id_seccion == Seccion.id_seccion)
            .join(AsistenciaEstudiante, AsistenciaEstudiante.id_estudiante == Estudiante.id_estudiante)
            .filter(AsistenciaEstudiante.id_asistencia_estudiante.in_(attendance_ids))
            .all()
        }

    assert attendance_sections() == {1}
    estudiante.id_seccion = 2
    db.session.flush()
    assert attendance_sections() == {2}
