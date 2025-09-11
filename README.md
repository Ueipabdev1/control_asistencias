# Sistema de Control de Asistencias

Una aplicación web moderna desarrollada con Flask y AJAX para que los profesores puedan gestionar la asistencia de estudiantes de manera eficiente.

## Características

- ✅ Interfaz moderna y responsiva con Bootstrap 5
- ✅ Gestión dinámica de estudiantes con AJAX
- ✅ Registro de asistencia por fecha
- ✅ Campo de observaciones para cada estudiante
- ✅ Carga y edición de asistencias existentes
- ✅ Agregar nuevos estudiantes dinámicamente
- ✅ Base de datos SQLite integrada
- ✅ Validaciones y alertas en tiempo real

## Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd control_asistencias
   ```

2. **Crear un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   
   # En Windows:
   venv\Scripts\activate
   
   # En macOS/Linux:
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

## Uso

1. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```

2. **Abrir en el navegador:**
   ```
   http://localhost:5000
   ```

## Funcionalidades

### Gestión de Estudiantes
- La aplicación incluye 5 estudiantes de ejemplo al iniciar
- Puedes agregar nuevos estudiantes usando el formulario en la parte superior
- Cada estudiante tiene: nombre, apellido y código único

### Registro de Asistencia
- Selecciona la fecha de la clase
- Marca cada estudiante como "Presente" o "Ausente"
- Agrega observaciones opcionales para cada estudiante
- Guarda la asistencia con un clic

### Cargar Asistencias Existentes
- Selecciona una fecha y haz clic en "Cargar Asistencia Existente"
- Edita y actualiza asistencias previamente guardadas

## Estructura del Proyecto

```
control_asistencias/
├── app.py                 # Aplicación principal Flask
├── requirements.txt       # Dependencias del proyecto
├── asistencias.db        # Base de datos SQLite (se crea automáticamente)
├── templates/
│   └── index.html        # Plantilla HTML principal
└── README.md            # Este archivo
```

## Tecnologías Utilizadas

- **Backend:** Flask, SQLAlchemy
- **Frontend:** HTML5, CSS3, JavaScript (jQuery), Bootstrap 5
- **Base de datos:** SQLite
- **AJAX:** Para comunicación asíncrona
- **Iconos:** Font Awesome

## API Endpoints

- `GET /` - Página principal
- `GET /estudiantes` - Obtener lista de estudiantes
- `POST /guardar_asistencia` - Guardar asistencia
- `GET /obtener_asistencia/<fecha>` - Obtener asistencia por fecha
- `POST /agregar_estudiante` - Agregar nuevo estudiante

## Personalización

### Cambiar el diseño
Edita los estilos CSS en `templates/index.html` para personalizar la apariencia.

### Agregar campos adicionales
Modifica los modelos en `app.py` y actualiza la interfaz en `index.html`.

### Configurar base de datos
Por defecto usa SQLite. Para usar otra base de datos, modifica `SQLALCHEMY_DATABASE_URI` en `app.py`.

## Desarrollo

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Soporte

Si encuentras algún problema o tienes sugerencias, por favor crea un issue en el repositorio.
