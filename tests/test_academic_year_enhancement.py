import os

import pandas as pd
import pytest

from dev.apply_migration_packet import apply_packet
from dev.build_synthetic_packet import OUTPUT_DIRECTORY
from dev.database import TEST_DATABASE, reset_database
from dev.migration_packet import load_packet
from models import (
    db,
    AnioEscolar,
    AsistenciaEstudiante,
    Estudiante,
    Inscripcion,
    Seccion,
)
from utils.excel_processor import buscar_seccion, procesar_excel_estudiantes


@pytest.fixture(scope="module")
def rolled_over(app):
    packet = load_packet(OUTPUT_DIRECTORY)
    with app.app_context():
        before_links = {
            row.id_asistencia_estudiante: row.id_inscripcion
            for row in AsistenciaEstudiante.query.all()
        }
        result = apply_packet(packet)
        yield result, before_links
        db.session.remove()
        db.engine.dispose()
        reset_database(os.environ["DATABASE_URL"], allowed_databases=(TEST_DATABASE,))
        from dev.enhance_academic_year import apply_schema, backfill
        from dev.synthetic_data import seed_synthetic_data
        apply_schema()
        seed_synthetic_data()
        backfill()


def admin_login(client):
    response = client.post("/auth/login", json={"email": "admin@dev.test", "password": "dev-only"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_rollover_preserves_history_and_promotes(rolled_over):
    result, before_links = rolled_over
    source_year = AnioEscolar.query.filter_by(nombre="2025-2026").one()
    target_year = AnioEscolar.query.filter_by(nombre="2026-2027").one()
    assert result["continuing"] == 28
    assert result["graduated"] == 2
    assert source_year.es_actual is False
    assert target_year.es_actual is True
    assert Inscripcion.query.filter_by(id_anio_escolar=source_year.id_anio_escolar).count() == 30
    assert Inscripcion.query.filter_by(id_anio_escolar=target_year.id_anio_escolar, estado="activo").count() == 28
    assert Seccion.query.filter_by(id_anio_escolar=source_year.id_anio_escolar, activa=False).count() == 15
    assert Seccion.query.filter_by(id_anio_escolar=target_year.id_anio_escolar, activa=True).count() == 15
    assert Estudiante.query.filter_by(activo=True).count() == 28
    assert Estudiante.query.filter_by(activo=False).count() == 2
    assert AsistenciaEstudiante.query.count() == 90
    for asistencia in AsistenciaEstudiante.query.all():
        assert asistencia.id_inscripcion == before_links[asistencia.id_asistencia_estudiante]


def test_current_section_apis_use_target_year(rolled_over, client):
    admin_login(client)
    for path in ("/secciones", "/api/matriculas"):
        response = client.get(path)
        assert response.status_code == 200
        rows = response.get_json()
        assert len(rows) == 15
        assert all(row["anio_escolar"] == "2026-2027" for row in rows)
        if path == "/secciones":
            assert sum(row["total_matricula"] for row in rows) == 28
        else:
            assert sum(row["total"] for row in rows) == 28

    response = client.get("/api/estudiantes/estadisticas")
    assert response.status_code == 200
    assert response.get_json()["total_estudiantes"] == 28

    response = client.get("/admin/validacion-matricula")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "2026-2027" in html
    assert "Asistencias sin inscripción" in html


def test_historical_statistics_and_logs_use_original_enrollments(rolled_over, client):
    admin_login(client)
    response = client.get("/admin/estadisticas?fecha_inicio=2026-03-02&fecha_fin=2026-03-03")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["estadisticas_generales"]["total_estudiantes"] == 30
    assert data["estadisticas_generales"]["total_asistencias"] == 90
    assert data["estadisticas_generales"]["total_asistentes"] == 80
    assert data["estadisticas_generales"]["total_secciones"] == 15

    response = client.get("/api/logs_asistencia")
    assert response.status_code == 200
    logs = response.get_json()
    assert len(logs) == 30
    assert {log["seccion"] for log in logs} == {
        f"{section.grado.nombre_grado} {section.nombre_seccion}"
        for section in Seccion.query.filter_by(id_anio_escolar=1).all()
    }


def test_complete_day_and_block_statistics(rolled_over, client):
    admin_login(client)
    response = client.get("/admin/estadisticas?fecha_inicio=2026-03-02&fecha_fin=2026-03-03&bloque=completo")
    data = response.get_json()
    assert data["estadisticas_generales"]["total_estudiantes"] == 30
    assert data["estadisticas_generales"]["total_asistentes"] == 50
    assert data["estadisticas_generales"]["total_asistencias"] == 50

    response = client.get("/admin/estadisticas?fecha_inicio=2026-03-02&fecha_fin=2026-03-03&bloque=bloque_1")
    data = response.get_json()
    assert data["estadisticas_generales"]["total_asistencias"] == 30
    assert data["estadisticas_generales"]["total_asistentes"] == 20


def test_attendance_write_uses_target_enrollment(rolled_over, client):
    admin_login(client)
    estudiante = Estudiante.query.filter_by(activo=True).first()
    target_enrollment = Inscripcion.query.filter_by(
        id_estudiante=estudiante.id_estudiante,
        id_anio_escolar=2,
        estado="activo",
    ).one()
    response = client.post("/api/asistencia-individual/guardar", json={
        "fecha": "2026-09-01",
        "id_seccion": estudiante.id_seccion,
        "bloque": "bloque_1",
        "asistencias": [{"id_estudiante": estudiante.id_estudiante, "presente": True}],
    })
    assert response.status_code == 200
    assert response.get_json()["registros_creados"] == 1
    asistencia = AsistenciaEstudiante.query.filter_by(
        id_estudiante=estudiante.id_estudiante,
        fecha="2026-09-01",
        bloque="bloque_1",
    ).one()
    assert asistencia.id_inscripcion == target_enrollment.id_inscripcion


def test_graduate_cannot_write_target_attendance(rolled_over, client):
    admin_login(client)
    graduate = Estudiante.query.filter_by(activo=False).first()
    response = client.post("/api/asistencia-individual/guardar", json={
        "fecha": "2026-09-01",
        "id_seccion": graduate.id_seccion,
        "bloque": "bloque_1",
        "asistencias": [{"id_estudiante": graduate.id_estudiante, "presente": True}],
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["registros_creados"] == 0
    assert data["errores"]


def test_excel_section_matching_single_a_vs_split(rolled_over):
    assert buscar_seccion("1er. Año", "U").nombre_seccion == "A"
    assert buscar_seccion("4to. Año", "U") is None


def test_98_excel_import_creates_current_enrollment(rolled_over, tmp_path):
    path = tmp_path / "students.xlsx"
    pd.DataFrame([{
        "Grado": "1er. Año",
        "Sección": "U",
        "Nombre": "Nuevo",
        "Apellido": "Sintético",
        "Cédula de identidad": "V-99999999",
        "Género": "M",
    }]).to_excel(path, index=False)
    result = procesar_excel_estudiantes(str(path), sobrescribir=False)
    assert result["success"] is True
    assert result["procesados"] == 1
    estudiante = Estudiante.query.filter_by(cedula="V99999999").one()
    enrollment = Inscripcion.query.filter_by(
        id_estudiante=estudiante.id_estudiante,
        id_anio_escolar=2,
        estado="activo",
    ).one()
    assert enrollment.id_seccion == estudiante.id_seccion


def test_99_manual_student_crud_syncs_enrollment(rolled_over, client):
    admin_login(client)
    sections = Seccion.query.filter_by(id_anio_escolar=2, activa=True).limit(2).all()
    response = client.post("/api/estudiantes", json={
        "nombre": "Manual",
        "apellido": "Sintético",
        "cedula": "V88888888",
        "genero": "F",
        "id_seccion": sections[0].id_seccion,
    })
    assert response.status_code == 201
    estudiante = Estudiante.query.filter_by(cedula="V88888888").one()
    enrollment = Inscripcion.query.filter_by(
        id_estudiante=estudiante.id_estudiante,
        id_anio_escolar=2,
        estado="activo",
    ).one()
    assert enrollment.id_seccion == sections[0].id_seccion

    response = client.put(f"/api/estudiantes/{estudiante.id_estudiante}", json={
        "id_seccion": sections[1].id_seccion,
    })
    assert response.status_code == 200
    assert enrollment.id_seccion == sections[1].id_seccion
    assert estudiante.id_seccion == sections[1].id_seccion

    response = client.delete(f"/api/estudiantes/{estudiante.id_estudiante}")
    assert response.status_code == 200
    assert enrollment.estado == "retirado"
    assert estudiante.activo is False
