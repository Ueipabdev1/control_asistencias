"""
Rutas y endpoints para gestión del calendario escolar
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime, date
from functools import wraps

from models import db, CalendarioEscolar, Usuario

# Blueprint para calendario escolar
calendario_bp = Blueprint('calendario', __name__, url_prefix='/calendario')

# Decorador para verificar que es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from flask import redirect, url_for, flash
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.rol != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@calendario_bp.route('/')
@login_required
@admin_required
def index():
    """Página principal del calendario escolar"""
    return render_template('calendario_escolar.html')

@calendario_bp.route('/api/dias-no-laborables', methods=['GET'])
@login_required
def obtener_dias_no_laborables():
    """API para obtener todos los días no laborables"""
    try:
        # Obtener parámetros opcionales de filtro
        año = request.args.get('año', type=int)
        mes = request.args.get('mes', type=int)
        
        query = CalendarioEscolar.query.filter_by(activo=True)
        
        if año:
            query = query.filter(db.extract('year', CalendarioEscolar.fecha) == año)
        if mes:
            query = query.filter(db.extract('month', CalendarioEscolar.fecha) == mes)
        
        dias = query.order_by(CalendarioEscolar.fecha).all()
        
        return jsonify({
            'success': True,
            'dias': [{
                'id': d.id_calendario,
                'fecha': d.fecha.isoformat(),
                'tipo': d.tipo,
                'descripcion': d.descripcion,
                'activo': d.activo
            } for d in dias]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@calendario_bp.route('/api/dia-no-laborable', methods=['POST'])
@login_required
@admin_required
def crear_dia_no_laborable():
    """API para crear un día no laborable"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not all(k in data for k in ['fecha', 'tipo', 'descripcion']):
            return jsonify({'success': False, 'error': 'Faltan campos requeridos'}), 400
        
        # Convertir fecha
        fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        
        # Verificar si ya existe
        existente = CalendarioEscolar.query.filter_by(fecha=fecha).first()
        if existente:
            return jsonify({'success': False, 'error': 'Ya existe un registro para esta fecha'}), 400
        
        # Crear nuevo registro
        nuevo_dia = CalendarioEscolar(
            fecha=fecha,
            tipo=data['tipo'],
            descripcion=data['descripcion'],
            activo=True
        )
        
        db.session.add(nuevo_dia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Día no laborable creado correctamente',
            'dia': {
                'id': nuevo_dia.id_calendario,
                'fecha': nuevo_dia.fecha.isoformat(),
                'tipo': nuevo_dia.tipo,
                'descripcion': nuevo_dia.descripcion
            }
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@calendario_bp.route('/api/dia-no-laborable/<int:id>', methods=['PUT'])
@login_required
@admin_required
def actualizar_dia_no_laborable(id):
    """API para actualizar un día no laborable"""
    try:
        dia = CalendarioEscolar.query.get(id)
        if not dia:
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
        
        data = request.get_json()
        
        # Actualizar campos
        if 'tipo' in data:
            dia.tipo = data['tipo']
        if 'descripcion' in data:
            dia.descripcion = data['descripcion']
        if 'activo' in data:
            dia.activo = data['activo']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Día no laborable actualizado correctamente',
            'dia': {
                'id': dia.id_calendario,
                'fecha': dia.fecha.isoformat(),
                'tipo': dia.tipo,
                'descripcion': dia.descripcion,
                'activo': dia.activo
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@calendario_bp.route('/api/dia-no-laborable/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def eliminar_dia_no_laborable(id):
    """API para eliminar un día no laborable"""
    try:
        dia = CalendarioEscolar.query.get(id)
        if not dia:
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
        
        db.session.delete(dia)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Día no laborable eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@calendario_bp.route('/api/verificar-dia/<fecha>', methods=['GET'])
@login_required
def verificar_dia_laborable(fecha):
    """API para verificar si un día es laborable"""
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        
        dia_no_laborable = CalendarioEscolar.query.filter_by(
            fecha=fecha_obj,
            activo=True
        ).first()
        
        return jsonify({
            'success': True,
            'es_laborable': dia_no_laborable is None,
            'info': {
                'tipo': dia_no_laborable.tipo,
                'descripcion': dia_no_laborable.descripcion
            } if dia_no_laborable else None
        })
        
    except ValueError:
        return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
