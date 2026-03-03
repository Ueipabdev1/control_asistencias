"""
Script para probar los endpoints de matrículas y estudiantes
"""
from app import app
from models import db, Matricula, Seccion, Grado, Etapa, Estudiante

with app.app_context():
    print("\n" + "="*60)
    print("VERIFICACIÓN DE DATOS")
    print("="*60)
    
    # Contar estudiantes
    total_estudiantes = Estudiante.query.filter_by(activo=True).count()
    print(f"\n✅ Total estudiantes activos: {total_estudiantes}")
    
    # Contar secciones
    total_secciones = Seccion.query.count()
    print(f"✅ Total secciones: {total_secciones}")
    
    # Contar matrículas
    total_matriculas = Matricula.query.count()
    print(f"✅ Total matrículas (legacy): {total_matriculas}")
    
    # Mostrar algunas secciones con estudiantes
    print("\n" + "="*60)
    print("SECCIONES CON ESTUDIANTES")
    print("="*60)
    
    secciones = Seccion.query.join(Grado).join(Etapa).limit(10).all()
    
    for seccion in secciones:
        estudiantes_count = Estudiante.query.filter_by(
            id_seccion=seccion.id_seccion,
            activo=True
        ).count()
        
        print(f"\n{seccion.nombre_completo}")
        print(f"  Estudiantes: {estudiantes_count}")
    
    # Verificar endpoint de secciones
    print("\n" + "="*60)
    print("SIMULACIÓN DE ENDPOINT /secciones")
    print("="*60)
    
    secciones_query = db.session.query(Seccion, Grado, Etapa, Matricula).join(
        Grado, Seccion.id_grado == Grado.id_grado
    ).join(
        Etapa, Grado.id_etapa == Etapa.id_etapa
    ).outerjoin(
        Matricula, Seccion.id_seccion == Matricula.id_seccion
    ).limit(5).all()
    
    for s in secciones_query:
        nombre_completo = f"{s.Etapa.nombre_etapa} - {s.Grado.nombre_grado} - Sección {s.Seccion.nombre_seccion}"
        print(f"\n{nombre_completo}")
        print(f"  ID: {s.Seccion.id_seccion}")
        print(f"  Matrícula: {s.Matricula.num_estudiantes_h if s.Matricula else 0}H + {s.Matricula.num_estudiantes_m if s.Matricula else 0}M")
