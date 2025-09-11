from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Modelo de base de datos para estudiantes
class Estudiante(db.Model):
    __tablename__ = 'estudiantes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    genero = db.Column(db.Enum('masculino', 'femenino'), nullable=False, default='masculino')
    seccion = db.Column(db.String(5), nullable=False, default='A')
    etapa = db.Column(db.Enum('inicial', 'primaria', 'secundaria'), nullable=False, default='primaria')
    fecha_registro = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Estudiante {self.nombre} {self.apellido}>'

# Modelo de base de datos para asistencias
class Asistencia(db.Model):
    __tablename__ = 'asistencias'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    presente = db.Column(db.Boolean, nullable=False, default=False)
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    estudiante = db.relationship('Estudiante', backref=db.backref('asistencias', lazy=True))
    
    def __repr__(self):
        return f'<Asistencia {self.estudiante.nombre} - {self.fecha}>'
