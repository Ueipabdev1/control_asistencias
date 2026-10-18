import os
import re
import shutil

import pytest

from dev.apply_migration_packet import packet_fingerprint
from dev.build_synthetic_packet import OUTPUT_DIRECTORY
from dev.database import TEST_DATABASE, reset_database
from dev.draft_roster import load_draft
from dev.migration_packet import write_packet
from models import (
    db,
    AnioEscolar,
    AsistenciaEstudiante,
    Estudiante,
    Inscripcion,
    ObservacionSeccion,
    ProfesorSeccion,
    Seccion,
)


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
def draft_db(app, tmp_path, monkeypatch):
    with app.app_context():
        reset_baseline()
        packet_directory = tmp_path / "packet"
        shutil.copytree(OUTPUT_DIRECTORY, packet_directory)
        monkeypatch.setattr("routes_periods.DEFAULT_PACKET_DIRECTORY", packet_directory)
        yield packet_directory


def login(client, email="admin@dev.test"):
    response = client.post("/auth/login", json={"email": email, "password": "dev-only"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def hidden_value(html, name):
    match = re.search(rf'name="{re.escape(name)}" value="([^"]+)"', html)
    assert match, f"Missing hidden field {name}"
    return match.group(1)


def target_year():
    return AnioEscolar.query.filter_by(nombre="2026-2027").one()


def draft_form(client):
    target = target_year()
    response = client.get(f"/admin/periodos/{target.id_anio_escolar}/borrador")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    return html, hidden_value(html, "csrf_token"), hidden_value(html, "packet_fingerprint")


def validate_current_draft(client):
    _, csrf_token, fingerprint = draft_form(client)
    target = target_year()
    return client.post(f"/admin/periodos/{target.id_anio_escolar}/borrador/validar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
    }, follow_redirects=True)


def file_snapshot(directory):
    return {
        path.name: path.read_bytes()
        for path in directory.iterdir()
        if path.is_file()
    }


def database_snapshot():
    models = (
        AnioEscolar,
        Estudiante,
        Inscripcion,
        Seccion,
        ProfesorSeccion,
        AsistenciaEstudiante,
        ObservacionSeccion,
    )
    return {
        model.__tablename__: tuple(sorted(
            tuple(getattr(row, column.name) for column in model.__table__.columns)
            for row in model.query.all()
        ))
        for model in models
    }


def test_draft_requires_admin_csrf_flag_and_current_fingerprint(draft_db, client, app):
    target = target_year()
    before = file_snapshot(draft_db)
    response = client.get(f"/admin/periodos/{target.id_anio_escolar}/borrador")
    assert response.status_code == 302

    login(client, "teacher1@dev.test")
    response = client.get(f"/admin/periodos/{target.id_anio_escolar}/borrador")
    assert response.status_code == 302
    client.get("/auth/logout")

    login(client)
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/borrador/validar", data={})
    assert response.status_code == 400

    app.config["ACADEMIC_PERIOD_ADMIN_ENABLED"] = False
    try:
        response = client.get(f"/admin/periodos/{target.id_anio_escolar}/borrador")
        assert response.status_code == 403
    finally:
        app.config["ACADEMIC_PERIOD_ADMIN_ENABLED"] = True

    current = AnioEscolar.query.filter_by(es_actual=True).one()
    response = client.get(f"/admin/periodos/{current.id_anio_escolar}/borrador")
    assert response.status_code == 400

    _, csrf_token, _ = draft_form(client)
    packet = load_draft(draft_db)
    student = next(row for row in packet.students if row["status"] == "continuing")
    response = client.post(
        f"/admin/periodos/{target.id_anio_escolar}/borrador/estudiantes/{student['source_student_id']}",
        data={
            "csrf_token": csrf_token,
            "packet_fingerprint": "0" * 64,
            "status": "continuing",
            "destination": f"{student['target_grade']}|{student['section']}",
        },
        follow_redirects=True,
    )
    assert "El borrador cambió" in response.get_data(as_text=True)
    assert file_snapshot(draft_db) == before


def test_student_edit_invalidates_validation_without_touching_database(draft_db, client):
    login(client)
    response = validate_current_draft(client)
    assert "Borrador validado." in response.get_data(as_text=True)
    before = database_snapshot()

    packet = load_draft(draft_db)
    student = next(row for row in packet.students if row["status"] == "continuing")
    destination = next(
        row for row in packet.sections
        if row["active"] == "true" and (row["grade"], row["section"]) != (student["target_grade"], student["section"])
    )
    _, csrf_token, fingerprint = draft_form(client)
    target = target_year()
    response = client.post(
        f"/admin/periodos/{target.id_anio_escolar}/borrador/estudiantes/{student['source_student_id']}",
        data={
            "csrf_token": csrf_token,
            "packet_fingerprint": fingerprint,
            "status": "continuing",
            "destination": f"{destination['grade']}|{destination['section']}",
        },
        follow_redirects=True,
    )
    assert "Decisión del estudiante actualizada" in response.get_data(as_text=True)

    updated = load_draft(draft_db)
    updated_student = next(row for row in updated.students if row["source_student_id"] == student["source_student_id"])
    assert (updated_student["target_grade"], updated_student["section"]) == (destination["grade"], destination["section"])
    assert updated_student["section_source"] == "manual_review"
    assert updated.manifest["readiness"]["strict_ready"] is False
    assert packet_fingerprint(updated) != fingerprint
    assert database_snapshot() == before

    response = client.get("/admin/periodos")
    period_csrf = hidden_value(response.get_data(as_text=True), "csrf_token")
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/activar", data={
        "csrf_token": period_csrf,
        "packet_fingerprint": packet_fingerprint(updated),
        "confirmacion": "2026-2027",
    }, follow_redirects=True)
    assert "debe validarse" in response.get_data(as_text=True)
    assert AnioEscolar.query.filter_by(es_actual=True).one().nombre == "2025-2026"
    assert Inscripcion.query.filter_by(id_anio_escolar=target.id_anio_escolar).count() == 0


def test_section_and_assignment_edits_preserve_live_tables(draft_db, client):
    login(client)
    before = database_snapshot()
    packet = load_draft(draft_db)
    section = packet.sections[0]
    old_key = (section["grade"], section["section"])
    _, csrf_token, fingerprint = draft_form(client)
    target = target_year()
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/borrador/secciones/guardar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "original_grade": section["grade"],
        "original_section": section["section"],
        "grade": section["grade"],
        "section": "Z",
        "group_label": section["group_label"] + " editado",
        "active": "1",
    }, follow_redirects=True)
    assert "Sección actualizada" in response.get_data(as_text=True)

    updated = load_draft(draft_db)
    assert any((row["grade"], row["section"]) == (old_key[0], "Z") for row in updated.sections)
    for student in updated.students:
        if student["source_student_id"] in {
            row["source_student_id"] for row in packet.students
            if (row["target_grade"], row["section"]) == old_key
        }:
            assert student["section"] == "Z"
    for original in packet.teacher_sections:
        if (original["grade"], original["section"]) == old_key:
            assert any(
                row["teacher_profile_id"] == original["teacher_profile_id"]
                and row["grade"] == old_key[0]
                and row["section"] == "Z"
                for row in updated.teacher_sections
            )

    teacher = updated.teacher_sections[0]
    used = {(row["teacher_profile_id"], row["grade"], row["section"]) for row in updated.teacher_sections}
    free = next(
        row for row in updated.sections
        if row["active"] == "true" and (teacher["teacher_profile_id"], row["grade"], row["section"]) not in used
    )
    _, csrf_token, fingerprint = draft_form(client)
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/borrador/asignaciones/guardar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "original_teacher_profile_id": "",
        "original_grade": "",
        "original_section": "",
        "teacher_profile_id": teacher["teacher_profile_id"],
        "destination": f"{free['grade']}|{free['section']}",
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    alerts = [re.sub(r"<[^>]+>", " ", alert).strip() for alert in re.findall(r'<div class="alert alert-.*?</div>', html, re.S)]
    assert "Asignación docente actualizada" in html, alerts[:2]
    added = load_draft(draft_db)
    assert len(added.teacher_sections) == len(updated.teacher_sections) + 1

    _, csrf_token, fingerprint = draft_form(client)
    response = client.post(f"/admin/periodos/{target.id_anio_escolar}/borrador/asignaciones/eliminar", data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "teacher_profile_id": teacher["teacher_profile_id"],
        "grade": free["grade"],
        "section": free["section"],
    }, follow_redirects=True)
    assert "Asignación docente eliminada" in response.get_data(as_text=True)
    assert len(load_draft(draft_db).teacher_sections) == len(updated.teacher_sections)
    assert database_snapshot() == before


def test_validation_blocks_review_teacher_and_reconciliation_errors(draft_db, client):
    login(client)
    packet = load_draft(draft_db)
    teacher = packet.teacher_sections[0]
    _, csrf_token, fingerprint = draft_form(client)
    target = target_year()
    response = client.post(
        f"/admin/periodos/{target.id_anio_escolar}/borrador/profesores/{teacher['teacher_profile_id']}/correo",
        data={
            "csrf_token": csrf_token,
            "packet_fingerprint": fingerprint,
            "work_email": "missing@dev.test",
        },
        follow_redirects=True,
    )
    assert "Correo docente actualizado" in response.get_data(as_text=True)
    response = validate_current_draft(client)
    assert "expected one active local professor, found 0" in response.get_data(as_text=True)
    assert load_draft(draft_db).manifest["readiness"]["strict_ready"] is False

    packet = load_draft(draft_db)
    _, csrf_token, fingerprint = draft_form(client)
    client.post(
        f"/admin/periodos/{target.id_anio_escolar}/borrador/profesores/{teacher['teacher_profile_id']}/correo",
        data={
            "csrf_token": csrf_token,
            "packet_fingerprint": fingerprint,
            "work_email": teacher["work_email"],
        },
        follow_redirects=True,
    )
    response = validate_current_draft(client)
    assert "Borrador validado." in response.get_data(as_text=True)

    packet = load_draft(draft_db)
    student = next(row for row in packet.students if row["status"] == "continuing")
    _, csrf_token, fingerprint = draft_form(client)
    student_url = f"/admin/periodos/{target.id_anio_escolar}/borrador/estudiantes/{student['source_student_id']}"
    client.post(student_url, data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "status": "continuing",
        "destination": f"{student['target_grade']}|{student['section']}",
        "review_required": "1",
    }, follow_redirects=True)
    response = validate_current_draft(client)
    assert "requires manual review" in response.get_data(as_text=True)

    _, csrf_token, fingerprint = draft_form(client)
    client.post(student_url, data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "status": "continuing",
        "destination": f"{student['target_grade']}|{student['section']}",
    }, follow_redirects=True)
    response = validate_current_draft(client)
    assert "Borrador validado." in response.get_data(as_text=True)

    packet = load_draft(draft_db)
    packet.manifest["readiness"]["blockers"] = {"student.synthetic_blocker": 1}
    write_packet(draft_db, packet.students, packet.sections, packet.teacher_sections, packet.manifest)
    response = validate_current_draft(client)
    assert "reconciliación" in response.get_data(as_text=True)
    assert load_draft(draft_db).manifest["readiness"]["strict_ready"] is False


def test_invalid_student_decisions_do_not_write_packet(draft_db, client):
    login(client)
    packet = load_draft(draft_db)
    student = next(row for row in packet.students if row["status"] == "continuing")
    before = file_snapshot(draft_db)
    _, csrf_token, fingerprint = draft_form(client)
    target = target_year()
    url = f"/admin/periodos/{target.id_anio_escolar}/borrador/estudiantes/{student['source_student_id']}"
    response = client.post(url, data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "status": "new_intake",
        "destination": "",
    }, follow_redirects=True)
    assert "Estado de estudiante no permitido" in response.get_data(as_text=True)
    assert file_snapshot(draft_db) == before

    response = client.post(url, data={
        "csrf_token": csrf_token,
        "packet_fingerprint": fingerprint,
        "status": "continuing",
        "destination": "Grado inexistente|Z",
        "student_name": "Nombre no permitido",
    }, follow_redirects=True)
    assert "target section does not exist" in response.get_data(as_text=True)
    assert file_snapshot(draft_db) == before
