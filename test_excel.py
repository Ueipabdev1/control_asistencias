"""
Script de prueba para cargar archivo Excel
"""
from app import app
from utils.excel_processor import procesar_excel_estudiantes

def test_carga():
    with app.app_context():
        resultado = procesar_excel_estudiantes(
            'data_estudiantes_akademia/lista_de_estudiantes20260203-1-1bb8grm.xls',
            sobrescribir=False
        )
        
        print("\n" + "="*60)
        print("RESULTADO DE LA CARGA")
        print("="*60)
        print(f"Success: {resultado.get('success')}")
        
        if resultado.get('success'):
            print(f"\nTotal filas: {resultado.get('total_filas')}")
            print(f"Procesados: {resultado.get('procesados')}")
            print(f"Actualizados: {resultado.get('actualizados')}")
            print(f"Duplicados: {resultado.get('duplicados')}")
            print(f"Errores: {resultado.get('errores')}")
            
            if resultado.get('detalle_errores'):
                print(f"\nPrimeros 10 errores:")
                for error in resultado.get('detalle_errores')[:10]:
                    print(f"  - {error}")
            
            if resultado.get('detalle_procesados'):
                print(f"\nPrimeros 5 estudiantes procesados:")
                for est in resultado.get('detalle_procesados')[:5]:
                    print(f"  - {est['nombre']} ({est['cedula']}) - {est['seccion']}")
        else:
            print(f"\nError: {resultado.get('error')}")
            if resultado.get('columnas_encontradas'):
                print(f"\nColumnas encontradas:")
                for col in resultado.get('columnas_encontradas'):
                    print(f"  - {col}")

if __name__ == '__main__':
    test_carga()
