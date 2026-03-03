"""
Rutas y endpoints para gestión de estudiantes y asistencia individual
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename

from models import db, Estudiante, Seccion, Grado, Etapa, AsistenciaEstudiante, ObservacionSeccion
from utils.excel_processor import procesar_excel_estudiantes, obtener_estadisticas_carga

# Blueprint para estudiantes
estudiantes_bp = Blueprint('estudiantes', __name__, url_prefix='/api/estudiantes')

# Blueprint para asistencia individual
asistencia_individual_bp = Blueprint('asistencia_individual', __name__, url_prefix='/api/asistencia-individual')

# Decorador para verificar que es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'administrador':
            return jsonify({'error': 'Acceso denegado. Se requiere rol de administrador'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== ENDPOINTS DE ESTUDIANTES ====================

@estudiantes_bp.route('/cargar-excel', methods=['POST'])
@login_required
@admin_required
def cargar_estudiantes_excel():
    """
    Carga estudiantes desde un archivo Excel
    Espera un archivo con columnas: Grado, Sección, Nombre, Apellido, Cédula de identidad, Género
    """
    try:
        # Verificar que se envió un archivo
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        # Validar extensión
        extensiones_permitidas = {'.xlsx', '.xls'}
        ext = os.path.splitext(archivo.filename)[1].lower()
        
        if ext not in extensiones_permitidas:
            return jsonify({'error': f'Extensión no permitida. Use: {", ".join(extensiones_permitidas)}'}), 400
        
        # Guardar archivo temporalmente
        filename = secure_filename(archivo.filename)
        temp_path = os.path.join('data_estudiantes_akademia', filename)
        
        # Crear directorio si no existe
        os.makedirs('data_estudiantes_akademia', exist_ok=True)
        
        archivo.save(temp_path)
        
        # Procesar archivo
        sobrescribir = request.form.get('sobrescribir', 'false').lower() == 'true'
        resultado = procesar_excel_estudiantes(temp_path, sobrescribir=sobrescribir)
        
        # Eliminar archivo temporal (opcional)
        # os.remove(temp_path)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': f'Archivo procesado correctamente',
                'total_filas': resultado['total_filas'],
                'procesados': resultado['procesados'],
                'actualizados': resultado['actualizados'],
                'duplicados': resultado['duplicados'],
                'errores': resultado['errores'],
                'detalle': {
                    'procesados': resultado['detalle_procesados'],
                    'actualizados': resultado['detalle_actualizados'],
                    'duplicados': resultado['detalle_duplicados'],
                    'errores': resultado['detalle_errores']
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Error desconocido')
            }), 400
            
    except Exception as e:
        return jsonify({'error': f'Error al procesar archivo: {str(e)}'}), 500

@estudiantes_bp.route('/seccion/<int:id_seccion>', methods=['GET'])
@login_required
def obtener_estudiantes_seccion(id_seccion):
    """
    Obtiene todos los estudiantes de una sección específica
    """
    try:
        # Verificar que la sección existe
        seccion = Seccion.query.get(id_seccion)
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        # Obtener estudiantes activos de la sección
        estudiantes = Estudiante.query.filter_by(
            id_seccion=id_seccion,
            activo=True
        ).order_by(Estudiante.apellido, Estudiante.nombre).all()
        
        return jsonify({
            'seccion': {
                'id': seccion.id_seccion,
                'nombre': seccion.nombre_completo,
                'total_estudiantes': len(estudiantes)
            },
            'estudiantes': [{
                'id_estudiante': e.id_estudiante,
                'cedula': e.cedula,
                'nombre': e.nombre,
                'apellido': e.apellido,
                'nombre_completo': e.nombre_completo,
                'genero': e.genero,
                'genero_texto': e.genero_texto
            } for e in estudiantes]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener estudiantes: {str(e)}'}), 500

@estudiantes_bp.route('/<int:id_estudiante>', methods=['GET'])
@login_required
def obtener_estudiante(id_estudiante):
    """
    Obtiene información detallada de un estudiante
    """
    try:
        estudiante = Estudiante.query.get(id_estudiante)
        
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        return jsonify({
            'id_estudiante': estudiante.id_estudiante,
            'cedula': estudiante.cedula,
            'nombre': estudiante.nombre,
            'apellido': estudiante.apellido,
            'nombre_completo': estudiante.nombre_completo,
            'genero': estudiante.genero,
            'genero_texto': estudiante.genero_texto,
            'activo': estudiante.activo,
            'seccion': {
                'id': estudiante.seccion.id_seccion,
                'nombre': estudiante.seccion.nombre_completo
            },
            'fecha_registro': estudiante.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener estudiante: {str(e)}'}), 500

@estudiantes_bp.route('/estadisticas', methods=['GET'])
@login_required
def obtener_estadisticas():
    """
    Obtiene estadísticas generales de estudiantes cargados
    """
    try:
        estadisticas = obtener_estadisticas_carga()
        return jsonify(estadisticas), 200
    except Exception as e:
        return jsonify({'error': f'Error al obtener estadísticas: {str(e)}'}), 500

@estudiantes_bp.route('/<int:id_estudiante>', methods=['PUT'])
@login_required
@admin_required
def actualizar_estudiante(id_estudiante):
    """
    Actualiza información de un estudiante
    """
    try:
        estudiante = Estudiante.query.get(id_estudiante)
        
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'nombre' in data:
            estudiante.nombre = data['nombre'].strip()
        if 'apellido' in data:
            estudiante.apellido = data['apellido'].strip()
        if 'cedula' in data:
            estudiante.cedula = data['cedula'].strip()
        if 'genero' in data and data['genero'] in ['M', 'F']:
            estudiante.genero = data['genero']
        if 'id_seccion' in data:
            estudiante.id_seccion = data['id_seccion']
        if 'activo' in data:
            estudiante.activo = bool(data['activo'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estudiante actualizado correctamente',
            'estudiante': {
                'id': estudiante.id_estudiante,
                'nombre_completo': estudiante.nombre_completo,
                'cedula': estudiante.cedula
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar estudiante: {str(e)}'}), 500

@estudiantes_bp.route('/<int:id_estudiante>', methods=['DELETE'])
@login_required
@admin_required
def eliminar_estudiante(id_estudiante):
    """
    Elimina (desactiva) un estudiante
    """
    try:
        estudiante = Estudiante.query.get(id_estudiante)
        
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Desactivar en lugar de eliminar
        estudiante.activo = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Estudiante {estudiante.nombre_completo} desactivado correctamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar estudiante: {str(e)}'}), 500

# ==================== ENDPOINTS DE ASISTENCIA INDIVIDUAL ====================

@asistencia_individual_bp.route('/registrar', methods=['POST'])
@login_required
def registrar_asistencia():
    """
    Registra asistencia individual de estudiantes
    Espera: { fecha: 'YYYY-MM-DD', asistencias: [{id_estudiante: 1, presente: true, observaciones: ''}] }
    """
    try:
        data = request.get_json()
        
        if not data or 'fecha' not in data or 'asistencias' not in data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        fecha_str = data['fecha']
        asistencias_data = data['asistencias']
        
        # Convertir fecha
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        registros_creados = 0
        registros_actualizados = 0
        errores = []
        
        for asistencia_data in asistencias_data:
            try:
                id_estudiante = asistencia_data.get('id_estudiante')
                presente = asistencia_data.get('presente', False)
                observaciones = asistencia_data.get('observaciones', '')
                
                if not id_estudiante:
                    continue
                
                # Verificar que el estudiante existe
                estudiante = Estudiante.query.get(id_estudiante)
                if not estudiante:
                    errores.append(f'Estudiante {id_estudiante} no encontrado')
                    continue
                
                # Buscar asistencia existente
                asistencia_existente = AsistenciaEstudiante.query.filter_by(
                    id_estudiante=id_estudiante,
                    fecha=fecha
                ).first()
                
                if asistencia_existente:
                    # Actualizar
                    asistencia_existente.presente = presente
                    asistencia_existente.observaciones = observaciones
                    asistencia_existente.id_usuario = current_user.id_usuario
                    registros_actualizados += 1
                else:
                    # Crear nuevo registro
                    nueva_asistencia = AsistenciaEstudiante(
                        id_estudiante=id_estudiante,
                        fecha=fecha,
                        presente=presente,
                        observaciones=observaciones,
                        id_usuario=current_user.id_usuario
                    )
                    db.session.add(nueva_asistencia)
                    registros_creados += 1
                    
            except Exception as e:
                errores.append(f'Error en estudiante {id_estudiante}: {str(e)}')
        
        # Guardar cambios
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Asistencia registrada correctamente',
            'creados': registros_creados,
            'actualizados': registros_actualizados,
            'errores': errores
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al registrar asistencia: {str(e)}'}), 500

@asistencia_individual_bp.route('/<fecha>/<int:id_seccion>', methods=['GET'])
@login_required
def obtener_asistencia_seccion(fecha, id_seccion):
    """
    Obtiene la asistencia de una sección en una fecha específica
    """
    try:
        # Validar fecha
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido'}), 400
        
        # Verificar sección
        seccion = Seccion.query.get(id_seccion)
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        # Obtener estudiantes de la sección
        estudiantes = Estudiante.query.filter_by(
            id_seccion=id_seccion,
            activo=True
        ).order_by(Estudiante.apellido, Estudiante.nombre).all()
        
        # Obtener asistencias del día
        asistencias = AsistenciaEstudiante.query.filter_by(fecha=fecha_obj).filter(
            AsistenciaEstudiante.id_estudiante.in_([e.id_estudiante for e in estudiantes])
        ).all()
        
        # Crear diccionario de asistencias
        asistencias_dict = {a.id_estudiante: a for a in asistencias}
        
        # Construir respuesta
        resultado = []
        total_presentes = 0
        
        for estudiante in estudiantes:
            asistencia = asistencias_dict.get(estudiante.id_estudiante)
            presente = asistencia.presente if asistencia else False
            
            if presente:
                total_presentes += 1
            
            resultado.append({
                'id_estudiante': estudiante.id_estudiante,
                'cedula': estudiante.cedula,
                'nombre_completo': estudiante.nombre_completo,
                'genero': estudiante.genero,
                'presente': presente,
                'observaciones': asistencia.observaciones if asistencia else '',
                'registrado': asistencia is not None
            })
        
        return jsonify({
            'fecha': fecha,
            'seccion': {
                'id': seccion.id_seccion,
                'nombre': seccion.nombre_completo
            },
            'total_estudiantes': len(estudiantes),
            'total_presentes': total_presentes,
            'total_ausentes': len(estudiantes) - total_presentes,
            'porcentaje_asistencia': round((total_presentes / len(estudiantes) * 100) if estudiantes else 0, 2),
            'estudiantes': resultado
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener asistencia: {str(e)}'}), 500

@asistencia_individual_bp.route('/verificar', methods=['POST'])
@login_required
def verificar_asistencia_existente():
    """
    Verifica si existe asistencia registrada para una fecha y sección
    Espera: { fecha: 'YYYY-MM-DD', id_seccion: 1 }
    """
    try:
        data = request.get_json()
        
        if not data or 'fecha' not in data or 'id_seccion' not in data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        fecha_str = data['fecha']
        id_seccion = data['id_seccion']
        
        # Convertir fecha
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido'}), 400
        
        # Obtener estudiantes de la sección
        estudiantes = Estudiante.query.filter_by(
            id_seccion=id_seccion,
            activo=True
        ).all()
        
        estudiantes_ids = [e.id_estudiante for e in estudiantes]
        
        # Buscar asistencias existentes
        asistencias = AsistenciaEstudiante.query.filter(
            AsistenciaEstudiante.fecha == fecha,
            AsistenciaEstudiante.id_estudiante.in_(estudiantes_ids)
        ).all()
        
        if not asistencias:
            return jsonify({
                'existe': False,
                'total_estudiantes': len(estudiantes)
            }), 200
        
        # Contar presentes
        total_presentes = sum(1 for a in asistencias if a.presente)
        
        # Construir lista de asistencias
        asistencias_list = [{
            'id_estudiante': a.id_estudiante,
            'presente': a.presente,
            'observaciones': a.observaciones
        } for a in asistencias]
        
        return jsonify({
            'existe': True,
            'total_estudiantes': len(estudiantes),
            'total_presentes': total_presentes,
            'total_ausentes': len(estudiantes) - total_presentes,
            'asistencias': asistencias_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al verificar asistencia: {str(e)}'}), 500

@asistencia_individual_bp.route('/guardar', methods=['POST'])
@login_required
def guardar_asistencia_individual():
    """
    Guarda o actualiza asistencia individual de estudiantes
    Espera: { fecha: 'YYYY-MM-DD', id_seccion: 1, asistencias: [{id_estudiante: 1, presente: true}] }
    """
    try:
        data = request.get_json()
        
        if not data or 'fecha' not in data or 'id_seccion' not in data or 'asistencias' not in data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        fecha_str = data['fecha']
        id_seccion = data['id_seccion']
        asistencias_data = data['asistencias']
        
        # Convertir fecha
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido'}), 400
        
        # Verificar sección
        seccion = Seccion.query.get(id_seccion)
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        registros_creados = 0
        registros_actualizados = 0
        errores = []
        
        for asistencia_data in asistencias_data:
            try:
                id_estudiante = asistencia_data.get('id_estudiante')
                presente = asistencia_data.get('presente', False)
                observaciones = asistencia_data.get('observaciones', '')
                
                if not id_estudiante:
                    continue
                
                # Verificar que el estudiante existe y pertenece a la sección
                estudiante = Estudiante.query.filter_by(
                    id_estudiante=id_estudiante,
                    id_seccion=id_seccion,
                    activo=True
                ).first()
                
                if not estudiante:
                    errores.append(f'Estudiante {id_estudiante} no encontrado en esta sección')
                    continue
                
                # Buscar asistencia existente
                asistencia_existente = AsistenciaEstudiante.query.filter_by(
                    id_estudiante=id_estudiante,
                    fecha=fecha
                ).first()
                
                if asistencia_existente:
                    # Actualizar
                    asistencia_existente.presente = presente
                    asistencia_existente.observaciones = observaciones
                    asistencia_existente.id_usuario = current_user.id_usuario
                    registros_actualizados += 1
                else:
                    # Crear nuevo registro
                    nueva_asistencia = AsistenciaEstudiante(
                        id_estudiante=id_estudiante,
                        fecha=fecha,
                        presente=presente,
                        observaciones=observaciones,
                        id_usuario=current_user.id_usuario
                    )
                    db.session.add(nueva_asistencia)
                    registros_creados += 1
                    
            except Exception as e:
                errores.append(f'Error procesando estudiante {id_estudiante}: {str(e)}')
                continue
        
        # Guardar cambios
        db.session.commit()
        
        mensaje = f'Asistencia guardada: {registros_creados} nuevos, {registros_actualizados} actualizados'
        if errores:
            mensaje += f'. {len(errores)} errores'
        
        return jsonify({
            'success': True,
            'message': mensaje,
            'registros_creados': registros_creados,
            'registros_actualizados': registros_actualizados,
            'errores': errores
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al guardar asistencia: {str(e)}'
        }), 500

@asistencia_individual_bp.route('/estadisticas/<int:id_seccion>', methods=['GET'])
@login_required
def obtener_estadisticas_asistencia(id_seccion):
    """
    Obtiene estadísticas de asistencia de una sección
    Query params: fecha_inicio, fecha_fin
    """
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        # Validar fechas
        if fecha_inicio:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        if fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        # Verificar sección
        seccion = Seccion.query.get(id_seccion)
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        # Obtener estudiantes
        estudiantes = Estudiante.query.filter_by(
            id_seccion=id_seccion,
            activo=True
        ).all()
        
        estudiantes_ids = [e.id_estudiante for e in estudiantes]
        
        # Query base de asistencias
        query = AsistenciaEstudiante.query.filter(
            AsistenciaEstudiante.id_estudiante.in_(estudiantes_ids)
        )
        
        if fecha_inicio:
            query = query.filter(AsistenciaEstudiante.fecha >= fecha_inicio)
        if fecha_fin:
            query = query.filter(AsistenciaEstudiante.fecha <= fecha_fin)
        
        asistencias = query.all()
        
        # Calcular estadísticas
        total_registros = len(asistencias)
        total_presentes = sum(1 for a in asistencias if a.presente)
        total_ausentes = total_registros - total_presentes
        
        return jsonify({
            'seccion': {
                'id': seccion.id_seccion,
                'nombre': seccion.nombre_completo
            },
            'total_estudiantes': len(estudiantes),
            'total_registros': total_registros,
            'total_presentes': total_presentes,
            'total_ausentes': total_ausentes,
            'porcentaje_asistencia': round((total_presentes / total_registros * 100) if total_registros > 0 else 0, 2)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener estadísticas: {str(e)}'}), 500
