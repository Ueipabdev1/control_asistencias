from flask import Flask
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import func, and_, extract
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, Etapa, Usuario, Seccion, ProfesorSeccion, Matricula, Asistencia
from extensions import bcrypt, login_manager

app = Flask(__name__)

# Handle reverse proxy with script name prefix
class ReverseProxied:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        return self.app(environ, start_response)

app.wsgi_app = ReverseProxied(app.wsgi_app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configuración desde variables de entorno
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tu_clave_secreta_aqui')

# Inicializar Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

# Inicializar Flask-Bcrypt
bcrypt.init_app(app)

# Configuración para MariaDB/MySQL
# En producción (Railway), usa DATABASE_URL de las variables de entorno
# En desarrollo local, usa la configuración por defecto
database_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:0000@localhost:3306/control_asistencias?charset=utf8mb4')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {
        'auth_plugin_map': {
            'mysql_native_password': 'mysql_native_password'
        },
        'charset': 'utf8mb4'
    }
}

# Inicializar la base de datos con la aplicación
db.init_app(app)

# User loader para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Registrar blueprints
from routes import main_bp, admin_bp, auth_bp
from routes_estudiantes import estudiantes_bp, asistencia_individual_bp
from routes_observaciones import observaciones_bp
from routes_estadisticas import estadisticas_bp
from routes_calendario import calendario_bp

app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(estudiantes_bp)
app.register_blueprint(asistencia_individual_bp)
app.register_blueprint(observaciones_bp)
app.register_blueprint(estadisticas_bp)
app.register_blueprint(calendario_bp)

if __name__ == '__main__':
    try:
        with app.app_context():
            # Verificar conexión a la base de datos
            db.engine.connect()
            print("✅ Conexión a MariaDB establecida correctamente")
            
            # Crear tablas si no existen (solo para desarrollo)
            # En producción, usa el script SQL proporcionado
            db.create_all()
            print("✅ Tablas verificadas/creadas")
            
    except Exception as e:
        print(f"❌ Error de conexión a MariaDB: {e}")
        print("\n📋 Instrucciones:")
        print("1. Asegúrate de que MariaDB esté ejecutándose")
        print("2. Ejecuta el script database_schema.sql en MariaDB")
        print("3. Actualiza las credenciales de conexión en app.py línea 12")
        print("4. Instala PyMySQL: pip install PyMySQL")
        exit(1)
    
    app.run(debug=True)
