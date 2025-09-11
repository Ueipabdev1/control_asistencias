from flask import Flask
from datetime import datetime
import os
from sqlalchemy import func, and_, extract
from models import db, Estudiante, Asistencia

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'

# Configuración para MariaDB/MySQL
# Actualiza estos valores con tus credenciales de MariaDB
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:0000@localhost/control_asistencias?charset=utf8mb4'
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

# Registrar blueprints
from routes import main_bp, admin_bp
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)

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
