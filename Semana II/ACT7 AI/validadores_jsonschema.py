"""
Validadores con JSON Schema para la API EcoMarket.

Este módulo es una alternativa al validadores.py manual.
Usa jsonschema para validación basada en esquemas JSON.

Instalación: pip install jsonschema

Ventajas:
- Esquemas reutilizables entre lenguajes
- Estándar de industria (RFC 8927)
- Exportable para documentación OpenAPI
"""

from jsonschema import Draft7Validator, FormatChecker
from typing import List

# ============================================================
# ESQUEMAS JSON
# ============================================================

PRODUCTOR_SCHEMA = {
    "type": "object",
    "required": ["id", "nombre"],
    "properties": {
        "id": {
            "type": "integer",
            "description": "Identificador único del productor"
        },
        "nombre": {
            "type": "string",
            "description": "Nombre del productor"
        }
    },
    "additionalProperties": True
}

PRODUCTO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://ecomarket.api/schemas/producto.json",
    "title": "Producto",
    "description": "Esquema para productos de EcoMarket",
    "type": "object",
    "required": ["id", "nombre", "precio", "categoria"],
    "properties": {
        "id": {
            "type": "integer",
            "description": "Identificador único del producto"
        },
        "nombre": {
            "type": "string",
            "description": "Nombre del producto"
        },
        "precio": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Precio del producto (debe ser > 0)"
        },
        "categoria": {
            "type": "string",
            "enum": ["frutas", "verduras", "lacteos", "miel", "conservas"],
            "description": "Categoría del producto"
        },
        "disponible": {
            "type": "boolean",
            "description": "Indica si el producto está disponible"
        },
        "descripcion": {
            "type": "string",
            "description": "Descripción detallada del producto"
        },
        "productor": PRODUCTOR_SCHEMA,
        "creado_en": {
            "type": "string",
            "format": "date-time",
            "description": "Fecha de creación en formato ISO 8601"
        }
    },
    "additionalProperties": True
}

LISTA_PRODUCTOS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Lista de Productos",
    "description": "Array de productos de EcoMarket",
    "type": "array",
    "items": PRODUCTO_SCHEMA
}

# ============================================================
# VALIDADORES COMPILADOS (mejor rendimiento)
# ============================================================

# FormatChecker valida formatos como date-time, email, uri, etc.
format_checker = FormatChecker()

# Compilar validadores una vez para reutilizar
_producto_validator = Draft7Validator(PRODUCTO_SCHEMA, format_checker=format_checker)
_lista_validator = Draft7Validator(LISTA_PRODUCTOS_SCHEMA, format_checker=format_checker)


# ============================================================
# EXCEPCIÓN COMPATIBLE
# ============================================================

class ValidationError(Exception):
    """Error de validación compatible con el módulo manual."""
    pass


# ============================================================
# FUNCIONES DE VALIDACIÓN (API compatible con validadores.py)
# ============================================================

def _formatear_errores(errors) -> str:
    """Formatea errores de jsonschema a mensajes legibles."""
    mensajes = []
    for error in errors:
        # json_path da la ubicación (ej: $.precio, $.productor.id)
        path = error.json_path if error.json_path != "$" else "raíz"
        mensajes.append(f"{path}: {error.message}")
    return "; ".join(mensajes)


def validar_producto(data: dict, contexto: str = "") -> dict:
    """
    Valida un producto individual usando JSON Schema.
    
    Args:
        data: Diccionario con datos del producto
        contexto: Prefijo para mensajes de error
    
    Returns:
        dict: El mismo diccionario si pasa validación
    
    Raises:
        ValidationError: Si la validación falla
    """
    # Verificar que sea diccionario primero
    if not isinstance(data, dict):
        raise ValidationError(
            f"{contexto}Se esperaba un objeto producto, "
            f"pero recibió: {type(data).__name__}"
        )
    
    # Recolectar todos los errores
    errores = list(_producto_validator.iter_errors(data))
    
    if errores:
        raise ValidationError(f"{contexto}{_formatear_errores(errores)}")
    
    return data


def validar_lista_productos(data: list) -> list:
    """
    Valida una lista de productos usando JSON Schema.
    
    Args:
        data: Lista de diccionarios de productos
    
    Returns:
        list: La misma lista si todos pasan validación
    
    Raises:
        ValidationError: Si data no es lista o algún producto falla
    """
    if not isinstance(data, list):
        raise ValidationError(
            f"Se esperaba una lista de productos, "
            f"pero recibió: {type(data).__name__}"
        )
    
    errores = list(_lista_validator.iter_errors(data))
    
    if errores:
        raise ValidationError(_formatear_errores(errores))
    
    return data


# ============================================================
# UTILIDADES ADICIONALES
# ============================================================

def exportar_schema_producto() -> dict:
    """
    Retorna el esquema JSON para uso en documentación.
    
    Útil para:
    - Generar documentación OpenAPI/Swagger
    - Compartir con equipos frontend/móvil
    - Validación en otros lenguajes
    """
    return PRODUCTO_SCHEMA.copy()


def exportar_schema_lista() -> dict:
    """Retorna el esquema JSON para lista de productos."""
    return LISTA_PRODUCTOS_SCHEMA.copy()


# ============================================================
# EJEMPLO DE USO
# ============================================================

if __name__ == "__main__":
    # Ejemplo de producto válido
    producto_valido = {
        "id": 1,
        "nombre": "Manzanas Orgánicas",
        "precio": 25.50,
        "categoria": "frutas",
        "disponible": True,
        "productor": {"id": 1, "nombre": "Granja El Sol"},
        "creado_en": "2024-01-15T10:30:00Z"
    }
    
    try:
        resultado = validar_producto(producto_valido)
        print("✅ Producto válido:", resultado)
    except ValidationError as e:
        print("❌ Error:", e)
    
    # Ejemplo de producto inválido
    producto_invalido = {
        "id": "no-es-int",
        "nombre": "Test",
        "precio": -5,
        "categoria": "invalida"
    }
    
    try:
        validar_producto(producto_invalido)
    except ValidationError as e:
        print("❌ Error esperado:", e)
    
    # Mostrar esquema exportable
    print("\n📋 Esquema JSON exportable:")
    import json
    print(json.dumps(exportar_schema_producto(), indent=2))
