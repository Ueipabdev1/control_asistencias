"""
Script para verificar que el endpoint de secciones devuelve datos correctamente
"""

from app import app, db
from models import Seccion, Grado, Etapa, Matricula

def verificar_secciones():
    """Verifica las secciones en la base de datos"""
    with app.app_context():
        print("🔍 Verificando secciones en la base de datos...\n")
        
        # Contar secciones
        total_secciones = Seccion.query.count()
        print(f"📊 Total de secciones: {total_secciones}")
        
        if total_secciones == 0:
            print("⚠️  No hay secciones en la base de datos")
            return
        
        # Mostrar secciones con su estructura
        print("\n📋 Secciones encontradas:")
        print("-" * 80)
        
        secciones = db.session.query(Seccion, Grado, Etapa).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).all()
        
        for s in secciones:
            matricula = Matricula.query.filter_by(id_seccion=s.Seccion.id_seccion).first()
            total_mat = 0
            if matricula:
                total_mat = (matricula.num_estudiantes_h or 0) + (matricula.num_estudiantes_m or 0)
            
            print(f"ID: {s.Seccion.id_seccion}")
            print(f"   Etapa: {s.Etapa.nombre_etapa}")
            print(f"   Grado: {s.Grado.nombre_grado}")
            print(f"   Sección: {s.Seccion.nombre_seccion}")
            print(f"   Matrícula: {total_mat} estudiantes")
            print(f"   Nombre completo: {s.Etapa.nombre_etapa} - {s.Grado.nombre_grado} - Sección {s.Seccion.nombre_seccion}")
            print("-" * 80)
        
        # Simular respuesta del endpoint
        print("\n📤 Simulación de respuesta del endpoint /secciones:")
        print("-" * 80)
        
        resultado = []
        for s in secciones:
            matricula = Matricula.query.filter_by(id_seccion=s.Seccion.id_seccion).first()
            resultado.append({
                'id_seccion': s.Seccion.id_seccion,
                'nombre_seccion': f"{s.Etapa.nombre_etapa} - {s.Grado.nombre_grado} - Sección {s.Seccion.nombre_seccion}",
                'etapa': s.Etapa.nombre_etapa,
                'grado': s.Grado.nombre_grado,
                'seccion': s.Seccion.nombre_seccion,
                'matricula_h': matricula.num_estudiantes_h if matricula else 0,
                'matricula_m': matricula.num_estudiantes_m if matricula else 0,
                'total_matricula': (matricula.num_estudiantes_h + matricula.num_estudiantes_m) if matricula else 0
            })
        
        import json
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        print("\n✅ Verificación completada")

if __name__ == '__main__':
    verificar_secciones()
