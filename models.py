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
    activa = db.Column(db.Boolean, default=True)
    
    # Relación con grados
    grados = db.relationship('Grado', backref='etapa', lazy=True, cascade='all, delete-orphan')
    
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

# Modelo para grados (nuevo en V2)
class Grado(db.Model):
    __tablename__ = 'grado'
    
    id_grado = db.Column(db.Integer, primary_key=True)
    id_etapa = db.Column(db.Integer, db.ForeignKey('etapa.id_etapa', ondelete='CASCADE'), nullable=False)
    nombre_grado = db.Column(db.String(100), nullable=False)
    orden = db.Column(db.Integer, nullable=False, comment='Orden del grado dentro de la etapa')
    descripcion = db.Column(db.String(255))
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    secciones = db.relationship('Seccion', backref='grado', lazy=True, cascade='all, delete-orphan')
    
    # Constraint único
    __table_args__ = (db.UniqueConstraint('id_etapa', 'nombre_grado', name='unique_grado_etapa'),)
    
    def __repr__(self):
        return f'<Grado {self.nombre_grado}>'

# Modelo para secciones (refactorizado en V2)
class Seccion(db.Model):
    __tablename__ = 'seccion'
    
    id_seccion = db.Column(db.Integer, primary_key=True)
    id_grado = db.Column(db.Integer, db.ForeignKey('grado.id_grado', ondelete='CASCADE'), nullable=False)
    nombre_seccion = db.Column(db.String(50), nullable=False, comment='A, B, C, Única, etc.')
    capacidad_maxima = db.Column(db.Integer, nullable=True, comment='Capacidad máxima de estudiantes')
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Relaciones
    profesores = db.relationship('ProfesorSeccion', backref='seccion', lazy=True)
    estudiantes = db.relationship('Estudiante', backref='seccion', lazy=True)
    
    # Constraint único
    __table_args__ = (db.UniqueConstraint('id_grado', 'nombre_seccion', name='unique_seccion_grado'),)
    
    @property
    def nombre_completo(self):
        """Retorna nombre completo: Etapa - Grado - Sección"""
        return f"{self.grado.etapa.nombre_etapa} - {self.grado.nombre_grado} - Sección {self.nombre_seccion}"
    
    @property
    def total_estudiantes(self):
        """Cuenta estudiantes activos en la sección"""
        return Estudiante.query.filter_by(id_seccion=self.id_seccion, activo=True).count()
    
    def __repr__(self):
        return f'<Seccion {self.nombre_seccion} - Grado:{self.id_grado}>'

# Modelo para relación profesor-secciones (muchos a muchos)
class ProfesorSeccion(db.Model):
    __tablename__ = 'profesor_seccion'
    
    id_profesor_seccion = db.Column(db.Integer, primary_key=True)
    id_profesor = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario', ondelete='CASCADE'), nullable=False)
    id_seccion = db.Column(db.Integer, db.ForeignKey('seccion.id_seccion', ondelete='CASCADE'), nullable=False)
    fecha_asignacion = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Constraint único para evitar duplicados
    __table_args__ = (db.UniqueConstraint('id_profesor', 'id_seccion', name='unique_profesor_seccion'),)
    
    def __repr__(self):
        return f'<ProfesorSeccion {self.id_profesor}-{self.id_seccion}>'

# Modelo para matrícula (conteo por género por sección) - LEGACY
class Matricula(db.Model):
    __tablename__ = 'matricula'
    
    id_matricula = db.Column(db.Integer, primary_key=True)
    id_seccion = db.Column(db.Integer, db.ForeignKey('seccion.id_seccion', ondelete='CASCADE'), nullable=False, unique=True)
    num_estudiantes_h = db.Column(db.Integer, default=0, comment='Número de estudiantes hombres')
    num_estudiantes_m = db.Column(db.Integer, default=0, comment='Número de estudiantes mujeres')
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def total_estudiantes(self):
        return (self.num_estudiantes_h or 0) + (self.num_estudiantes_m or 0)
    
    def __repr__(self):
        return f'<Matricula Sección:{self.id_seccion} H:{self.num_estudiantes_h} M:{self.num_estudiantes_m}>'

# Modelo para estudiantes individuales (nuevo en V2)
class Estudiante(db.Model):
    __tablename__ = 'estudiante'
    
    id_estudiante = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False, index=True, comment='Cédula de identidad')
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    genero = db.Column(db.Enum('M', 'F'), nullable=False, comment='M=Masculino, F=Femenino')
    id_seccion = db.Column(db.Integer, db.ForeignKey('seccion.id_seccion', ondelete='RESTRICT'), nullable=False)
    activo = db.Column(db.Boolean, default=True, comment='Estudiante activo en el sistema')
    fecha_registro = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    asistencias = db.relationship('AsistenciaEstudiante', backref='estudiante', lazy=True, cascade='all, delete-orphan')
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def genero_texto(self):
        return 'Masculino' if self.genero == 'M' else 'Femenino'
    
    def __repr__(self):
        return f'<Estudiante {self.cedula} - {self.nombre} {self.apellido}>'

# Modelo para asistencia individual por estudiante (nuevo en V2)
class AsistenciaEstudiante(db.Model):
    __tablename__ = 'asistencia_estudiante'
    
    id_asistencia_estudiante = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id_estudiante', ondelete='CASCADE'), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    presente = db.Column(db.Boolean, default=False, nullable=False, comment='TRUE=Presente, FALSE=Ausente')
    observaciones = db.Column(db.Text, nullable=True, comment='Observaciones opcionales')
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario', ondelete='SET NULL'), nullable=True, comment='Usuario que registró')
    fecha_registro = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # Constraint único para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('id_estudiante', 'fecha', name='unique_asistencia_estudiante'),
        db.Index('idx_fecha_presente', 'fecha', 'presente')
    )
    
    @property
    def estado_texto(self):
        return 'Presente' if self.presente else 'Ausente'
    
    def __repr__(self):
        estado = "Presente" if self.presente else "Ausente"
        return f'<AsistenciaEstudiante {self.fecha} - Estudiante:{self.id_estudiante} - {estado}>'

# Modelo para observaciones generales de sección
class ObservacionSeccion(db.Model):
    __tablename__ = 'observacion_seccion'
    
    id_observacion = db.Column(db.Integer, primary_key=True)
    id_seccion = db.Column(db.Integer, db.ForeignKey('seccion.id_seccion', ondelete='CASCADE'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    observaciones = db.Column(db.Text, nullable=True, comment='Observaciones generales de la clase')
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario', ondelete='SET NULL'), nullable=True, comment='Usuario que registró la observación')
    fecha_registro = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraint único para evitar duplicados por sección y fecha
    __table_args__ = (db.UniqueConstraint('id_seccion', 'fecha', name='unique_observacion_seccion'),)
    
    def __repr__(self):
        return f'<ObservacionSeccion {self.fecha} - Sección:{self.id_seccion}>'

# =====================================================
# MODELOS LEGACY (para compatibilidad con datos antiguos)
# =====================================================

# Modelo para asistencia legacy (registra por género por sección)
class Asistencia(db.Model):
    __tablename__ = 'asistencia_legacy'
    
    id_asistencia = db.Column(db.Integer, primary_key=True)
    id_seccion_legacy = db.Column(db.Integer, nullable=False, comment='Referencia a secciones antiguas')
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario', ondelete='SET NULL'), nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    asistentes_h = db.Column(db.Integer, default=0)
    asistentes_m = db.Column(db.Integer, default=0)
    
    @property
    def total_asistentes(self):
        return (self.asistentes_h or 0) + (self.asistentes_m or 0)
    
    def __repr__(self):
        return f'<AsistenciaLegacy {self.fecha} Sección:{self.id_seccion_legacy}>'
