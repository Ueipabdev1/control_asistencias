from datetime import date

from models import db, AsistenciaEstudiante, Estudiante, Inscripcion


def admin_login(client):
    response = client.post("/auth/login", json={"email": "admin@dev.test", "password": "dev-only"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def attendance_ids(student_id, attendance_date):
    return {
        row.id_asistencia_estudiante
        for row in AsistenciaEstudiante.query.filter_by(
            id_estudiante=student_id,
            fecha=attendance_date,
        ).all()
    }


def test_planned_year_attendance_is_rejected_before_rollover(client):
    from models import Asistencia

    admin_login(client)
    student = Estudiante.query.filter_by(activo=True).first()
    attendance_date = date(2026, 9, 1)
    before = attendance_ids(student.id_estudiante, attendance_date)
    legacy_before = Asistencia.query.filter_by(
        id_seccion_legacy=student.id_seccion,
        fecha=attendance_date,
    ).count()

    responses = [
        client.post("/api/asistencia-individual/registrar", json={
            "fecha": attendance_date.isoformat(),
            "asistencias": [{"id_estudiante": student.id_estudiante, "presente": True}],
        }),
        client.post("/api/asistencia-individual/guardar", json={
            "fecha": attendance_date.isoformat(),
            "id_seccion": student.id_seccion,
            "bloque": "completo",
            "asistencias": [{"id_estudiante": student.id_estudiante, "presente": True}],
        }),
        client.post("/guardar_asistencia", json={
            "fecha": attendance_date.isoformat(),
            "id_seccion": student.id_seccion,
            "masculinos": 1,
            "femeninos": 0,
        }),
    ]

    for response in responses:
        assert response.status_code == 409
        assert response.get_json()["success"] is False
        assert "2026-2027" in response.get_json()["error"]
    assert attendance_ids(student.id_estudiante, attendance_date) == before
    assert Asistencia.query.filter_by(
        id_seccion_legacy=student.id_seccion,
        fecha=attendance_date,
    ).count() == legacy_before


def test_current_year_boundary_attendance_is_allowed(client):
    admin_login(client)
    student = Estudiante.query.filter_by(activo=True).first()
    attendance_date = date(2026, 8, 31)
    try:
        response = client.post("/api/asistencia-individual/guardar", json={
            "fecha": attendance_date.isoformat(),
            "id_seccion": student.id_seccion,
            "bloque": "completo",
            "asistencias": [{"id_estudiante": student.id_estudiante, "presente": True}],
        })
        assert response.status_code == 200
        assert response.get_json()["registros_creados"] == 1
        attendance = AsistenciaEstudiante.query.filter_by(
            id_estudiante=student.id_estudiante,
            fecha=attendance_date,
            bloque="completo",
        ).one()
        enrollment = Inscripcion.query.filter_by(
            id_estudiante=student.id_estudiante,
            id_anio_escolar=1,
        ).one()
        assert attendance.id_inscripcion == enrollment.id_inscripcion
    finally:
        AsistenciaEstudiante.query.filter_by(
            id_estudiante=student.id_estudiante,
            fecha=attendance_date,
            bloque="completo",
        ).delete(synchronize_session=False)
        db.session.commit()


def test_retired_enrollment_cannot_write_attendance(client):
    admin_login(client)
    student = Estudiante.query.filter_by(activo=True).first()
    enrollment = Inscripcion.query.filter_by(
        id_estudiante=student.id_estudiante,
        id_anio_escolar=1,
        estado="activo",
    ).one()
    attendance_dates = [date(2026, 4, 7), date(2026, 4, 8)]
    before = {
        attendance_date: attendance_ids(student.id_estudiante, attendance_date)
        for attendance_date in attendance_dates
    }
    enrollment.estado = "retirado"
    student.activo = False
    db.session.commit()
    try:
        responses = [
            client.post("/api/asistencia-individual/registrar", json={
                "fecha": attendance_dates[0].isoformat(),
                "asistencias": [{"id_estudiante": student.id_estudiante, "presente": True}],
            }),
            client.post("/api/asistencia-individual/guardar", json={
                "fecha": attendance_dates[1].isoformat(),
                "id_seccion": student.id_seccion,
                "bloque": "completo",
                "asistencias": [{"id_estudiante": student.id_estudiante, "presente": True}],
            }),
        ]
        assert responses[0].get_json()["creados"] == 0
        assert responses[0].get_json()["errores"]
        assert responses[1].get_json()["registros_creados"] == 0
        assert responses[1].get_json()["errores"]
        for attendance_date in attendance_dates:
            assert attendance_ids(student.id_estudiante, attendance_date) == before[attendance_date]
    finally:
        enrollment.estado = "activo"
        student.activo = True
        db.session.commit()


def test_historical_statistics_include_retired_enrollments(client):
    student = Estudiante.query.filter_by(activo=True).first()
    enrollment = Inscripcion.query.filter_by(
        id_estudiante=student.id_estudiante,
        id_anio_escolar=1,
        estado="activo",
    ).one()
    enrollment.estado = "retirado"
    student.activo = False
    db.session.commit()
    try:
        admin_login(client)
        response = client.get("/admin/estadisticas?fecha_inicio=2026-03-02&fecha_fin=2026-03-03")
        assert response.status_code == 200
        statistics = response.get_json()["estadisticas_generales"]
        assert statistics["total_estudiantes"] == 30
        assert statistics["total_asistencias"] == 90
    finally:
        enrollment.estado = "activo"
        student.activo = True
        db.session.commit()
