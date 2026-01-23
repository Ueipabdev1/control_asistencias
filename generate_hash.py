#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para generar hash bcrypt de contraseñas
"""
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

# Generar hash para password123
password = "password123"
hashed = bcrypt.generate_password_hash(password).decode('utf-8')

print("=" * 60)
print("HASH BCRYPT GENERADO")
print("=" * 60)
print(f"Contraseña: {password}")
print(f"Hash: {hashed}")
print("=" * 60)
print("\nCopia este hash y reemplázalo en seed_data.sql")
print("=" * 60)
