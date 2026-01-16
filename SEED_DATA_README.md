# 📊 Script de Datos de Prueba - Control de Asistencias

Este script SQL (`seed_data.sql`) genera datos de prueba completos para el sistema de control de asistencias, cubriendo un mes completo de operación (Diciembre 2025).

## 🎯 Contenido del Script

### **Usuarios Creados**
- **2 Administradores**
  - `admin@ueipab.edu` - Carlos Rodríguez
  - `maria.gonzalez@ueipab.edu` - María González

- **14 Profesores** distribuidos por etapas:
  - **Maternal (3)**: Ana Martínez, Luis Pérez, Carmen Silva
  - **Primaria (6)**: Roberto Fernández, Patricia López, Jorge Ramírez, Elena Torres, Miguel Vargas, Sandra Morales
  - **Secundaria (5)**: Fernando Castro, Gabriela Mendoza, Ricardo Herrera, Daniela Ortiz, Alberto Ruiz

### **Contraseña Universal**
Todos los usuarios tienen la misma contraseña para facilitar las pruebas:
```
password123
```

### **Datos Generados**
- ✅ **16 usuarios** (2 admins + 14 profesores)
- ✅ **15 secciones** con matrícula (Maternal, Primaria, Secundaria)
- ✅ **16 asignaciones** profesor-sección
- ✅ **465 estudiantes** matriculados en total
- ✅ **~330 registros de asistencia** (22 días laborables × 15 secciones)
- ✅ **Período**: 1-31 Diciembre 2025

### **Cronología de Asistencias**
El script simula un mes completo con patrones realistas:

- **Semanas 1-3 (1-19 Dic)**: Asistencia normal (~90-95%)
- **Semana 4 (22-24 Dic)**: Asistencia reducida por Navidad (~70-80%)
- **Semana 5 (29-31 Dic)**: Asistencia baja por fin de año (~50-60%)

## 🚀 Cómo Ejecutar el Script

### **Opción 1: Desde MySQL/MariaDB CLI**
```bash
mysql -u root -p control_asistencias < seed_data.sql
```

### **Opción 2: Desde phpMyAdmin**
1. Abre phpMyAdmin
2. Selecciona la base de datos `control_asistencias`
3. Ve a la pestaña "SQL"
4. Copia y pega el contenido de `seed_data.sql`
5. Haz clic en "Continuar"

### **Opción 3: Desde HeidiSQL/DBeaver**
1. Conecta a tu servidor MariaDB
2. Abre el archivo `seed_data.sql`
3. Ejecuta el script completo (F9)

### **Opción 4: Desde Python (si tienes la app corriendo)**
```bash
# En la carpeta del proyecto
python -c "import pymysql; conn = pymysql.connect(host='localhost', user='root', password='tu_password', database='control_asistencias'); cursor = conn.cursor(); cursor.execute(open('seed_data.sql').read()); conn.commit()"
```

## 📋 Usuarios para Probar

### **Como Administrador**
```
Email: admin@ueipab.edu
Contraseña: password123
```
**Puede hacer:**
- Ver todas las secciones
- Registrar asistencias en cualquier sección
- Acceder a todos los dashboards
- Gestionar profesores y matrículas

### **Como Profesor (Ejemplo: Maternal)**
```
Email: ana.martinez@ueipab.edu
Contraseña: password123
Sección asignada: Nivel 1 maternal
```

### **Como Profesor (Ejemplo: Primaria)**
```
Email: roberto.fernandez@ueipab.edu
Contraseña: password123
Sección asignada: 1er grado primaria
```

### **Como Profesor (Ejemplo: Secundaria)**
```
Email: fernando.castro@ueipab.edu
Contraseña: password123
Secciones asignadas: 1er año y 5to año secundaria
```

## 🧪 Casos de Prueba Sugeridos

### **1. Probar Restricciones de Profesor**
1. Inicia sesión como `ana.martinez@ueipab.edu`
2. Ve a "Control de Asistencias"
3. Verifica que solo aparece "Nivel 1 maternal" en el dropdown
4. Intenta registrar asistencia (debe funcionar)

### **2. Probar Dashboard Administrativo**
1. Inicia sesión como `admin@ueipab.edu`
2. Ve a "Dashboard Administrativo"
3. Verifica que se muestren gráficos con datos reales:
   - Distribución por género
   - Asistencia por etapa
   - Tendencia temporal
   - Top 5 secciones
4. Cambia los filtros de fecha (1-31 Diciembre 2025)
5. Cambia entre períodos: Diario, Semanal, Mensual

### **3. Probar Gestión de Profesores**
1. Inicia sesión como administrador
2. Ve a "Gestión de Profesores"
3. Verifica que aparezcan todos los profesores
4. Prueba asignar/desasignar secciones

### **4. Probar Múltiples Secciones por Profesor**
1. Inicia sesión como `fernando.castro@ueipab.edu`
2. Verifica que puede ver 2 secciones: 1er año y 5to año
3. Registra asistencia en ambas

## 📊 Estadísticas Esperadas

Con estos datos, deberías ver aproximadamente:

- **Asistencia promedio general**: ~85-90%
- **Total estudiantes**: 465
- **Secciones activas**: 15
- **Días con registro**: 22 días laborables
- **Registros de asistencia**: ~330

### **Por Etapa**
- **Maternal**: 72 estudiantes (3 secciones)
- **Primaria**: 180 estudiantes (6 secciones)
- **Secundaria**: 210 estudiantes (6 secciones)

## ⚠️ Notas Importantes

1. **El script limpia datos existentes**: Usa `TRUNCATE` en las tablas de datos, pero mantiene la estructura
2. **No afecta las tablas de estructura**: Las tablas `etapa` y `secciones` se mantienen
3. **Contraseñas hasheadas**: Las contraseñas están encriptadas con bcrypt
4. **Fechas en el pasado**: Las fechas son de Diciembre 2025 para simular datos históricos
5. **Asistencias realistas**: Los números varían para simular comportamiento real

## 🔄 Para Limpiar y Volver a Ejecutar

Si quieres limpiar todo y volver a ejecutar el script:

```sql
-- El script ya incluye limpieza automática
-- Solo ejecuta seed_data.sql nuevamente
```

## 🐛 Solución de Problemas

### Error: "Foreign key constraint fails"
- Asegúrate de que las tablas `etapa` y `secciones` existan
- Ejecuta primero `database_schema.sql` si es necesario

### Error: "Duplicate entry"
- El script limpia automáticamente, pero si persiste:
```sql
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE asistencia;
TRUNCATE TABLE profesor_secciones;
TRUNCATE TABLE matricula;
DELETE FROM usuario WHERE id_usuario > 0;
SET FOREIGN_KEY_CHECKS = 1;
```

### No se muestran datos en el dashboard
- Verifica que las fechas del filtro incluyan Diciembre 2025
- Cambia el rango de fechas a: 2025-12-01 hasta 2025-12-31

## 📝 Personalización

Si quieres modificar los datos:

1. **Cambiar fechas**: Busca y reemplaza `2025-12-` por el mes deseado
2. **Agregar más profesores**: Añade más `INSERT INTO usuario`
3. **Modificar asistencias**: Ajusta los números en los `INSERT INTO asistencia`
4. **Cambiar contraseña**: Genera un nuevo hash bcrypt y reemplázalo

### Generar nuevo hash bcrypt en Python:
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
print(bcrypt.generate_password_hash('tu_nueva_contraseña').decode('utf-8'))
```

## ✅ Verificación Post-Ejecución

Después de ejecutar el script, verifica:

```sql
-- Ver resumen
SELECT COUNT(*) FROM usuario;
SELECT COUNT(*) FROM matricula;
SELECT COUNT(*) FROM profesor_secciones;
SELECT COUNT(*) FROM asistencia;

-- Ver rango de fechas
SELECT MIN(fecha), MAX(fecha) FROM asistencia;

-- Ver profesores y sus secciones
SELECT u.nombre, u.apellido, s.nombre_seccion 
FROM usuario u
JOIN profesor_secciones ps ON u.id_usuario = ps.id_profesor
JOIN secciones s ON ps.id_seccion = s.id_seccion
ORDER BY u.apellido;
```

---

**¡Listo para probar el sistema completo!** 🎉
