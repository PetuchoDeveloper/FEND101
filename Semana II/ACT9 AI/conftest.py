"""
Configuración compartida de pytest para la suite de pruebas de EcoMarket.

Este archivo contiene:
- Fixtures compartidas entre todos los tests
- Configuración de markers personalizados
- Helpers de testing reutilizables
"""

import pytest
import responses


# =============================================================================
# DATOS DE PRUEBA COMUNES
# =============================================================================

PRODUCTO_VALIDO_MINIMO = {
    "id": 1,
    "nombre": "Producto Test",
    "precio": 10.00,
    "categoria": "frutas"
}

PRODUCTO_COMPLETO = {
    "id": 1,
    "nombre": "Manzanas Orgánicas Premium",
    "precio": 25.50,
    "categoria": "frutas",
    "disponible": True,
    "descripcion": "Manzanas rojas de producción local, libres de pesticidas",
    "productor": {
        "id": 101,
        "nombre": "Granja El Valle"
    },
    "creado_en": "2024-01-15T10:30:00Z"
}


# =============================================================================
# FIXTURES GLOBALES
# =============================================================================

@pytest.fixture
def producto_minimo():
    """Producto con solo campos requeridos (id, nombre, precio, categoria)."""
    return PRODUCTO_VALIDO_MINIMO.copy()


@pytest.fixture
def producto_completo():
    """Producto con todos los campos opcionales poblados."""
    return PRODUCTO_COMPLETO.copy()


@pytest.fixture
def lista_productos_variada():
    """Lista con productos de diferentes categorías."""
    return [
        {"id": 1, "nombre": "Manzanas", "precio": 25.50, "categoria": "frutas"},
        {"id": 2, "nombre": "Leche Entera", "precio": 18.00, "categoria": "lacteos"},
        {"id": 3, "nombre": "Zanahorias Bio", "precio": 12.00, "categoria": "verduras"},
        {"id": 4, "nombre": "Miel Silvestre", "precio": 95.00, "categoria": "miel"},
        {"id": 5, "nombre": "Mermelada Casera", "precio": 45.00, "categoria": "conservas"}
    ]


@pytest.fixture
def mock_api():
    """
    Fixture que activa el contexto de responses automáticamente.
    Uso: No necesitas @responses.activate en el test.
    """
    with responses.RequestsMock() as rsps:
        yield rsps


# =============================================================================
# MARKERS PERSONALIZADOS
# =============================================================================

def pytest_configure(config):
    """Registra markers personalizados para categorizar tests."""
    config.addinivalue_line(
        "markers", "happy_path: Tests de operaciones exitosas"
    )
    config.addinivalue_line(
        "markers", "error_http: Tests de manejo de errores HTTP"
    )
    config.addinivalue_line(
        "markers", "edge_case: Tests de casos límite y respuestas anómalas"
    )
    config.addinivalue_line(
        "markers", "slow: Tests que pueden tardar más de lo normal"
    )
    config.addinivalue_line(
        "markers", "security: Tests relacionados con seguridad (URL injection, etc.)"
    )


# =============================================================================
# HELPERS DE TESTING
# =============================================================================

def crear_respuesta_producto(id: int, **kwargs) -> dict:
    """
    Helper para crear un producto de prueba con valores customizables.
    
    Args:
        id: ID del producto
        **kwargs: Campos opcionales a sobrescribir
    
    Returns:
        dict: Producto con valores por defecto + customizaciones
    """
    producto = {
        "id": id,
        "nombre": kwargs.get("nombre", f"Producto {id}"),
        "precio": kwargs.get("precio", 10.00 * id),
        "categoria": kwargs.get("categoria", "frutas"),
    }
    
    # Añadir campos opcionales si se proporcionan
    for campo in ["disponible", "descripcion", "productor", "creado_en"]:
        if campo in kwargs:
            producto[campo] = kwargs[campo]
    
    return producto


def crear_lista_productos(cantidad: int, categoria: str = "frutas") -> list:
    """
    Helper para generar una lista de productos de prueba.
    
    Args:
        cantidad: Número de productos a generar
        categoria: Categoría para todos los productos
    
    Returns:
        list: Lista de productos
    """
    return [
        crear_respuesta_producto(i + 1, categoria=categoria)
        for i in range(cantidad)
    ]
