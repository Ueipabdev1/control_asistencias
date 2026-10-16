import os

import pytest

from dev.apply_migration_packet import apply_packet
from dev.build_synthetic_packet import OUTPUT_DIRECTORY
from dev.database import TEST_DATABASE, reset_database
from dev.migration_packet import load_packet
from models import db, Grado, Seccion


@pytest.fixture(scope="module")
def rolled_over(app):
    packet = load_packet(OUTPUT_DIRECTORY)
    with app.app_context():
        apply_packet(packet)
        yield
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


def test_structure_menu_is_admin_only(rolled_over, client):
    admin_login(client)
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/admin/estructura"' in html
    assert "Estructura académica" in html

    client.get("/auth/logout")
    response = client.post("/auth/login", json={"email": "teacher1@dev.test", "password": "dev-only"})
    assert response.status_code == 200
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/admin/estructura"' not in html
    assert "Estructura académica" not in html


def test_structure_page_and_grade_creation(rolled_over, client):
    admin_login(client)
    response = client.get("/admin/estructura")
    assert response.status_code == 200
    assert "2026-2027" in response.get_data(as_text=True)

    response = client.post("/admin/estructura/grados", data={
        "id_etapa": 1,
        "nombre_grado": "Grado temporal",
        "orden": 99,
        "descripcion": "Synthetic grade",
        "activo": "on",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "creado correctamente" in response.get_data(as_text=True)
    grado = Grado.query.filter_by(nombre_grado="Grado temporal").one()
    assert grado.orden == 99
    assert grado.activo is True

    response = client.post("/admin/estructura/grados", data={
        "id_etapa": 1,
        "nombre_grado": "Grado temporal",
        "orden": 99,
        "activo": "on",
    }, follow_redirects=True)
    assert "Ya existe un grado" in response.get_data(as_text=True)
    assert Grado.query.filter_by(nombre_grado="Grado temporal").count() == 1


def test_used_grade_name_and_deactivation_are_blocked(rolled_over, client):
    admin_login(client)
    grado = Grado.query.get(1)
    original_name = grado.nombre_grado
    response = client.post("/admin/estructura/grados/1/editar", data={
        "nombre_grado": "Nombre no permitido",
        "orden": grado.orden,
        "activo": "on",
    }, follow_redirects=True)
    assert "No se puede renombrar" in response.get_data(as_text=True)
    assert grado.nombre_grado == original_name

    response = client.post("/admin/estructura/grados/1/editar", data={
        "nombre_grado": original_name,
        "orden": 99,
        "descripcion": "Orden actualizado",
        "activo": "on",
    }, follow_redirects=True)
    assert "actualizado correctamente" in response.get_data(as_text=True)
    assert grado.orden == 99
    assert grado.descripcion == "Orden actualizado"

    response = client.post("/admin/estructura/grados/1/editar", data={
        "nombre_grado": original_name,
        "orden": grado.orden,
    }, follow_redirects=True)
    assert "No se puede desactivar" in response.get_data(as_text=True)
    assert grado.activo is True


def test_section_create_rename_duplicate_and_deactivate(rolled_over, client):
    admin_login(client)
    response = client.post("/admin/estructura/secciones", data={
        "id_grado": 1,
        "nombre_seccion": "z",
        "activa": "on",
    }, follow_redirects=True)
    assert "creada" in response.get_data(as_text=True)
    seccion = Seccion.query.filter_by(id_grado=1, id_anio_escolar=2, nombre_seccion="Z").one()
    assert seccion.activa is True

    response = client.post("/admin/estructura/secciones", data={
        "id_grado": 1,
        "nombre_seccion": "Z",
        "activa": "on",
    }, follow_redirects=True)
    assert "Ya existe esa sección" in response.get_data(as_text=True)

    response = client.post(f"/admin/estructura/secciones/{seccion.id_seccion}/editar", data={
        "nombre_seccion": "Y",
        "activa": "on",
    }, follow_redirects=True)
    assert "actualizada correctamente" in response.get_data(as_text=True)
    assert seccion.nombre_seccion == "Y"

    response = client.post(f"/admin/estructura/secciones/{seccion.id_seccion}/editar", data={
        "nombre_seccion": "Y",
    }, follow_redirects=True)
    assert "actualizada correctamente" in response.get_data(as_text=True)
    assert seccion.activa is False


def test_used_section_rename_and_deactivate_are_blocked(rolled_over, client):
    admin_login(client)
    seccion = next(s for s in Seccion.query.filter_by(id_anio_escolar=2, activa=True).all() if s.inscripciones)
    original_name = seccion.nombre_seccion
    response = client.post(f"/admin/estructura/secciones/{seccion.id_seccion}/editar", data={
        "nombre_seccion": "Z",
        "activa": "on",
    }, follow_redirects=True)
    assert "No se puede renombrar" in response.get_data(as_text=True)
    assert seccion.nombre_seccion == original_name

    response = client.post(f"/admin/estructura/secciones/{seccion.id_seccion}/editar", data={
        "nombre_seccion": original_name,
    }, follow_redirects=True)
    assert "No se puede desactivar" in response.get_data(as_text=True)
    assert seccion.activa is True


def test_historical_section_is_read_only(rolled_over, client):
    admin_login(client)
    seccion = Seccion.query.filter_by(id_anio_escolar=1).first()
    original_name = seccion.nombre_seccion
    response = client.post(f"/admin/estructura/secciones/{seccion.id_seccion}/editar", data={
        "nombre_seccion": "Z",
        "activa": "on",
    }, follow_redirects=True)
    assert "históricas son de solo lectura" in response.get_data(as_text=True)
    assert seccion.nombre_seccion == original_name
