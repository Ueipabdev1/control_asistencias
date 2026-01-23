from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Modelo para etapas educativas
class Etapa(db.Model):
    __tablename__ = 'etapa'
    
    id_etapa = db.Column(db.Integer, primary_key=True)
    nombre_etapa = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255))
    
    # Relación con secciones
    secciones = db.relationship('Seccion', backref='etapa', lazy=True)
    
    def __repr__(self):
        return f'<Etapa {self.nombre_etapa}>'

# Modelo para usuarios (administradores y profesores)
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.Enum('administrador', 'profesor'), nullable=False)
    fecha_creacion = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Relación con secciones (solo para profesores)
    secciones = db.relationship('ProfesorSeccion', backref='profesor', lazy=True)
    
    # Métodos requeridos por Flask-Login
    def get_id(self):
        return str(self.id_usuario)
    
    @property
    def is_admin(self):
        return self.rol == 'administrador'
    
    @property
    def is_profesor(self):
        return self.rol == 'profesor'
    
    def __repr__(self):
        return f'<Usuario {self.nombre} {self.apellido} - {self.rol}>'

# Modelo para secciones (cursos/grupos)
class Seccion(db.Model):
    __tablename__ = 'secciones'
    
    id_seccion = db.Column(db.Integer, primary_key=True)
    nombre_seccion = db.Column(db.String(50), nullable=False)
    id_etapa = db.Column(db.Integer, db.ForeignKey('etapa.id_etapa'), nullable=False)
    
    # Relaciones
    profesores = db.relationship('ProfesorSeccion', backref='seccion', lazy=True)
    matricula = db.relationship('Matricula', backref='seccion', uselist=False)
    asistencias = db.relationship('Asistencia', backref='seccion', lazy=True)
    
    def __repr__(self):
        return f'<Seccion {self.nombre_seccion}>'

# Modelo para relación profesor-secciones (muchos a muchos)
class ProfesorSeccion(db.Model):
    __tablename__ = 'profesor_secciones'
    
    id_profesor_seccion = db.Column(db.Integer, primary_key=True)
    id_profesor = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario', ondelete='CASCADE'), nullable=False)
    id_seccion = db.Column(db.Integer, db.ForeignKey('secciones.id_seccion', ondelete='CASCADE'), nullable=False)
    
    # Constraint único para evitar duplicados
    __table_args__ = (db.UniqueConstraint('id_profesor', 'id_seccion', name='unique_profesor_seccion'),)
    
    def __repr__(self):
        return f'<ProfesorSeccion {self.id_profesor}-{self.id_seccion}>'

# Modelo para matrícula (conteo por género por sección)
class Matricula(db.Model):
    __tablename__ = 'matricula'
    
    id_matricula = db.Column(db.Integer, primary_key=True)
    id_seccion = db.Column(db.Integer, db.ForeignKey('secciones.id_seccion', ondelete='CASCADE'), nullable=False, unique=True)
    num_estudiantes_h = db.Column(db.Integer, default=0, comment='Número de estudiantes hombres')
    num_estudiantes_m = db.Column(db.Integer, default=0, comment='Número de estudiantes mujeres')
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def total_estudiantes(self):
        return (self.num_estudiantes_h or 0) + (self.num_estudiantes_m or 0)
    
    def __repr__(self):
        return f'<Matricula Sección:{self.id_seccion} H:{self.num_estudiantes_h} M:{self.num_estudiantes_m}>'

# Modelo para asistencia (registra por género por sección)
class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    
    id_asistencia = db.Column(db.Integer, primary_key=True)
    id_seccion = db.Column(db.Integer, db.ForeignKey('secciones.id_seccion', ondelete='CASCADE'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    asistentes_h = db.Column(db.Integer, default=0, comment='Estudiantes hombres presentes')
    asistentes_m = db.Column(db.Integer, default=0, comment='Estudiantes mujeres presentes')
    
    # Constraint único para evitar duplicados por sección y fecha
    __table_args__ = (db.UniqueConstraint('id_seccion', 'fecha', name='unique_asistencia'),)
    
    @property
    def total_asistentes(self):
        return (self.asistentes_h or 0) + (self.asistentes_m or 0)
    
    def calcular_porcentaje_asistencia(self):
        """Calcula el porcentaje de asistencia basado en la matrícula de la sección"""
        matricula = Matricula.query.filter_by(id_seccion=self.id_seccion).first()
        if not matricula or matricula.total_estudiantes == 0:
            return 0
        return round((self.total_asistentes / matricula.total_estudiantes) * 100, 2)
    
    def __repr__(self):
        return f'<Asistencia {self.fecha} Sección:{self.id_seccion} H:{self.asistentes_h} M:{self.asistentes_m}>'
