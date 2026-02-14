"""
Rutas y endpoints para gestión de observaciones de sección
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from models import db, ObservacionSeccion, Seccion

# Blueprint para observaciones
observaciones_bp = Blueprint('observaciones', __name__, url_prefix='/api/observaciones')

@observaciones_bp.route('/verificar', methods=['POST'])
@login_required
def verificar_observacion_existente():
    """
    Verifica si existe observación para una fecha y sección
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
        
        # Buscar observación existente
        observacion = ObservacionSeccion.query.filter_by(
            id_seccion=id_seccion,
            fecha=fecha
        ).first()
        
        if observacion:
            return jsonify({
                'existe': True,
                'observaciones': observacion.observaciones or ''
            }), 200
        else:
            return jsonify({
                'existe': False,
                'observaciones': ''
            }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al verificar observación: {str(e)}'}), 500

@observaciones_bp.route('/guardar', methods=['POST'])
@login_required
def guardar_observacion():
    """
    Guarda o actualiza observación de sección
    Espera: { fecha: 'YYYY-MM-DD', id_seccion: 1, observaciones: 'texto' }
    """
    try:
        data = request.get_json()
        
        if not data or 'fecha' not in data or 'id_seccion' not in data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        fecha_str = data['fecha']
        id_seccion = data['id_seccion']
        observaciones_texto = data.get('observaciones', '').strip()
        
        # Convertir fecha
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido'}), 400
        
        # Verificar sección
        seccion = Seccion.query.get(id_seccion)
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        # Buscar observación existente
        observacion = ObservacionSeccion.query.filter_by(
            id_seccion=id_seccion,
            fecha=fecha
        ).first()
        
        if observacion:
            # Actualizar
            observacion.observaciones = observaciones_texto
            observacion.id_usuario = current_user.id_usuario
            mensaje = 'Observación actualizada correctamente'
        else:
            # Crear nueva
            observacion = ObservacionSeccion(
                id_seccion=id_seccion,
                fecha=fecha,
                observaciones=observaciones_texto,
                id_usuario=current_user.id_usuario
            )
            db.session.add(observacion)
            mensaje = 'Observación guardada correctamente'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': mensaje
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al guardar observación: {str(e)}'
        }), 500

@observaciones_bp.route('/<fecha>/<int:id_seccion>', methods=['GET'])
@login_required
def obtener_observacion(fecha, id_seccion):
    """
    Obtiene la observación de una sección en una fecha específica
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
        
        # Buscar observación
        observacion = ObservacionSeccion.query.filter_by(
            id_seccion=id_seccion,
            fecha=fecha_obj
        ).first()
        
        if observacion:
            return jsonify({
                'existe': True,
                'observaciones': observacion.observaciones or '',
                'fecha_registro': observacion.fecha_registro.isoformat() if observacion.fecha_registro else None
            }), 200
        else:
            return jsonify({
                'existe': False,
                'observaciones': ''
            }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener observación: {str(e)}'}), 500
