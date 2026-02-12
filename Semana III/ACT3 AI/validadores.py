"""
Módulo de validación para respuestas de la API EcoMarket.
Valida estructura, tipos y reglas de negocio de los datos recibidos.
"""

import re
from typing import Any

# Categorías válidas para productos EcoMarket
CATEGORIAS_VALIDAS = ['frutas', 'verduras', 'lacteos', 'miel', 'conservas']

# Patrón ISO 8601 simplificado (YYYY-MM-DDTHH:MM:SS con zona horaria opcional)
ISO8601_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$'
)


class ValidationError(Exception):
    """Error de validación con mensaje descriptivo del campo y razón."""
    pass


def _validar_campo_requerido(data: dict, campo: str, contexto: str = "") -> None:
    """Verifica que un campo requerido exista en el diccionario."""
    if campo not in data:
        raise ValidationError(
            f"{contexto}Campo requerido '{campo}' no encontrado en la respuesta"
        )


def _validar_tipo(valor: Any, campo: str, tipo_esperado: type, contexto: str = "") -> None:
    """Verifica que un valor sea del tipo esperado."""
    # Para precio, aceptamos int o float
    if tipo_esperado == float and isinstance(valor, (int, float)):
        return
    
    if not isinstance(valor, tipo_esperado):
        tipo_actual = type(valor).__name__
        tipo_nombre = tipo_esperado.__name__
        raise ValidationError(
            f"{contexto}Campo '{campo}' debe ser {tipo_nombre}, "
            f"pero recibió {tipo_actual}: {repr(valor)}"
        )


def _validar_precio_positivo(precio: float, contexto: str = "") -> None:
    """Verifica que el precio sea mayor a 0."""
    if precio <= 0:
        raise ValidationError(
            f"{contexto}Campo 'precio' debe ser mayor a 0, pero recibió: {precio}"
        )


def _validar_categoria(categoria: str, contexto: str = "") -> None:
    """Verifica que la categoría sea válida."""
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(
            f"{contexto}Campo 'categoria' tiene valor inválido: '{categoria}'. "
            f"Valores permitidos: {CATEGORIAS_VALIDAS}"
        )


def _validar_iso8601(fecha: str, campo: str, contexto: str = "") -> None:
    """Verifica que una fecha esté en formato ISO 8601."""
    if not ISO8601_PATTERN.match(fecha):
        raise ValidationError(
            f"{contexto}Campo '{campo}' no está en formato ISO 8601 válido: '{fecha}'"
        )


def _validar_productor(productor: dict, contexto: str = "") -> None:
    """Valida la estructura del campo productor (opcional)."""
    if not isinstance(productor, dict):
        raise ValidationError(
            f"{contexto}Campo 'productor' debe ser un objeto, "
            f"pero recibió: {type(productor).__name__}"
        )
    
    # Productor debe tener id y nombre
    if 'id' not in productor:
        raise ValidationError(
            f"{contexto}Campo 'productor.id' es requerido"
        )
    if 'nombre' not in productor:
        raise ValidationError(
            f"{contexto}Campo 'productor.nombre' es requerido"
        )
    
    _validar_tipo(productor['id'], 'productor.id', int, contexto)
    _validar_tipo(productor['nombre'], 'productor.nombre', str, contexto)


def validar_producto(data: dict, contexto: str = "") -> dict:
    """
    Valida un producto individual de EcoMarket.
    
    Campos requeridos:
        - id (int): Identificador único
        - nombre (str): Nombre del producto
        - precio (float): Precio, debe ser > 0
        - categoria (str): Una de las categorías válidas
    
    Campos opcionales:
        - disponible (bool): Si está disponible
        - descripcion (str): Descripción del producto
        - productor (dict): {id: int, nombre: str}
        - creado_en (str): Fecha ISO 8601
    
    Args:
        data: Diccionario con los datos del producto
        contexto: Prefijo para mensajes de error (ej: "Producto[0]: ")
    
    Returns:
        dict: El mismo diccionario si pasa validación
    
    Raises:
        ValidationError: Si algún campo no cumple las reglas
    
    Ejemplo:
        >>> validar_producto({
        ...     "id": 1,
        ...     "nombre": "Manzanas Orgánicas",
        ...     "precio": 25.50,
        ...     "categoria": "frutas"
        ... })
        {'id': 1, 'nombre': 'Manzanas Orgánicas', 'precio': 25.50, 'categoria': 'frutas'}
    """
    # Verificar que sea un diccionario
    if not isinstance(data, dict):
        raise ValidationError(
            f"{contexto}Se esperaba un objeto producto, "
            f"pero recibió: {type(data).__name__}"
        )
    
    # === CAMPOS REQUERIDOS ===
    
    # id - requerido, int
    _validar_campo_requerido(data, 'id', contexto)
    _validar_tipo(data['id'], 'id', int, contexto)
    
    # nombre - requerido, str
    _validar_campo_requerido(data, 'nombre', contexto)
    _validar_tipo(data['nombre'], 'nombre', str, contexto)
    
    # precio - requerido, float/int, > 0
    _validar_campo_requerido(data, 'precio', contexto)
    _validar_tipo(data['precio'], 'precio', float, contexto)
    _validar_precio_positivo(data['precio'], contexto)
    
    # categoria - requerido, str, valor válido
    _validar_campo_requerido(data, 'categoria', contexto)
    _validar_tipo(data['categoria'], 'categoria', str, contexto)
    _validar_categoria(data['categoria'], contexto)
    
    # === CAMPOS OPCIONALES ===
    
    # disponible - opcional, bool
    if 'disponible' in data:
        _validar_tipo(data['disponible'], 'disponible', bool, contexto)
    
    # descripcion - opcional, str
    if 'descripcion' in data:
        _validar_tipo(data['descripcion'], 'descripcion', str, contexto)
    
    # productor - opcional, dict con id y nombre
    if 'productor' in data:
        _validar_productor(data['productor'], contexto)
    
    # creado_en - opcional, str ISO 8601
    if 'creado_en' in data:
        _validar_tipo(data['creado_en'], 'creado_en', str, contexto)
        _validar_iso8601(data['creado_en'], 'creado_en', contexto)
    
    return data


def validar_lista_productos(data: list) -> list:
    """
    Valida una lista de productos de EcoMarket.
    
    Args:
        data: Lista de diccionarios de productos
    
    Returns:
        list: La misma lista si todos los productos pasan validación
    
    Raises:
        ValidationError: Si data no es lista o algún producto falla validación
    
    Ejemplo:
        >>> validar_lista_productos([
        ...     {"id": 1, "nombre": "Miel", "precio": 80.0, "categoria": "miel"},
        ...     {"id": 2, "nombre": "Leche", "precio": 25.0, "categoria": "lacteos"}
        ... ])
        [{'id': 1, ...}, {'id': 2, ...}]
    """
    if not isinstance(data, list):
        raise ValidationError(
            f"Se esperaba una lista de productos, "
            f"pero recibió: {type(data).__name__}"
        )
    
    # Validar cada producto con contexto para identificar cuál falló
    for i, producto in enumerate(data):
        validar_producto(producto, contexto=f"Producto[{i}]: ")
    
    return data
