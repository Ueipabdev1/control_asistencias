from datetime import date

import pytest

from models import (
    db,
    AsistenciaEstudiante,
    Estudiante,
    Matricula,
    ObservacionSeccion,
    ProfesorSeccion,
    Usuario,
)


ADMIN_REQUESTS = [
    ("post", "/api/usuario", {
        "nombre": "Intruso",
        "apellido": "Sintético",
        "email": "intruso@dev.test",
        "contraseña": "dev-only",
        "rol": "administrador",
    }),
    ("get", "/api/usuarios", None),
    ("put", "/api/usuario/{usuario_id}/rol", {"rol": "administrador"}),
    ("get", "/api/profesores", None),
    ("delete", "/api/profesor/3", None),
    ("get", "/api/secciones/Maternal", None),
    ("get", "/api/profesor/2/secciones", None),
    ("delete", "/api/profesor/2/seccion/1", None),
    ("post", "/api/profesor/asignar-secciones", {"profesor_id": 3, "secciones": [1]}),
    ("get", "/api/profesores/asignaciones", None),
    ("delete", "/api/profesor/2/secciones", None),
    ("get", "/api/matriculas", None),
    ("post", "/api/matricula", {"etapa": "Maternal", "seccion": "Única"}),
    ("get", "/api/matricula/{matricula_id}", None),
    ("put", "/api/matricula/{matricula_id}", {"num_estudiantes_h": 99, "num_estudiantes_m": 99}),
    ("delete", "/api/matricula/{matricula_id}", None),
    ("post", "/api/matriculas/sincronizar", None),
    ("get", "/admin/estadisticas-legacy", None),
    ("get", "/matricula", None),
    ("post", "/matricula", {"id_seccion": 1, "num_estudiantes_h": 99, "num_estudiantes_m": 99}),
]

ATTENDANCE_WRITE_DATE = date(2026, 3, 10)
BATCH_WRITE_DATE = date(2026, 3, 11)
ADMIN_BATCH_WRITE_DATE = date(2026, 3, 12)
OBSERVATION_WRITE_DATE = date(2026, 3, 10)


def login(client, email):
    response = client.post("/auth/login", json={"email": email, "password": "dev-only"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def administration_state():
    return {
        "users": [
            (u.id_usuario, u.email, u.rol, u.activo)
            for u in Usuario.query.order_by(Usuario.id_usuario).all()
        ],
        "assignments": [
            (a.id_profesor_seccion, a.id_profesor, a.id_seccion)
            for a in ProfesorSeccion.query.order_by(ProfesorSeccion.id_profesor_seccion).all()
        ],
        "enrollments": [
            (m.id_matricula, m.id_seccion, m.num_estudiantes_h, m.num_estudiantes_m, m.fecha_actualizacion)
            for m in Matricula.query.order_by(Matricula.id_matricula).all()
        ],
    }


def registration_payload(email, rol="administrador"):
    return {
        "nombre": "Registro",
        "apellido": "Sintético",
        "email": email,
        "password": "dev-only",
        "confirm_password": "dev-only",
        "rol": rol,
    }


def section_requests(section_id):
    return [
        ("get", f"/api/estudiantes/seccion/{section_id}", None),
        ("get", f"/api/asistencia-individual/2026-03-02/{section_id}", None),
        ("post", "/api/asistencia-individual/verificar", {
            "fecha": "2026-03-02",
            "id_seccion": section_id,
            "bloque": "completo",
        }),
        ("get", f"/api/asistencia-individual/estadisticas/{section_id}", None),
        ("post", "/api/observaciones/verificar", {
            "fecha": "2026-03-03",
            "id_seccion": section_id,
        }),
        ("get", f"/api/observaciones/2026-03-03/{section_id}", None),
    ]


@pytest.fixture
def temporary_user_emails():
    emails = []
    yield emails
    db.session.rollback()
    for email in emails:
        Usuario.query.filter_by(email=email).delete()
    db.session.commit()


@pytest.fixture
def authorization_write_cleanup():
    yield
    db.session.rollback()
    attendance_dates = [ATTENDANCE_WRITE_DATE, BATCH_WRITE_DATE, ADMIN_BATCH_WRITE_DATE]
    AsistenciaEstudiante.query.filter(AsistenciaEstudiante.fecha.in_(attendance_dates)).delete(
        synchronize_session=False
    )
    ObservacionSeccion.query.filter_by(fecha=OBSERVATION_WRITE_DATE).delete(synchronize_session=False)
    db.session.commit()


@pytest.mark.parametrize("actor", ["anonymous", "professor"])
def test_admin_apis_are_denied_without_mutations(client, actor):
    if actor == "professor":
        login(client, "teacher1@dev.test")
        usuario_id = 2
    else:
        usuario_id = 3

    matricula_id = Matricula.query.first().id_matricula
    for method, path, payload in ADMIN_REQUESTS:
        before = administration_state()
        request_path = path.format(usuario_id=usuario_id, matricula_id=matricula_id)
        kwargs = {"json": payload} if payload is not None else {}
        response = client.open(request_path, method=method, **kwargs)
        assert response.status_code in {302, 401, 403}, (actor, method, request_path)
        assert administration_state() == before, (actor, method, request_path)


@pytest.mark.parametrize("actor", ["anonymous", "professor"])
def test_registration_cannot_be_used_for_privilege_escalation(client, actor):
    if actor == "professor":
        login(client, "teacher1@dev.test")
    email = f"registro-{actor}@dev.test"

    assert client.get("/auth/registro").status_code in {302, 401, 403}
    response = client.post("/auth/registro", json=registration_payload(email))
    assert response.status_code in {302, 401, 403}
    assert Usuario.query.filter_by(email=email).count() == 0


def test_admin_registration_workflow(client, temporary_user_emails):
    email = "nuevo-admin@dev.test"
    temporary_user_emails.append(email)
    login(client, "admin@dev.test")

    response = client.get("/auth/registro")
    assert response.status_code == 200
    assert 'value="administrador"' in response.get_data(as_text=True)

    response = client.post("/auth/registro", json=registration_payload(email))
    assert response.status_code == 201
    usuario = Usuario.query.filter_by(email=email).one()
    assert usuario.rol == "administrador"
    assert usuario.is_active is True

    client.get("/auth/logout")
    login(client, email)
    assert client.get("/auth/registro").status_code == 200


def test_inactive_login_and_deactivated_existing_session(client, temporary_user_emails):
    email = "inactivo@dev.test"
    temporary_user_emails.append(email)
    from app import bcrypt

    inactive = Usuario(
        nombre="Inactivo",
        apellido="Sintético",
        email=email,
        contraseña=bcrypt.generate_password_hash("dev-only").decode("utf-8"),
        rol="profesor",
        activo=False,
    )
    db.session.add(inactive)
    db.session.commit()
    assert inactive.is_active is False

    response = client.post("/auth/login", json={"email": email, "password": "dev-only"})
    assert response.status_code == 401
    assert response.get_json() == {"success": False, "message": "Email o contraseña incorrectos"}
    with client.session_transaction() as session:
        assert "_user_id" not in session

    login(client, "teacher1@dev.test")
    assert client.get("/").status_code == 200
    teacher = Usuario.query.filter_by(email="teacher1@dev.test").one()
    assert teacher.is_active is True
    teacher.activo = False
    db.session.commit()
    try:
        assert client.get("/").status_code == 302
        assert client.get("/api/estudiantes/seccion/1").status_code == 302
    finally:
        teacher.activo = True
        db.session.commit()


def test_assigned_and_cross_section_reads_with_admin_controls(client):
    login(client, "teacher1@dev.test")
    assigned_student = Estudiante.query.filter_by(id_seccion=1).first()

    for assigned_request, cross_request in zip(section_requests(1), section_requests(9)):
        method, assigned_path, assigned_payload = assigned_request
        _, cross_path, cross_payload = cross_request
        kwargs = {"json": assigned_payload} if assigned_payload is not None else {}
        assert client.open(assigned_path, method=method, **kwargs).status_code == 200
        kwargs = {"json": cross_payload} if cross_payload is not None else {}
        response = client.open(cross_path, method=method, **kwargs)
        assert response.status_code == 403, (method, cross_path)
        assert response.get_json()["error"] == "Acceso denegado. Sección no asignada"

    assert client.get(f"/api/estudiantes/{assigned_student.id_estudiante}").status_code == 403
    assert client.get("/api/estudiantes/estadisticas").status_code == 403

    client.get("/auth/logout")
    login(client, "admin@dev.test")
    for method, path, payload in section_requests(9):
        kwargs = {"json": payload} if payload is not None else {}
        assert client.open(path, method=method, **kwargs).status_code == 200
    assert client.get(f"/api/estudiantes/{assigned_student.id_estudiante}").status_code == 200
    assert client.get("/api/estudiantes/estadisticas").status_code == 200


def test_cross_section_writes_and_mixed_batch_have_no_partial_writes(client, authorization_write_cleanup):
    login(client, "teacher1@dev.test")
    assigned_student = Estudiante.query.filter_by(id_seccion=1).first()
    cross_student = Estudiante.query.filter_by(id_seccion=9).first()

    response = client.post("/api/asistencia-individual/guardar", json={
        "fecha": ATTENDANCE_WRITE_DATE.isoformat(),
        "id_seccion": 9,
        "bloque": "completo",
        "asistencias": [{"id_estudiante": cross_student.id_estudiante, "presente": True}],
    })
    assert response.status_code == 403
    assert AsistenciaEstudiante.query.filter_by(
        id_estudiante=cross_student.id_estudiante,
        fecha=ATTENDANCE_WRITE_DATE,
    ).count() == 0

    response = client.post("/api/observaciones/guardar", json={
        "fecha": OBSERVATION_WRITE_DATE.isoformat(),
        "id_seccion": 9,
        "observaciones": "No autorizado",
    })
    assert response.status_code == 403
    assert ObservacionSeccion.query.filter_by(
        id_seccion=9,
        fecha=OBSERVATION_WRITE_DATE,
    ).count() == 0

    response = client.post("/api/asistencia-individual/registrar", json={
        "fecha": BATCH_WRITE_DATE.isoformat(),
        "asistencias": [
            {"id_estudiante": assigned_student.id_estudiante, "presente": True},
            {"id_estudiante": cross_student.id_estudiante, "presente": True},
        ],
    })
    assert response.status_code == 403
    assert AsistenciaEstudiante.query.filter_by(fecha=BATCH_WRITE_DATE).count() == 0


def test_assigned_professor_and_admin_write_success_controls(client, authorization_write_cleanup):
    login(client, "teacher1@dev.test")
    assigned_students = Estudiante.query.filter_by(id_seccion=1).limit(2).all()
    cross_student = Estudiante.query.filter_by(id_seccion=9).first()

    response = client.post("/api/asistencia-individual/guardar", json={
        "fecha": ATTENDANCE_WRITE_DATE.isoformat(),
        "id_seccion": 1,
        "bloque": "completo",
        "asistencias": [{"id_estudiante": assigned_students[0].id_estudiante, "presente": True}],
    })
    assert response.status_code == 200
    assert response.get_json()["registros_creados"] == 1

    response = client.post("/api/observaciones/guardar", json={
        "fecha": OBSERVATION_WRITE_DATE.isoformat(),
        "id_seccion": 1,
        "observaciones": "Control profesor asignado",
    })
    assert response.status_code == 200

    response = client.post("/api/asistencia-individual/registrar", json={
        "fecha": BATCH_WRITE_DATE.isoformat(),
        "asistencias": [
            {"id_estudiante": student.id_estudiante, "presente": True}
            for student in assigned_students
        ],
    })
    assert response.status_code == 200
    assert response.get_json()["creados"] == 2

    client.get("/auth/logout")
    login(client, "admin@dev.test")
    response = client.post("/api/asistencia-individual/registrar", json={
        "fecha": ADMIN_BATCH_WRITE_DATE.isoformat(),
        "asistencias": [
            {"id_estudiante": assigned_students[0].id_estudiante, "presente": True},
            {"id_estudiante": cross_student.id_estudiante, "presente": True},
        ],
    })
    assert response.status_code == 200
    assert response.get_json()["creados"] == 2
    assert AsistenciaEstudiante.query.filter_by(fecha=ADMIN_BATCH_WRITE_DATE).count() == 2
