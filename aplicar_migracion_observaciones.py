"""
Script para aplicar la migración de observaciones de sección
Ejecutar: python aplicar_migracion_observaciones.py
"""

from app import app, db
from models import ObservacionSeccion

def aplicar_migracion():
    """Aplica la migración para crear la tabla de observaciones"""
    try:
        with app.app_context():
            print("🔄 Aplicando migración de observaciones de sección...")
            
            # Crear la tabla si no existe
            db.create_all()
            
            print("✅ Migración aplicada correctamente")
            print("📋 Tabla 'observacion_seccion' creada/verificada")
            
            # Verificar que la tabla existe
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tablas = inspector.get_table_names()
            
            if 'observacion_seccion' in tablas:
                print("✅ Tabla 'observacion_seccion' confirmada en la base de datos")
                
                # Mostrar columnas
                columnas = inspector.get_columns('observacion_seccion')
                print("\n📊 Columnas de la tabla:")
                for col in columnas:
                    print(f"   - {col['name']}: {col['type']}")
            else:
                print("⚠️  Advertencia: No se pudo confirmar la tabla en la base de datos")
                
    except Exception as e:
        print(f"❌ Error al aplicar migración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    aplicar_migracion()
