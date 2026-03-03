"""
Script para ver la estructura de grados y secciones en la base de datos
"""
from app import app, db
from models import Etapa, Grado, Seccion

with app.app_context():
    print("\n" + "="*60)
    print("GRADOS Y SECCIONES EN LA BASE DE DATOS")
    print("="*60)
    
    for etapa in Etapa.query.all():
        print(f"\n{etapa.nombre_etapa}:")
        for grado in etapa.grados:
            print(f"  - {grado.nombre_grado}")
            for seccion in grado.secciones:
                print(f"      * Sección {seccion.nombre_seccion}")
    
    print("\n" + "="*60)
    print("GRADOS EN EL ARCHIVO EXCEL")
    print("="*60)
    print("1er Grupo, 2do Grupo, 3er Grupo")
    print("1er grado, 2do grado, 3er grado, 4to grado, 5to grado, 6to grado")
    print("1er año, 2do año, 3er año, 4to año, 5to año")
