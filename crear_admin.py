"""
Script para crear usuario administrador
"""
from app import app, db
from models import Usuario
from extensions import bcrypt

def crear_admin():
    with app.app_context():
        # Verificar si ya existe un administrador
        admin_existente = Usuario.query.filter_by(email='admin@ueipab.edu.ve').first()
        
        if admin_existente:
            print(f"⚠️  Ya existe un administrador con el email: admin@ueipab.edu.ve")
            print(f"   Nombre: {admin_existente.nombre} {admin_existente.apellido}")
            respuesta = input("¿Deseas actualizar la contraseña? (s/n): ")
            
            if respuesta.lower() == 's':
                nueva_contraseña = input("Ingresa la nueva contraseña: ")
                admin_existente.contraseña = bcrypt.generate_password_hash(nueva_contraseña).decode('utf-8')
                db.session.commit()
                print("✅ Contraseña actualizada correctamente")
            else:
                print("❌ Operación cancelada")
            return
        
        # Crear nuevo administrador
        print("\n=== Crear Usuario Administrador ===\n")
        
        nombre = input("Nombre (default: Admin): ").strip() or "Admin"
        apellido = input("Apellido (default: Sistema): ").strip() or "Sistema"
        email = input("Email (default: admin@ueipab.edu.ve): ").strip() or "admin@ueipab.edu.ve"
        contraseña = input("Contraseña (default: admin123): ").strip() or "admin123"
        
        # Verificar si el email ya existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            print(f"\n❌ Error: Ya existe un usuario con el email {email}")
            return
        
        # Hash de la contraseña
        contraseña_hash = bcrypt.generate_password_hash(contraseña).decode('utf-8')
        
        # Crear administrador
        admin = Usuario(
            nombre=nombre,
            apellido=apellido,
            email=email,
            contraseña=contraseña_hash,
            rol='administrador'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("\n✅ Usuario administrador creado exitosamente!")
        print(f"\n📋 Credenciales:")
        print(f"   Email: {email}")
        print(f"   Contraseña: {contraseña}")
        print(f"   Rol: Administrador")
        print(f"\n🔐 Accede al sistema en: http://localhost:5000/login")

if __name__ == '__main__':
    try:
        crear_admin()
    except Exception as e:
        print(f"\n❌ Error: {e}")
