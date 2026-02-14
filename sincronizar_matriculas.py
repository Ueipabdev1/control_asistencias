"""
Script para sincronizar las matrículas legacy con los estudiantes individuales
"""
from app import app, db
from models import Matricula, Estudiante, Seccion

with app.app_context():
    print("\n" + "="*60)
    print("SINCRONIZACIÓN DE MATRÍCULAS")
    print("="*60)
    
    # Obtener todas las secciones
    secciones = Seccion.query.all()
    
    creadas = 0
    actualizadas = 0
    
    for seccion in secciones:
        # Contar estudiantes por género
        masculinos = Estudiante.query.filter_by(
            id_seccion=seccion.id_seccion,
            activo=True,
            genero='M'
        ).count()
        
        femeninos = Estudiante.query.filter_by(
            id_seccion=seccion.id_seccion,
            activo=True,
            genero='F'
        ).count()
        
        # Buscar matrícula existente
        matricula = Matricula.query.filter_by(id_seccion=seccion.id_seccion).first()
        
        if matricula:
            # Actualizar
            matricula.num_estudiantes_h = masculinos
            matricula.num_estudiantes_m = femeninos
            actualizadas += 1
            print(f"✅ Actualizada: {seccion.nombre_completo} ({masculinos}H + {femeninos}M)")
        else:
            # Crear nueva
            nueva_matricula = Matricula(
                id_seccion=seccion.id_seccion,
                num_estudiantes_h=masculinos,
                num_estudiantes_m=femeninos
            )
            db.session.add(nueva_matricula)
            creadas += 1
            print(f"➕ Creada: {seccion.nombre_completo} ({masculinos}H + {femeninos}M)")
    
    # Guardar cambios
    db.session.commit()
    
    print("\n" + "="*60)
    print(f"✅ Matrículas creadas: {creadas}")
    print(f"🔄 Matrículas actualizadas: {actualizadas}")
    print(f"📊 Total: {creadas + actualizadas}")
    print("="*60)
