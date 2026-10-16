from datetime import date

from models import (
    db,
    AsistenciaEstudiante,
    Estudiante,
    Etapa,
    Grado,
    Matricula,
    ObservacionSeccion,
    ProfesorSeccion,
    Seccion,
    SeccionLegacy,
    Usuario,
)

GRADE_NAMES = [
    "Nivel 1 maternal",
    "Nivel 2 maternal",
    "Nivel 3 maternal",
    "1er grado primaria",
    "2do grado primaria",
    "3er grado primaria",
    "4to grado primaria",
    "5to grado primaria",
    "6to grado primaria",
    "1er año secundaria",
    "2do año secundaria",
    "3er año secundaria",
    "4to año secundaria",
    "5to año secundaria",
]


def seed_synthetic_data():
    if any(model.query.count() for model in (Etapa, Usuario, Estudiante)):
        raise RuntimeError("Refusing to seed a non-empty database")

    etapas = [
        Etapa(id_etapa=1, nombre_etapa="Maternal", descripcion="Synthetic maternal", activa=True),
        Etapa(id_etapa=2, nombre_etapa="Primaria", descripcion="Synthetic primaria", activa=True),
        Etapa(id_etapa=3, nombre_etapa="Secundaria", descripcion="Synthetic secundaria", activa=True),
    ]
    db.session.add_all(etapas)

    grados = []
    for index, nombre in enumerate(GRADE_NAMES, start=1):
        id_etapa = 1 if index <= 3 else 2 if index <= 9 else 3
        orden = index if index <= 3 else index - 3 if index <= 9 else index - 9
        grados.append(Grado(
            id_grado=index,
            id_etapa=id_etapa,
            nombre_grado=nombre,
            orden=orden,
            descripcion="Synthetic test grade",
            activo=True,
        ))
    db.session.add_all(grados)

    secciones = []
    for grado_id in range(1, 15):
        if grado_id == 12:
            secciones.extend([
                Seccion(id_seccion=12, id_grado=12, nombre_seccion="A", activa=True),
                Seccion(id_seccion=13, id_grado=12, nombre_seccion="B", activa=True),
            ])
        else:
            secciones.append(Seccion(
                id_seccion=grado_id if grado_id < 12 else grado_id + 1,
                id_grado=grado_id,
                nombre_seccion="Única",
                activa=True,
            ))
    db.session.add_all(secciones)

    legacy_names = [
        "Nivel 1 maternal",
        "Nivel 2 maternal",
        "Nivel 3 maternal",
        "1er grado primaria",
        "2do grado primaria",
        "3er grado primaria",
        "4to grado primaria",
        "5to grado primaria",
        "6to grado primaria",
        "1er año secundaria",
        "2do año secundaria",
        "3er año A secundaria",
        "3er año B secundaria",
        "4to año secundaria",
        "5to año secundaria",
    ]
    db.session.add_all([
        SeccionLegacy(id_seccion=index, nombre_seccion=nombre, id_etapa=1 if index <= 3 else 2 if index <= 9 else 3)
        for index, nombre in enumerate(legacy_names, start=1)
    ])

    from app import bcrypt

    usuarios = [
        Usuario(id_usuario=1, nombre="Admin", apellido="Synthetic", email="admin@dev.test", contraseña=bcrypt.generate_password_hash("dev-only").decode("utf-8"), rol="administrador", activo=True),
        Usuario(id_usuario=2, nombre="Profesora", apellido="Synthetic", email="teacher1@dev.test", contraseña=bcrypt.generate_password_hash("dev-only").decode("utf-8"), rol="profesor", activo=True),
        Usuario(id_usuario=3, nombre="Profesor", apellido="Synthetic", email="teacher2@dev.test", contraseña=bcrypt.generate_password_hash("dev-only").decode("utf-8"), rol="profesor", activo=True),
    ]
    db.session.add_all(usuarios)
    db.session.flush()

    db.session.add_all([
        ProfesorSeccion(id_profesor=2 if section.id_seccion <= 8 else 3, id_seccion=section.id_seccion)
        for section in secciones
    ])

    estudiantes = []
    for section in secciones:
        for offset in range(2):
            number = (section.id_seccion - 1) * 2 + offset + 1
            estudiantes.append(Estudiante(
                cedula=f"TEST{number:04d}",
                nombre=f"Estudiante{number:02d}",
                apellido="Sintético",
                genero="M" if number % 2 else "F",
                id_seccion=section.id_seccion,
                activo=True,
            ))
    db.session.add_all(estudiantes)
    db.session.flush()

    for estudiante in estudiantes:
        db.session.add_all([
            AsistenciaEstudiante(
                id_estudiante=estudiante.id_estudiante,
                fecha=date(2026, 3, 2),
                bloque="completo",
                presente=True,
                observaciones="Synthetic attendance",
                id_usuario=1,
            ),
            AsistenciaEstudiante(
                id_estudiante=estudiante.id_estudiante,
                fecha=date(2026, 3, 3),
                bloque="bloque_1",
                presente=estudiante.id_estudiante % 3 != 0,
                observaciones="Synthetic block 1",
                id_usuario=1,
            ),
            AsistenciaEstudiante(
                id_estudiante=estudiante.id_estudiante,
                fecha=date(2026, 3, 3),
                bloque="bloque_2",
                presente=True,
                observaciones="Synthetic block 2",
                id_usuario=1,
            ),
        ])

    db.session.add_all([
        ObservacionSeccion(
            id_seccion=section.id_seccion,
            fecha=date(2026, 3, 3),
            observaciones="Synthetic section observation",
            id_usuario=1,
        )
        for section in secciones
    ])

    for section in secciones:
        section_students = [e for e in estudiantes if e.id_seccion == section.id_seccion]
        db.session.add(Matricula(
            id_seccion=section.id_seccion,
            num_estudiantes_h=sum(e.genero == "M" for e in section_students),
            num_estudiantes_m=sum(e.genero == "F" for e in section_students),
        ))

    db.session.commit()
    return {
        "etapas": len(etapas),
        "grados": len(grados),
        "secciones": len(secciones),
        "estudiantes": len(estudiantes),
        "asistencias": len(estudiantes) * 3,
        "observaciones": len(secciones),
    }
