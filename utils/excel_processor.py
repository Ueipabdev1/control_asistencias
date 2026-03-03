"""
Utilidad para procesar archivos Excel de estudiantes
Estructura esperada del Excel:
- Grado: Nombre del grado (ej: "1er grado", "3er año")
- Sección: Letra de la sección (ej: "A", "B", "Única")
- Nombre: Nombre del estudiante
- Apellido: Apellido del estudiante
- Cédula de identidad: Cédula del estudiante
- Género: M o F
"""

import pandas as pd
from models import db, Estudiante, Seccion, Grado, Etapa
from sqlalchemy import or_

def limpiar_texto(texto):
    """Limpia y normaliza texto"""
    if pd.isna(texto):
        return ""
    return str(texto).strip()

def normalizar_genero(genero):
    """Normaliza el género a M o F"""
    genero = limpiar_texto(genero).upper()
    
    # Mapeo de posibles valores
    if genero in ['M', 'MASCULINO', 'HOMBRE', 'H', 'MALE', 'MASC']:
        return 'M'
    elif genero in ['F', 'FEMENINO', 'MUJER', 'FEMALE', 'FEM']:
        return 'F'
    else:
        return None

def normalizar_seccion(seccion):
    """Normaliza el nombre de la sección"""
    seccion = limpiar_texto(seccion).upper()
    
    # Mapeo de posibles valores
    if seccion in ['U', 'UNICA', 'ÚNICA']:
        return 'Única'
    
    # Si es una letra simple (A, B, C), retornarla en mayúscula
    if len(seccion) == 1 and seccion.isalpha():
        return seccion.upper()
    
    return seccion

def normalizar_nombre_grado(nombre_grado):
    """
    Normaliza nombres de grados para manejar variaciones
    Ejemplos: 1er Grupo -> Nivel 1, 2do Grupo -> Nivel 2, 1er. Grado -> 1er grado
    """
    nombre_grado = limpiar_texto(nombre_grado).lower()
    
    # Eliminar puntos
    nombre_grado = nombre_grado.replace('.', '')
    
    # Mapeo de variaciones comunes
    mapeo = {
        '1er grupo': 'nivel 1',
        '2do grupo': 'nivel 2',
        '3er grupo': 'nivel 3',
        'primer grupo': 'nivel 1',
        'segundo grupo': 'nivel 2',
        'tercer grupo': 'nivel 3',
    }
    
    return mapeo.get(nombre_grado, nombre_grado)

def buscar_seccion(nombre_grado, nombre_seccion):
    """
    Busca una sección basándose en el nombre del grado y la sección
    Retorna el objeto Seccion o None si no se encuentra
    """
    # Limpiar y normalizar inputs
    nombre_grado = normalizar_nombre_grado(nombre_grado)
    nombre_seccion = limpiar_texto(nombre_seccion).lower()
    
    # Buscar grado que contenga el nombre
    grado = db.session.query(Grado).filter(
        Grado.nombre_grado.ilike(f'%{nombre_grado}%')
    ).first()
    
    if not grado:
        return None
    
    # Buscar sección dentro del grado
    seccion = db.session.query(Seccion).filter(
        Seccion.id_grado == grado.id_grado,
        Seccion.nombre_seccion.ilike(f'%{nombre_seccion}%')
    ).first()
    
    return seccion

def detectar_fila_encabezado(file_path):
    """
    Detecta en qué fila están los encabezados del Excel
    Busca la fila que contiene 'Grado' o 'Nombre'
    """
    df_temp = pd.read_excel(file_path, header=None, nrows=10)
    
    for idx, row in df_temp.iterrows():
        row_str = ' '.join([str(val).lower() for val in row if pd.notna(val)])
        if 'grado' in row_str and 'nombre' in row_str:
            return idx
    
    return 0

def procesar_excel_estudiantes(file_path, sobrescribir=False):
    """
    Procesa archivo Excel con estudiantes y los carga en la base de datos
    
    Args:
        file_path: Ruta al archivo Excel
        sobrescribir: Si True, actualiza estudiantes existentes. Si False, los omite.
    
    Returns:
        dict con resultados del procesamiento
    """
    try:
        # Detectar fila de encabezado
        header_row = detectar_fila_encabezado(file_path)
        
        # Leer archivo Excel con el encabezado correcto
        df = pd.read_excel(file_path, header=header_row)
        
        # Limpiar nombres de columnas (quitar espacios extra)
        df.columns = df.columns.str.strip()
        
        # Validar columnas requeridas
        columnas_requeridas = ['Grado', 'Sección', 'Nombre', 'Apellido', 'Cédula de identidad', 'Género']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            return {
                'success': False,
                'error': f'Faltan columnas requeridas: {", ".join(columnas_faltantes)}',
                'columnas_encontradas': list(df.columns)
            }
        
        # Eliminar filas vacías
        df = df.dropna(how='all')
        df = df[df['Nombre'].notna()]
        
        # Resultados
        estudiantes_procesados = []
        estudiantes_actualizados = []
        estudiantes_duplicados = []
        errores = []
        
        # Procesar cada fila
        for index, row in df.iterrows():
            fila_num = index + 2  # +2 porque Excel empieza en 1 y tiene header
            
            try:
                # Extraer y limpiar datos
                cedula = limpiar_texto(row['Cédula de identidad'])
                # Limpiar cédula (quitar V-, E-, guiones, espacios)
                cedula = cedula.replace('V-', '').replace('E-', '').replace('-', '').replace(' ', '')
                if cedula and not cedula.startswith(('V', 'E')):
                    cedula = 'V' + cedula
                
                nombre = limpiar_texto(row['Nombre'])
                apellido = limpiar_texto(row['Apellido'])
                genero = normalizar_genero(row['Género'])
                nombre_grado = limpiar_texto(row['Grado'])
                nombre_seccion = normalizar_seccion(row['Sección'])
                
                # Validaciones básicas
                if not cedula:
                    errores.append(f"Fila {fila_num}: Cédula vacía")
                    continue
                
                if not nombre or not apellido:
                    errores.append(f"Fila {fila_num}: Nombre o apellido vacío para cédula {cedula}")
                    continue
                
                if not genero:
                    errores.append(f"Fila {fila_num}: Género inválido '{row['Género']}' para {nombre} {apellido}")
                    continue
                
                # Buscar sección correspondiente
                seccion = buscar_seccion(nombre_grado, nombre_seccion)
                
                if not seccion:
                    errores.append(f"Fila {fila_num}: No se encontró sección para '{nombre_grado} - {nombre_seccion}'")
                    continue
                
                # Verificar si el estudiante ya existe
                estudiante_existente = Estudiante.query.filter_by(cedula=cedula).first()
                
                if estudiante_existente:
                    if sobrescribir:
                        # Actualizar estudiante existente
                        estudiante_existente.nombre = nombre
                        estudiante_existente.apellido = apellido
                        estudiante_existente.genero = genero
                        estudiante_existente.id_seccion = seccion.id_seccion
                        estudiante_existente.activo = True
                        
                        estudiantes_actualizados.append({
                            'cedula': cedula,
                            'nombre': f"{nombre} {apellido}",
                            'seccion': seccion.nombre_completo,
                            'accion': 'actualizado'
                        })
                    else:
                        # Omitir duplicado
                        estudiantes_duplicados.append({
                            'cedula': cedula,
                            'nombre': f"{nombre} {apellido}",
                            'seccion_actual': estudiante_existente.seccion.nombre_completo,
                            'seccion_nueva': seccion.nombre_completo
                        })
                    continue
                
                # Crear nuevo estudiante
                nuevo_estudiante = Estudiante(
                    cedula=cedula,
                    nombre=nombre,
                    apellido=apellido,
                    genero=genero,
                    id_seccion=seccion.id_seccion,
                    activo=True
                )
                
                db.session.add(nuevo_estudiante)
                
                estudiantes_procesados.append({
                    'cedula': cedula,
                    'nombre': f"{nombre} {apellido}",
                    'seccion': seccion.nombre_completo,
                    'genero': 'Masculino' if genero == 'M' else 'Femenino'
                })
                
            except Exception as e:
                errores.append(f"Fila {fila_num}: Error al procesar - {str(e)}")
                continue
        
        # Guardar cambios en la base de datos
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'Error al guardar en base de datos: {str(e)}'
            }
        
        # Retornar resultados
        return {
            'success': True,
            'total_filas': len(df),
            'procesados': len(estudiantes_procesados),
            'actualizados': len(estudiantes_actualizados),
            'duplicados': len(estudiantes_duplicados),
            'errores': len(errores),
            'detalle_procesados': estudiantes_procesados,
            'detalle_actualizados': estudiantes_actualizados,
            'detalle_duplicados': estudiantes_duplicados,
            'detalle_errores': errores
        }
        
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'Archivo no encontrado'
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': f'Error al procesar archivo: {str(e)}'
        }

def obtener_estadisticas_carga():
    """
    Retorna estadísticas generales de estudiantes cargados
    """
    try:
        total_estudiantes = Estudiante.query.filter_by(activo=True).count()
        estudiantes_por_genero = db.session.query(
            Estudiante.genero,
            db.func.count(Estudiante.id_estudiante)
        ).filter_by(activo=True).group_by(Estudiante.genero).all()
        
        estudiantes_por_seccion = db.session.query(
            Seccion.id_seccion,
            Seccion.nombre_seccion,
            Grado.nombre_grado,
            Etapa.nombre_etapa,
            db.func.count(Estudiante.id_estudiante)
        ).join(
            Estudiante, Seccion.id_seccion == Estudiante.id_seccion
        ).join(
            Grado, Seccion.id_grado == Grado.id_grado
        ).join(
            Etapa, Grado.id_etapa == Etapa.id_etapa
        ).filter(
            Estudiante.activo == True
        ).group_by(
            Seccion.id_seccion, Seccion.nombre_seccion, Grado.nombre_grado, Etapa.nombre_etapa
        ).all()
        
        return {
            'total_estudiantes': total_estudiantes,
            'por_genero': {g: c for g, c in estudiantes_por_genero},
            'por_seccion': [{
                'id_seccion': s[0],
                'seccion': f"{s[3]} - {s[2]} - Sección {s[1]}",
                'total': s[4]
            } for s in estudiantes_por_seccion]
        }
    except Exception as e:
        return {
            'error': f'Error al obtener estadísticas: {str(e)}'
        }
