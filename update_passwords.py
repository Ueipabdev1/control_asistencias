#!/usr/bin/env python3
"""
Script para actualizar contraseñas en texto plano a contraseñas hasheadas con bcrypt
"""
from app import app, bcrypt
from models import db, Usuario

def update_passwords():
    with app.app_context():
        # Obtener todos los usuarios
        usuarios = Usuario.query.all()
        
        updated_count = 0
        for usuario in usuarios:
            # Verificar si la contraseña ya está hasheada (bcrypt hash empieza con $2b$)
            if not usuario.contraseña.startswith('$2b$'):
                print(f"Actualizando contraseña para: {usuario.email}")
                # Hashear la contraseña actual
                hashed_password = bcrypt.generate_password_hash(usuario.contraseña).decode('utf-8')
                usuario.contraseña = hashed_password
                updated_count += 1
            else:
                print(f"Contraseña ya hasheada para: {usuario.email}")
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✅ Se actualizaron {updated_count} contraseñas correctamente")
        else:
            print("\n✅ Todas las contraseñas ya estaban hasheadas")

if __name__ == '__main__':
    update_passwords()
