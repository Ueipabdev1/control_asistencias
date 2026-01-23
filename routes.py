from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, abort
from datetime import datetime, timedelta
from sqlalchemy import func, and_, extract
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from models import db, Etapa, Usuario, Seccion, ProfesorSeccion, Matricula, Asistencia
from app import bcrypt

# Decorador para verificar roles
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.rol != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def profesor_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.rol not in ['administrador', 'profesor']:
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Blueprint para las rutas principales
main_bp = Blueprint('main', __name__)

# Blueprint para las rutas de administración
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Blueprint para autenticación
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ==================== RUTAS PRINCIPALES ====================

@main_bp.route('/')
@login_required
def index():
    """Página principal - Control de asistencias"""
    return render_template('index.html')

@main_bp.route('/secciones')
@login_required
def obtener_secciones():
    """API para obtener lista de secciones con su matrícula"""
    # Si es administrador, mostrar todas las secciones
    if current_user.is_admin:
        secciones = db.session.query(Seccion, Etapa, Matricula).join(
            Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).outerjoin(
            Matricula, Seccion.id_seccion == Matricula.id_seccion
        ).all()
    else:
        # Si es profesor, solo mostrar sus secciones asignadas
        secciones = db.session.query(Seccion, Etapa, Matricula).join(
            Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).outerjoin(
            Matricula, Seccion.id_seccion == Matricula.id_seccion
        ).join(
            ProfesorSeccion, Seccion.id_seccion == ProfesorSeccion.id_seccion
        ).filter(
            ProfesorSeccion.id_profesor == current_user.id_usuario
        ).all()
    
    return jsonify([{
        'id_seccion': s.Seccion.id_seccion,
        'nombre_seccion': s.Seccion.nombre_seccion,
        'etapa': s.Etapa.nombre_etapa,
        'matricula_h': s.Matricula.num_estudiantes_h if s.Matricula else 0,
        'matricula_m': s.Matricula.num_estudiantes_m if s.Matricula else 0,
        'total_matricula': (s.Matricula.num_estudiantes_h + s.Matricula.num_estudiantes_m) if s.Matricula else 0
    } for s in secciones])

@main_bp.route('/guardar_asistencia', methods=['POST'])
@login_required
def guardar_asistencia():
    """API para guardar asistencias diarias por sección"""
    try:
        data = request.get_json()
        fecha_str = data.get('fecha')
        id_seccion = data.get('id_seccion')
        asistentes_h = data.get('masculinos', 0)
        asistentes_m = data.get('femeninos', 0)
        
        # Convertir fecha string a objeto date
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        # Verificar que la sección existe
        seccion = Seccion.query.get(id_seccion)
        if not seccion:
            return jsonify({'success': False, 'message': 'Sección no encontrada'})
        
        # Si es profesor, verificar que tiene asignada esta sección
        if not current_user.is_admin:
            asignacion = ProfesorSeccion.query.filter_by(
                id_profesor=current_user.id_usuario,
                id_seccion=id_seccion
            ).first()
            
            if not asignacion:
                return jsonify({
                    'success': False, 
                    'message': 'No tienes permisos para registrar asistencia en esta sección'
                }), 403
        
        # Buscar asistencia existente para esta fecha y sección
        asistencia_existente = Asistencia.query.filter_by(
            id_seccion=id_seccion, 
            fecha=fecha
        ).first()
        
        if asistencia_existente:
            # Actualizar asistencia existente
            asistencia_existente.asistentes_h = asistentes_h
            asistencia_existente.asistentes_m = asistentes_m
        else:
            # Crear nueva asistencia
            nueva_asistencia = Asistencia(
                id_seccion=id_seccion,
                fecha=fecha,
                asistentes_h=asistentes_h,
                asistentes_m=asistentes_m
            )
            db.session.add(nueva_asistencia)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asistencia guardada correctamente'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar: {str(e)}'})

@main_bp.route('/obtener_asistencia/<fecha>')
@login_required
def obtener_asistencia(fecha):
    """API para obtener asistencias de una fecha específica"""
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        
        # Query base
        query = db.session.query(Asistencia, Seccion, Etapa).join(
            Seccion, Asistencia.id_seccion == Seccion.id_seccion
        ).join(
            Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).filter(Asistencia.fecha == fecha_obj)
        
        # Si es profesor, filtrar solo sus secciones asignadas
        if not current_user.is_admin:
            query = query.join(
                ProfesorSeccion, Seccion.id_seccion == ProfesorSeccion.id_seccion
            ).filter(
                ProfesorSeccion.id_profesor == current_user.id_usuario
            )
        
        asistencias = query.all()
        
        return jsonify([{
            'id_seccion': a.Asistencia.id_seccion,
            'nombre_seccion': a.Seccion.nombre_seccion,
            'etapa': a.Etapa.nombre_etapa,
            'asistentes_h': a.Asistencia.asistentes_h,
            'asistentes_m': a.Asistencia.asistentes_m,
            'total_asistentes': a.Asistencia.total_asistentes
        } for a in asistencias])
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener asistencias: {str(e)}'})

# ==================== RUTAS DE ADMINISTRACIÓN ====================

@main_bp.route('/admin_dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Dashboard administrativo - Solo administradores"""
    return render_template('admin_dashboard.html')

@main_bp.route('/gestion_matricula')
@login_required
@admin_required
def gestion_matricula():
    """Gestión de matrícula por secciones - Solo administradores"""
    return render_template('gestion_matricula.html')

# ==================== RUTAS PARA GESTIÓN DE PROFESORES ====================

@main_bp.route('/gestion_profesores')
@login_required
@admin_required
def gestion_profesores():
    """Gestión de profesores y asignación de secciones - Solo administradores"""
    return render_template('gestion_profesores.html')

# ==================== API ENDPOINTS PARA USUARIOS ====================

@main_bp.route('/api/usuario', methods=['POST'])
def crear_usuario():
    """API para crear un nuevo usuario (profesor o administrador)"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        campos_requeridos = ['nombre', 'apellido', 'email', 'contraseña', 'rol']
        if not all(k in data for k in campos_requeridos):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Validar rol
        if data['rol'] not in ['profesor', 'administrador']:
            return jsonify({'error': 'Rol inválido'}), 400
        
        # Verificar si el email ya existe
        usuario_existente = Usuario.query.filter_by(email=data['email']).first()
        if usuario_existente:
            return jsonify({'error': 'Ya existe un usuario con este email'}), 400
        
        # Hashear la contraseña
        hashed_password = bcrypt.generate_password_hash(data['contraseña']).decode('utf-8')
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombre=data['nombre'].strip(),
            apellido=data['apellido'].strip(),
            email=data['email'].strip().lower(),
            contraseña=hashed_password,
            rol=data['rol']
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return jsonify({
            'message': f'Usuario {data["rol"]} creado correctamente',
            'id': nuevo_usuario.id_usuario,
            'nombre': nuevo_usuario.nombre,
            'apellido': nuevo_usuario.apellido,
            'email': nuevo_usuario.email,
            'rol': nuevo_usuario.rol
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear usuario: {str(e)}'}), 500

# ==================== API ENDPOINTS PARA PROFESORES ====================

@main_bp.route('/api/profesores', methods=['GET'])
def obtener_profesores():
    """API para obtener todos los profesores"""
    try:
        profesores = Usuario.query.filter_by(rol='profesor').all()
        
        return jsonify([{
            'id': p.id_usuario,
            'nombre': p.nombre,
            'apellido': p.apellido,
            'email': p.email
        } for p in profesores])
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener profesores: {str(e)}'}), 500

@main_bp.route('/api/profesor/<int:profesor_id>', methods=['DELETE'])
def eliminar_profesor(profesor_id):
    """API para eliminar un profesor"""
    try:
        profesor = Usuario.query.get(profesor_id)
        if not profesor:
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        if profesor.rol != 'profesor':
            return jsonify({'error': 'El usuario no es un profesor'}), 400
        
        # Eliminar manualmente todas las asignaciones del profesor
        ProfesorSeccion.query.filter_by(id_profesor=profesor_id).delete()
        
        # Ahora eliminar el profesor
        db.session.delete(profesor)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Profesor {profesor.nombre} {profesor.apellido} eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar profesor: {str(e)}'}), 500

@main_bp.route('/api/secciones/<etapa>', methods=['GET'])
def obtener_secciones_por_etapa(etapa):
    """API para obtener secciones por etapa educativa"""
    try:
        secciones = db.session.query(Seccion).join(Etapa).filter(
            Etapa.nombre_etapa == etapa
        ).all()
        
        return jsonify([{
            'id': s.id_seccion,
            'nombre': s.nombre_seccion
        } for s in secciones])
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener secciones: {str(e)}'}), 500

@main_bp.route('/api/profesor/<int:profesor_id>/secciones', methods=['GET'])
def obtener_secciones_profesor(profesor_id):
    """API para obtener las secciones asignadas a un profesor"""
    try:
        profesor = Usuario.query.get(profesor_id)
        if not profesor:
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        # Obtener secciones asignadas al profesor
        asignaciones = db.session.query(ProfesorSeccion, Seccion, Etapa).join(
            Seccion, ProfesorSeccion.id_seccion == Seccion.id_seccion
        ).join(
            Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).filter(ProfesorSeccion.id_profesor == profesor_id).all()
        
        secciones = [{
            'id': a.Seccion.id_seccion,
            'seccion': a.Seccion.nombre_seccion,
            'etapa': a.Etapa.nombre_etapa
        } for a in asignaciones]
        
        return jsonify({
            'profesor': {
                'id': profesor.id_usuario,
                'nombre': profesor.nombre,
                'apellido': profesor.apellido,
                'email': profesor.email
            },
            'secciones': secciones
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener secciones del profesor: {str(e)}'}), 500

@main_bp.route('/api/profesor/<int:profesor_id>/seccion/<int:seccion_id>', methods=['DELETE'])
def desasignar_seccion_profesor(profesor_id, seccion_id):
    """API para desasignar una sección específica de un profesor"""
    try:
        # Verificar que el profesor existe
        profesor = Usuario.query.get(profesor_id)
        if not profesor or profesor.rol != 'profesor':
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        # Verificar que la sección existe
        seccion = Seccion.query.get(seccion_id)
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        # Buscar y eliminar la asignación
        asignacion = ProfesorSeccion.query.filter_by(
            id_profesor=profesor_id,
            id_seccion=seccion_id
        ).first()
        
        if not asignacion:
            return jsonify({'error': 'La sección no está asignada a este profesor'}), 400
        
        db.session.delete(asignacion)
        db.session.commit()
        
        return jsonify({
            'message': f'Se ha quitado la sección {seccion.nombre_seccion} del profesor {profesor.nombre} {profesor.apellido}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al desasignar la sección: {str(e)}'}), 500

@main_bp.route('/api/profesor/asignar-secciones', methods=['POST'])
def asignar_secciones_profesor():
    """API para asignar secciones a un profesor"""
    try:
        data = request.get_json()
        profesor_id = data.get('profesor_id')
        secciones_ids = data.get('secciones', [])
        
        if not profesor_id or not secciones_ids:
            return jsonify({'error': 'Faltan datos requeridos'}), 400
        
        # Verificar que el profesor existe
        profesor = Usuario.query.get(profesor_id)
        if not profesor or profesor.rol != 'profesor':
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        # Agregar nuevas asignaciones (sin eliminar las existentes)
        asignaciones_creadas = 0
        for seccion_id in secciones_ids:
            # Verificar si ya existe la asignación
            asignacion_existente = ProfesorSeccion.query.filter_by(
                id_profesor=profesor_id,
                id_seccion=seccion_id
            ).first()
            
            if not asignacion_existente:
                nueva_asignacion = ProfesorSeccion(
                    id_profesor=profesor_id,
                    id_seccion=seccion_id
                )
                db.session.add(nueva_asignacion)
                asignaciones_creadas += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Se asignaron {asignaciones_creadas} nuevas secciones al profesor',
            'asignaciones_creadas': asignaciones_creadas
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al asignar secciones: {str(e)}'}), 500

@main_bp.route('/api/profesores/asignaciones', methods=['GET'])
def obtener_todas_asignaciones():
    """API para obtener todas las asignaciones de profesores"""
    try:
        # Obtener todos los profesores con sus asignaciones
        profesores = Usuario.query.filter_by(rol='profesor').all()
        
        resultado = []
        for profesor in profesores:
            # Obtener secciones asignadas
            asignaciones = db.session.query(ProfesorSeccion, Seccion, Etapa).join(
                Seccion, ProfesorSeccion.id_seccion == Seccion.id_seccion
            ).join(
                Etapa, Seccion.id_etapa == Etapa.id_etapa
            ).filter(ProfesorSeccion.id_profesor == profesor.id_usuario).all()
            
            secciones = [{
                'id': a.Seccion.id_seccion,
                'seccion': a.Seccion.nombre_seccion,
                'etapa': a.Etapa.nombre_etapa
            } for a in asignaciones]
            
            resultado.append({
                'id': profesor.id_usuario,
                'nombre': profesor.nombre,
                'apellido': profesor.apellido,
                'email': profesor.email,
                'secciones': secciones
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener asignaciones: {str(e)}'}), 500

@main_bp.route('/api/profesor/<int:profesor_id>/secciones', methods=['DELETE'])
def eliminar_asignaciones_profesor(profesor_id):
    """API para eliminar todas las asignaciones de un profesor"""
    try:
        # Eliminar todas las asignaciones del profesor
        ProfesorSeccion.query.filter_by(id_profesor=profesor_id).delete()
        db.session.commit()
        
        return jsonify({'message': 'Asignaciones eliminadas correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar asignaciones: {str(e)}'}), 500

# ==================== API ENDPOINTS PARA MATRÍCULA ====================

@main_bp.route('/api/matriculas', methods=['GET'])
def obtener_matriculas():
    """API para obtener todas las matrículas"""
    try:
        matriculas = db.session.query(Matricula, Seccion, Etapa).join(
            Seccion, Matricula.id_seccion == Seccion.id_seccion
        ).join(
            Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).all()
        
        return jsonify([{
            'id': m.Matricula.id_matricula,
            'etapa_nombre': m.Etapa.nombre_etapa,
            'seccion_nombre': m.Seccion.nombre_seccion,
            'etapa': m.Etapa.nombre_etapa,
            'seccion': m.Seccion.nombre_seccion,
            'num_estudiantes_h': m.Matricula.num_estudiantes_h,
            'num_estudiantes_m': m.Matricula.num_estudiantes_m
        } for m in matriculas])
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener matrículas: {str(e)}'}), 500

@main_bp.route('/api/matricula', methods=['POST'])
def crear_matricula():
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not all(k in data for k in ['etapa', 'seccion']):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Buscar la sección
        seccion = Seccion.query.join(Etapa).filter(
            Etapa.nombre_etapa == data['etapa'],
            Seccion.nombre_seccion == data['seccion']
        ).first()
        
        if not seccion:
            return jsonify({'error': 'Sección no encontrada'}), 404
        
        # Verificar si ya existe una matrícula para esta sección
        matricula_existente = Matricula.query.filter_by(
            id_seccion=seccion.id_seccion
        ).first()
        
        if matricula_existente:
            return jsonify({'error': 'Ya existe una matrícula para esta sección'}), 400
        
        # Crear nueva matrícula
        nueva_matricula = Matricula(
            id_seccion=seccion.id_seccion,
            num_estudiantes_h=data.get('num_estudiantes_h', 0),
            num_estudiantes_m=data.get('num_estudiantes_m', 0)
        )
        
        db.session.add(nueva_matricula)
        db.session.commit()
        
        return jsonify({'message': 'Matrícula creada correctamente', 'id': nueva_matricula.id_matricula}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/matricula/<int:id>', methods=['GET'])
def obtener_matricula(id):
    """API para obtener una matrícula específica"""
    try:
        matricula = db.session.query(Matricula, Seccion, Etapa).join(
            Seccion, Matricula.id_seccion == Seccion.id_seccion
        ).join(
            Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).filter(Matricula.id_matricula == id).first()
        
        if not matricula:
            return jsonify({'error': 'Matrícula no encontrada'}), 404
        
        return jsonify({
            'id': matricula.Matricula.id_matricula,
            'etapa': matricula.Etapa.nombre_etapa,
            'seccion': matricula.Seccion.nombre_seccion,
            'num_estudiantes_h': matricula.Matricula.num_estudiantes_h,
            'num_estudiantes_m': matricula.Matricula.num_estudiantes_m
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener matrícula: {str(e)}'}), 500

@main_bp.route('/api/matricula/<int:id>', methods=['PUT'])
def actualizar_matricula(id):
    """API para actualizar una matrícula"""
    try:
        matricula = Matricula.query.get(id)
        if not matricula:
            return jsonify({'error': 'Matrícula no encontrada'}), 404
        
        data = request.get_json()
        
        # Actualizar campos
        matricula.num_estudiantes_h = data.get('num_estudiantes_h', 0)
        matricula.num_estudiantes_m = data.get('num_estudiantes_m', 0)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Matrícula actualizada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar matrícula: {str(e)}'}), 500

@main_bp.route('/api/matricula/<int:id>', methods=['DELETE'])
def eliminar_matricula(id):
    """API para eliminar una matrícula"""
    try:
        matricula = Matricula.query.get(id)
        if not matricula:
            return jsonify({'error': 'Matrícula no encontrada'}), 404
        
        db.session.delete(matricula)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Matrícula eliminada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar matrícula: {str(e)}'}), 500

@admin_bp.route('/estadisticas')
def obtener_estadisticas():
    """API para obtener estadísticas detalladas"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        etapa = request.args.get('etapa', '')
        seccion = request.args.get('seccion', '')
        
        # Convertir fechas
        if fecha_inicio:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        else:
            fecha_inicio = datetime.now().date() - timedelta(days=30)
            
        if fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        else:
            fecha_fin = datetime.now().date()
        
        # Filtro base de secciones
        secciones_query = db.session.query(Seccion).join(Etapa)
        if etapa:
            secciones_query = secciones_query.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            secciones_query = secciones_query.filter(Seccion.id_seccion == int(seccion))
        
        # Filtro base de asistencias
        asistencias_query = db.session.query(Asistencia).join(Seccion).join(Etapa).filter(
            and_(Asistencia.fecha >= fecha_inicio, Asistencia.fecha <= fecha_fin)
        )
        if etapa:
            asistencias_query = asistencias_query.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            asistencias_query = asistencias_query.filter(Seccion.id_seccion == int(seccion))
        
        # Estadísticas generales
        total_secciones = secciones_query.count()
        total_asistencias = asistencias_query.count()
        
        # Calcular total de estudiantes matriculados
        total_estudiantes = db.session.query(
            func.sum(Matricula.num_estudiantes_h + Matricula.num_estudiantes_m)
        ).join(Seccion).join(Etapa)
        if etapa:
            total_estudiantes = total_estudiantes.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            total_estudiantes = total_estudiantes.filter(Seccion.id_seccion == int(seccion))
        total_estudiantes = total_estudiantes.scalar() or 0
        
        # Calcular total de asistentes
        total_asistentes = db.session.query(
            func.sum(Asistencia.asistentes_h + Asistencia.asistentes_m)
        ).join(Seccion).join(Etapa).filter(
            and_(Asistencia.fecha >= fecha_inicio, Asistencia.fecha <= fecha_fin)
        )
        if etapa:
            total_asistentes = total_asistentes.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            total_asistentes = total_asistentes.filter(Seccion.id_seccion == int(seccion))
        total_asistentes = total_asistentes.scalar() or 0
        
        # Calcular días analizados
        dias_analizados = (fecha_fin - fecha_inicio).days + 1
        
        # Calcular porcentaje de asistencia: (total asistentes / (matrícula * días)) * 100
        porcentaje_total = round((total_asistentes / (total_estudiantes * dias_analizados) * 100) if total_estudiantes > 0 and dias_analizados > 0 else 0, 1)
        
        # Estadísticas por género
        stats_genero = db.session.query(
            func.sum(Asistencia.asistentes_h).label('total_h'),
            func.sum(Asistencia.asistentes_m).label('total_m'),
            func.sum(Matricula.num_estudiantes_h).label('matricula_h'),
            func.sum(Matricula.num_estudiantes_m).label('matricula_m')
        ).join(Seccion, Asistencia.id_seccion == Seccion.id_seccion
        ).join(Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).join(Matricula, Seccion.id_seccion == Matricula.id_seccion
        ).filter(and_(Asistencia.fecha >= fecha_inicio, Asistencia.fecha <= fecha_fin))
        
        if etapa:
            stats_genero = stats_genero.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            stats_genero = stats_genero.filter(Seccion.id_seccion == int(seccion))
        
        genero_result = stats_genero.first()
        genero_data = {
            'masculino': {
                'total': 0,
                'matricula': 0,
                'porcentaje': 0
            },
            'femenino': {
                'total': 0,
                'matricula': 0,
                'porcentaje': 0
            }
        }
        
        if genero_result and genero_result.total_h is not None:
            genero_data['masculino'] = {
                'total': int(genero_result.total_h or 0),
                'matricula': int(genero_result.matricula_h or 0),
                'porcentaje': round((genero_result.total_h / (genero_result.matricula_h * dias_analizados) * 100) if genero_result.matricula_h and dias_analizados else 0, 1)
            }
            genero_data['femenino'] = {
                'total': int(genero_result.total_m or 0),
                'matricula': int(genero_result.matricula_m or 0),
                'porcentaje': round((genero_result.total_m / (genero_result.matricula_m * dias_analizados) * 100) if genero_result.matricula_m and dias_analizados else 0, 1)
            }
        
        # Estadísticas por sección
        stats_seccion = db.session.query(
            Seccion.nombre_seccion,
            func.sum(Asistencia.asistentes_h + Asistencia.asistentes_m).label('total_asistentes'),
            func.avg(Matricula.num_estudiantes_h + Matricula.num_estudiantes_m).label('matricula_promedio')
        ).join(Asistencia, Seccion.id_seccion == Asistencia.id_seccion
        ).join(Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).join(Matricula, Seccion.id_seccion == Matricula.id_seccion
        ).filter(and_(Asistencia.fecha >= fecha_inicio, Asistencia.fecha <= fecha_fin))
        
        if etapa:
            stats_seccion = stats_seccion.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            stats_seccion = stats_seccion.filter(Seccion.id_seccion == int(seccion))
        
        stats_seccion = stats_seccion.group_by(Seccion.nombre_seccion).all()
        
        seccion_data = {}
        for stat in stats_seccion:
            dias_periodo = (fecha_fin - fecha_inicio).days + 1
            porcentaje = round((stat.total_asistentes / (stat.matricula_promedio * dias_periodo) * 100) if stat.matricula_promedio and dias_periodo else 0, 1)
            seccion_data[stat.nombre_seccion] = {
                'total': stat.total_asistentes or 0,
                'matricula': stat.matricula_promedio or 0,
                'porcentaje': porcentaje
            }
        
        # Estadísticas por etapa
        stats_etapa = db.session.query(
            Etapa.nombre_etapa,
            func.sum(Asistencia.asistentes_h + Asistencia.asistentes_m).label('total_asistentes'),
            func.sum(Matricula.num_estudiantes_h + Matricula.num_estudiantes_m).label('total_matricula')
        ).join(Seccion, Etapa.id_etapa == Seccion.id_etapa
        ).join(Asistencia, Seccion.id_seccion == Asistencia.id_seccion
        ).join(Matricula, Seccion.id_seccion == Matricula.id_seccion
        ).filter(and_(Asistencia.fecha >= fecha_inicio, Asistencia.fecha <= fecha_fin)
        ).group_by(Etapa.nombre_etapa).all()
        
        etapa_data = {}
        for stat in stats_etapa:
            dias_periodo = (fecha_fin - fecha_inicio).days + 1
            porcentaje = round((stat.total_asistentes / (stat.total_matricula * dias_periodo) * 100) if stat.total_matricula and dias_periodo else 0, 1)
            etapa_data[stat.nombre_etapa] = {
                'total': stat.total_asistentes or 0,
                'matricula': stat.total_matricula or 0,
                'porcentaje': porcentaje
            }
        
        # Tendencia temporal por fecha (agrupación diaria)
        tendencia_query = db.session.query(
            Asistencia.fecha,
            func.sum(Asistencia.asistentes_h + Asistencia.asistentes_m).label('total_asistentes'),
            func.sum(Matricula.num_estudiantes_h + Matricula.num_estudiantes_m).label('total_matricula')
        ).join(Seccion, Asistencia.id_seccion == Seccion.id_seccion
        ).join(Etapa, Seccion.id_etapa == Etapa.id_etapa
        ).join(Matricula, Seccion.id_seccion == Matricula.id_seccion
        ).filter(and_(Asistencia.fecha >= fecha_inicio, Asistencia.fecha <= fecha_fin))
        
        if etapa:
            tendencia_query = tendencia_query.filter(Etapa.nombre_etapa == etapa)
        if seccion:
            tendencia_query = tendencia_query.filter(Seccion.id_seccion == int(seccion))
        
        tendencia_query = tendencia_query.group_by(Asistencia.fecha).order_by(Asistencia.fecha)
        
        tendencia_data = []
        for item in tendencia_query.all():
            total_esperado = item.total_matricula or 0
            porcentaje = round((item.total_asistentes / total_esperado * 100) if total_esperado > 0 else 0, 1)
            
            tendencia_data.append({
                'periodo': str(item.fecha),
                'total_asistentes': item.total_asistentes or 0,
                'total_esperado': int(total_esperado),
                'porcentaje': porcentaje
            })
        
        return jsonify({
            'success': True,
            'estadisticas_generales': {
                'total_estudiantes': total_estudiantes,
                'total_asistencias': total_asistencias,
                'total_asistentes': total_asistentes,
                'porcentaje_total': porcentaje_total,
                'dias_analizados': dias_analizados
            },
            'por_genero': genero_data,
            'por_seccion': seccion_data,
            'por_etapa': etapa_data,
            'tendencia_temporal': tendencia_data,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener estadísticas: {str(e)}'})

@main_bp.route('/matricula', methods=['GET', 'POST'])
def gestionar_matricula():
    """Gestión de matrícula por sección"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            id_seccion = data.get('id_seccion')
            num_estudiantes_h = data.get('num_estudiantes_h', 0)
            num_estudiantes_m = data.get('num_estudiantes_m', 0)
            
            # Verificar que la sección existe
            seccion = Seccion.query.get(id_seccion)
            if not seccion:
                return jsonify({'success': False, 'message': 'Sección no encontrada'})
            
            # Buscar matrícula existente o crear nueva
            matricula = Matricula.query.filter_by(id_seccion=id_seccion).first()
            if matricula:
                matricula.num_estudiantes_h = num_estudiantes_h
                matricula.num_estudiantes_m = num_estudiantes_m
            else:
                matricula = Matricula(
                    id_seccion=id_seccion,
                    num_estudiantes_h=num_estudiantes_h,
                    num_estudiantes_m=num_estudiantes_m
                )
                db.session.add(matricula)
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Matrícula actualizada correctamente',
                'matricula': {
                    'id_seccion': matricula.id_seccion,
                    'num_estudiantes_h': matricula.num_estudiantes_h,
                    'num_estudiantes_m': matricula.num_estudiantes_m,
                    'total_estudiantes': matricula.total_estudiantes
                }
            })
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error al actualizar matrícula: {str(e)}'})
    
    # GET - Listar matrícula por secciones
    matriculas = db.session.query(Matricula, Seccion, Etapa).join(
        Seccion, Matricula.id_seccion == Seccion.id_seccion
    ).join(
        Etapa, Seccion.id_etapa == Etapa.id_etapa
    ).all()
    
    return jsonify([{
        'id_matricula': m.Matricula.id_matricula,
        'id_seccion': m.Matricula.id_seccion,
        'nombre_seccion': m.Seccion.nombre_seccion,
        'etapa': m.Etapa.nombre_etapa,
        'num_estudiantes_h': m.Matricula.num_estudiantes_h,
        'num_estudiantes_m': m.Matricula.num_estudiantes_m,
        'total_estudiantes': m.Matricula.total_estudiantes,
        'fecha_actualizacion': m.Matricula.fecha_actualizacion.isoformat() if m.Matricula.fecha_actualizacion else None
    } for m in matriculas])

# ==================== RUTAS DE NAVEGACIÓN ====================

@main_bp.route('/ir_admin')
def ir_admin():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/ir_inicio')
def ir_inicio():
    """Redirección a la página de inicio"""
    return redirect(url_for('main.index'))

# ==================== RUTAS DE AUTENTICACIÓN ====================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Ruta de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        from app import bcrypt
        
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        if not email or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email y contraseña son requeridos'}), 400
            flash('Email y contraseña son requeridos', 'danger')
            return redirect(url_for('auth.login'))
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and bcrypt.check_password_hash(usuario.contraseña, password):
            login_user(usuario, remember=remember)
            next_page = request.args.get('next')
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': 'Inicio de sesión exitoso',
                    'redirect': next_page or url_for('main.index'),
                    'user': {
                        'nombre': usuario.nombre,
                        'apellido': usuario.apellido,
                        'rol': usuario.rol
                    }
                })
            
            flash(f'¡Bienvenido {usuario.nombre}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email o contraseña incorrectos'}), 401
            flash('Email o contraseña incorrectos', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Ruta de cierre de sesión"""
    logout_user()
    flash('Has cerrado sesión exitosamente', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Ruta de registro de nuevos usuarios"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        from app import bcrypt
        
        data = request.get_json() if request.is_json else request.form
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        rol = data.get('rol', 'profesor')
        
        # Validaciones
        if not all([nombre, apellido, email, password, confirm_password]):
            if request.is_json:
                return jsonify({'success': False, 'message': 'Todos los campos son requeridos'}), 400
            flash('Todos los campos son requeridos', 'danger')
            return redirect(url_for('auth.registro'))
        
        if password != confirm_password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Las contraseñas no coinciden'}), 400
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('auth.registro'))
        
        if len(password) < 6:
            if request.is_json:
                return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'}), 400
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('auth.registro'))
        
        if rol not in ['profesor', 'administrador']:
            rol = 'profesor'
        
        # Verificar si el email ya existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Ya existe un usuario con este email'}), 400
            flash('Ya existe un usuario con este email', 'danger')
            return redirect(url_for('auth.registro'))
        
        try:
            # Encriptar contraseña
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # Crear nuevo usuario
            nuevo_usuario = Usuario(
                nombre=nombre,
                apellido=apellido,
                email=email,
                contraseña=hashed_password,
                rol=rol
            )
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': 'Usuario registrado exitosamente',
                    'redirect': url_for('auth.login')
                }), 201
            
            flash('¡Registro exitoso! Ahora puedes iniciar sesión', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Error al registrar usuario: {str(e)}'}), 500
            flash(f'Error al registrar usuario: {str(e)}', 'danger')
            return redirect(url_for('auth.registro'))
    
    return render_template('registro.html')
