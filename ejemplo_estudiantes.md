# Ejemplo de Archivo Excel para Carga de Estudiantes

## Formato Requerido

El archivo Excel debe tener las siguientes columnas (exactamente con estos nombres):

| Grado | Sección | Nombre | Apellido | Cédula de identidad | Género |
|-------|---------|--------|----------|---------------------|--------|
| 1er grado | Única | Juan | Pérez | V12345678 | M |
| 1er grado | Única | María | González | V87654321 | F |
| 2do grado | A | Pedro | Ramírez | V11223344 | M |
| 2do grado | A | Ana | Martínez | V55667788 | F |
| 3er año | A | Carlos | López | V99887766 | M |
| 3er año | B | Laura | Rodríguez | V44556677 | F |

## Notas Importantes:

1. **Grado**: Debe coincidir exactamente con los grados en la base de datos
   - Ejemplos: "1er grado", "2do grado", "3er grado", "1er año", "2do año", "3er año"

2. **Sección**: Debe coincidir con las secciones existentes
   - Ejemplos: "A", "B", "C", "Única"

3. **Género**: Solo acepta dos valores:
   - "M" para Masculino
   - "F" para Femenino

4. **Cédula de identidad**: Debe ser única por estudiante
   - Formato: V12345678 (con o sin la V)

## Cómo Usar:

1. Crea un archivo Excel (.xlsx o .xls)
2. Agrega las columnas exactamente como se muestran arriba
3. Llena los datos de los estudiantes
4. Ve a "Gestión de Matrícula" en el sistema
5. Haz clic en "Seleccionar Archivo Excel"
6. Selecciona tu archivo
7. (Opcional) Marca "Actualizar estudiantes existentes" si quieres sobrescribir datos
8. Haz clic en "Cargar Archivo"

## Ejemplo de Datos para Probar:

Puedes usar estos datos de ejemplo para crear tu archivo Excel:

### Maternal - Nivel 1 - Única
- Ana Pérez (V10000001) - F
- Juan García (V10000002) - M
- María López (V10000003) - F

### Primaria - 1er grado - Única
- Carlos Martínez (V20000001) - M
- Laura Rodríguez (V20000002) - F
- Pedro Sánchez (V20000003) - M

### Secundaria - 1er año - A
- José Hernández (V30000001) - M
- Carmen Díaz (V30000002) - F
- Luis Torres (V30000003) - M

### Secundaria - 1er año - B
- Rosa Flores (V30000004) - F
- Miguel Ruiz (V30000005) - M
- Elena Castro (V30000006) - F
