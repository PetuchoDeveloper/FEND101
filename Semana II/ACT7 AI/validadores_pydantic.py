"""
Validadores con Pydantic v2 para la API EcoMarket.

Este módulo es una alternativa al validadores.py manual.
Usa Pydantic v2 para validación declarativa con tipos.

Instalación: pip install pydantic>=2.0

Ventajas:
- Menos código (~25 líneas vs ~80)
- Autocompletado en IDEs
- Mensajes de error descriptivos
- Serialización automática (model_dump)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal, List
from datetime import datetime


# Categorías válidas como Literal (enum en tiempo de compilación)
CategoriaProducto = Literal['frutas', 'verduras', 'lacteos', 'miel', 'conservas']


class Productor(BaseModel):
    """Modelo para datos del productor (campo anidado en Producto)."""
    id: int
    nombre: str


class Producto(BaseModel):
    """
    Modelo de Producto para EcoMarket.
    
    Campos requeridos:
        - id: Identificador único
        - nombre: Nombre del producto
        - precio: Precio (debe ser > 0)
        - categoria: Una de las categorías válidas
    
    Campos opcionales:
        - disponible: Si está disponible
        - descripcion: Descripción del producto
        - productor: Datos del productor
        - creado_en: Fecha de creación (ISO 8601)
    """
    model_config = ConfigDict(extra='allow')  # Permitir campos adicionales
    
    id: int
    nombre: str
    precio: float = Field(gt=0, description="Precio debe ser mayor a 0")
    categoria: CategoriaProducto
    disponible: Optional[bool] = None
    descripcion: Optional[str] = None
    productor: Optional[Productor] = None
    creado_en: Optional[datetime] = None


# ============================================================
# FUNCIONES DE VALIDACIÓN (API compatible con validadores.py)
# ============================================================

class ValidationError(Exception):
    """Error de validación compatible con el módulo manual."""
    pass


def validar_producto(data: dict, contexto: str = "") -> dict:
    """
    Valida un producto individual usando Pydantic.
    
    Args:
        data: Diccionario con datos del producto
        contexto: Prefijo para mensajes de error (ignorado, Pydantic incluye ubicación)
    
    Returns:
        dict: Datos validados como diccionario
    
    Raises:
        ValidationError: Si la validación falla
    """
    try:
        producto = Producto.model_validate(data)
        return producto.model_dump(mode='json', exclude_none=True)
    except Exception as e:
        raise ValidationError(f"{contexto}{e}")


def validar_lista_productos(data: list) -> list:
    """
    Valida una lista de productos usando Pydantic.
    
    Args:
        data: Lista de diccionarios de productos
    
    Returns:
        list: Lista de productos validados
    
    Raises:
        ValidationError: Si algún producto falla validación
    """
    if not isinstance(data, list):
        raise ValidationError(
            f"Se esperaba una lista de productos, pero recibió: {type(data).__name__}"
        )
    
    productos_validados = []
    for i, item in enumerate(data):
        try:
            producto = Producto.model_validate(item)
            productos_validados.append(producto.model_dump(mode='json', exclude_none=True))
        except Exception as e:
            raise ValidationError(f"Producto[{i}]: {e}")
    
    return productos_validados


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
        "productor": {"id": 1, "nombre": "Granja El Sol"}
    }
    
    try:
        resultado = validar_producto(producto_valido)
        print("✅ Producto válido:", resultado)
    except ValidationError as e:
        print("❌ Error:", e)
    
    # Ejemplo de producto inválido
    producto_invalido = {
        "id": "no-es-int",  # Error: debe ser int
        "nombre": "Test",
        "precio": -5,  # Error: debe ser > 0
        "categoria": "invalida"  # Error: no está en el enum
    }
    
    try:
        validar_producto(producto_invalido)
    except ValidationError as e:
        print("❌ Error esperado:", e)
