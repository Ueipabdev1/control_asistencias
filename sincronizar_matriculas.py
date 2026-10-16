from app import app, db
from models import Estudiante, Inscripcion, Matricula, Seccion, SeccionLegacy
from utils.academic_year import current_academic_year

with app.app_context():
    print("\n" + "=" * 60)
    print("SINCRONIZACIÓN DE MATRÍCULAS LEGACY")
    print("=" * 60)

    year = current_academic_year()
    secciones = Seccion.query.filter_by(
        id_anio_escolar=year.id_anio_escolar,
        activa=True,
    ).all()
    creadas = 0
    actualizadas = 0
    omitidas = 0

    for seccion in secciones:
        if not SeccionLegacy.query.get(seccion.id_seccion):
            omitidas += 1
            continue

        masculinos = Inscripcion.query.join(
            Estudiante, Inscripcion.id_estudiante == Estudiante.id_estudiante
        ).filter(
            Inscripcion.id_seccion == seccion.id_seccion,
            Inscripcion.id_anio_escolar == year.id_anio_escolar,
            Inscripcion.estado == 'activo',
            Estudiante.genero == 'M',
        ).count()
        femeninos = Inscripcion.query.join(
            Estudiante, Inscripcion.id_estudiante == Estudiante.id_estudiante
        ).filter(
            Inscripcion.id_seccion == seccion.id_seccion,
            Inscripcion.id_anio_escolar == year.id_anio_escolar,
            Inscripcion.estado == 'activo',
            Estudiante.genero == 'F',
        ).count()

        matricula = Matricula.query.filter_by(id_seccion=seccion.id_seccion).first()
        if matricula:
            matricula.num_estudiantes_h = masculinos
            matricula.num_estudiantes_m = femeninos
            actualizadas += 1
            print(f"Actualizada: {seccion.nombre_completo} ({masculinos}H + {femeninos}M)")
        else:
            db.session.add(Matricula(
                id_seccion=seccion.id_seccion,
                num_estudiantes_h=masculinos,
                num_estudiantes_m=femeninos,
            ))
            creadas += 1
            print(f"Creada: {seccion.nombre_completo} ({masculinos}H + {femeninos}M)")

    db.session.commit()
    print("\n" + "=" * 60)
    print(f"Matrículas creadas: {creadas}")
    print(f"Matrículas actualizadas: {actualizadas}")
    print(f"Secciones sin contraparte legacy omitidas: {omitidas}")
    print("=" * 60)
