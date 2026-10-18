import os
import re
import shutil

import pytest

from dev.apply_migration_packet import packet_fingerprint, preflight_packet
from dev.build_synthetic_packet import OUTPUT_DIRECTORY
from dev.database import TEST_DATABASE, reset_database
from dev.migration_packet import MigrationPacket, load_packet
from models import db, AnioEscolar, AsistenciaEstudiante, Estudiante, Inscripcion, Seccion


def reset_baseline():
    from dev.enhance_academic_year import apply_schema, backfill
    from dev.synthetic_data import seed_synthetic_data

    db.session.remove()
    db.engine.dispose()
    reset_database(os.environ["DATABASE_URL"], allowed_databases=(TEST_DATABASE,))
    apply_schema()
    seed_synthetic_data()
    backfill()


@pytest.fixture
def period_db(app, tmp_path, monkeypatch):
    with app.app_context():
        reset_baseline()
        packet_directory = tmp_path / "packet"
        shutil.copytree(OUTPUT_DIRECTORY, packet_directory)
        monkeypatch.setattr("routes_periods.DEFAULT_PACKET_DIRECTORY", packet_directory)
        yield packet_directory
        reset_baseline()


def admin_login(client):
    response = client.post("/auth/login", json={"email": "admin@dev.test", "password": "dev-only"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def hidden_value(html, name):
    match = re.search(rf'name="{re.escape(name)}" value="([^"]+)"', html)
    assert match, f"Missing hidden field {name}"
    return match.group(1)


def period_page(client):
    response = client.get("/admin/periodos")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    return html, hidden_value(html, "csrf_token")


def draft_form(client):
    target = AnioEscolar.query.filter_by(nombre="2026-2027").one()
    response = client.get(f"/admin/periodos/{target.id_anio_escolar}/borrador")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    return html, hidden_value(html, "csrf_token"), hidden_value(html, "packet_fingerprint")


def validate_current_draft(client):
    _, csrf_token, fingerprint = draft_form(client)
    target = AnioEscolar.query.filter_by(nombre="2026-2027").one()
    return client.post(f"/admin/periodos/{target.id_anio_escolar}/borrador/validar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
    }, follow_redirects=True)


def activation_form(client):
    response = validate_current_draft(client)
    assert "Borrador validado." in response.get_data(as_text=True)
    html, csrf_token = period_page(client)
    return html, csrf_token, hidden_value(html, "packet_fingerprint")


def test_period_page_and_menu_are_admin_only(period_db, client):
    admin_login(client)
    html, _ = period_page(client)
    assert "2025-2026" in html
    assert "2026-2027" in html
    assert "Actual" in html
    assert "Planificado" in html
    assert "Borrador pendiente de validación" in html

    response = client.get("/")
    html = response.get_data(as_text=True)
    assert 'href="/admin/periodos"' in html
    assert "Períodos académicos" in html

    client.get("/auth/logout")
    response = client.post("/auth/login", json={"email": "teacher1@dev.test", "password": "dev-only"})
    assert response.status_code == 200
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert 'href="/admin/periodos"' not in html
    assert "Períodos académicos" not in html
    response = client.get("/admin/periodos")
    assert response.status_code == 302


def test_create_planned_period_and_reject_invalid_dates(period_db, client):
    admin_login(client)
    _, csrf_token = period_page(client)
    response = client.post("/admin/periodos", data={
        "csrf_token": csrf_token,
        "fecha_inicio": "2027-09-01",
        "fecha_fin": "2028-08-31",
        "es_actual": "on",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "creado como planificado" in response.get_data(as_text=True)
    planned = AnioEscolar.query.filter_by(nombre="2027-2028").one()
    assert planned.codigo == "2728"
    assert planned.es_actual is False
    assert AnioEscolar.query.filter_by(es_actual=True).one().nombre == "2025-2026"

    response = client.post("/admin/periodos", data={
        "csrf_token": csrf_token,
        "fecha_inicio": "2027-09-01",
        "fecha_fin": "2028-08-31",
    }, follow_redirects=True)
    assert "debe iniciar el día después" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(nombre="2027-2028").count() == 1

    response = client.post("/admin/periodos", data={
        "csrf_token": csrf_token,
        "fecha_inicio": "2028-10-01",
        "fecha_fin": "2029-08-31",
    }, follow_redirects=True)
    assert "debe iniciar el día después" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(nombre="2028-2029").count() == 0


def test_period_mutations_require_csrf_and_feature_flag(period_db, client, app):
    admin_login(client)
    response = client.post("/admin/periodos", data={
        "fecha_inicio": "2028-09-01",
        "fecha_fin": "2029-08-31",
    })
    assert response.status_code == 400

    _, csrf_token = period_page(client)
    app.config["ACADEMIC_PERIOD_ADMIN_ENABLED"] = False
    try:
        response = client.post("/admin/periodos", data={
            "csrf_token": csrf_token,
            "fecha_inicio": "2028-09-01",
            "fecha_fin": "2029-08-31",
        })
        assert response.status_code == 403
        assert AnioEscolar.query.filter_by(nombre="2028-2029").count() == 0
    finally:
        app.config["ACADEMIC_PERIOD_ADMIN_ENABLED"] = True


def test_activation_requires_confirmation_and_reviewed_fingerprint(period_db, client):
    admin_login(client)
    _, csrf_token, fingerprint = activation_form(client)
    target = AnioEscolar.query.filter_by(nombre="2026-2027").one()

    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/activar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "confirmacion": "incorrecto",
    }, follow_redirects=True)
    assert "para confirmar la activación" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(es_actual=True).one().nombre == "2025-2026"
    assert Inscripcion.query.filter_by(id_anio_escolar=target.id_anio_escolar).count() == 0

    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/activar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": "0" * 64,
        "confirmacion": "2026-2027",
    }, follow_redirects=True)
    assert "paquete cambió" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(es_actual=True).one().nombre == "2025-2026"
    assert Inscripcion.query.filter_by(id_anio_escolar=target.id_anio_escolar).count() == 0


def test_missing_active_source_student_blocks_preflight(period_db):
    packet = load_packet(period_db)
    incomplete = MigrationPacket(
        students=packet.students[:-1],
        sections=packet.sections,
        teacher_sections=packet.teacher_sections,
        manifest=packet.manifest,
    )
    with pytest.raises(RuntimeError, match="missing 1 active source students"):
        preflight_packet(incomplete)


def test_target_with_enrollments_blocks_activation(period_db, client):
    target = AnioEscolar.query.filter_by(nombre="2026-2027").one()
    student = Estudiante.query.filter_by(activo=True).first()
    section = Seccion(id_grado=1, id_anio_escolar=target.id_anio_escolar, nombre_seccion="A", activa=True)
    db.session.add(section)
    db.session.flush()
    db.session.add(Inscripcion(
        id_estudiante=student.id_estudiante,
        id_seccion=section.id_seccion,
        id_anio_escolar=target.id_anio_escolar,
        estado="activo",
    ))
    db.session.commit()

    admin_login(client)
    html, csrf_token = period_page(client)
    assert "already has enrollments" in html
    assert 'name="confirmacion"' not in html
    packet = load_packet(period_db)
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/activar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": packet_fingerprint(packet),
        "confirmacion": "2026-2027",
    }, follow_redirects=True)
    assert "already has enrollments" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(es_actual=True).one().nombre == "2025-2026"
    assert AsistenciaEstudiante.query.count() == 90

    db.session.delete(Inscripcion.query.filter_by(id_anio_escolar=target.id_anio_escolar).one())
    db.session.delete(section)
    db.session.commit()


def test_web_activation_rolls_over_and_blocks_repeat(period_db, client):
    before_links = {
        row.id_asistencia_estudiante: row.id_inscripcion
        for row in AsistenciaEstudiante.query.all()
    }
    admin_login(client)
    _, csrf_token, fingerprint = activation_form(client)
    target = AnioEscolar.query.filter_by(nombre="2026-2027").one()
    data = {
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "confirmacion": "2026-2027",
    }
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/activar", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert "28 promovidos, 2 graduados y 90 asistencias preservadas" in response.get_data(as_text=True)

    source = AnioEscolar.query.filter_by(nombre="2025-2026").one()
    assert source.es_actual is False
    assert target.es_actual is True
    assert AnioEscolar.query.filter_by(es_actual=True).count() == 1
    assert Inscripcion.query.filter_by(id_anio_escolar=target.id_anio_escolar, estado="activo").count() == 28
    assert Inscripcion.query.filter_by(id_anio_escolar=source.id_anio_escolar, estado="graduado").count() == 2
    assert Seccion.query.filter_by(id_anio_escolar=target.id_anio_escolar).count() == 15
    assert AsistenciaEstudiante.query.count() == 90
    for attendance in AsistenciaEstudiante.query.all():
        assert attendance.id_inscripcion == before_links[attendance.id_asistencia_estudiante]

    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/activar", data=data, follow_redirects=True)
    assert "already current" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(es_actual=True).count() == 1
    assert Inscripcion.query.filter_by(id_anio_escolar=target.id_anio_escolar, estado="activo").count() == 28
