"""
Fixtures compartidos para tests del cliente async EcoMarket

Este módulo proporciona:
- Servidor mock con HTTP real (aiohttp.web)
- Datos de prueba validados
- Configuración de pytest-asyncio
"""

import pytest
import asyncio
from typing import Dict, List
import aiohttp
from mock_server import create_app, start_server, stop_server


# ============================================================
# SERVIDOR MOCK
# ============================================================

@pytest.fixture(scope="session")
async def mock_server():
    """
    Inicia un servidor mock HTTP real para toda la sesión de tests.
    
    Esto reemplaza aioresponses que tiene limitaciones para simular
    timeouts y comportamiento real de aiohttp.
    """
    runner = await start_server(host='127.0.0.1', port=3000)
    yield runner
    await stop_server(runner)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Política de event loop para pytest-asyncio"""
    return asyncio.get_event_loop_policy()


# ============================================================
# DATOS DE PRUEBA
# ============================================================

@pytest.fixture
def producto_valido() -> Dict:
    """Producto que cumple el esquema de validación."""
    return {
        "id": 1,
        "nombre": "Manzanas Orgánicas",
        "descripcion": "Manzanas frescas de producción local",
        "precio": 25.50,
        "categoria": "frutas",
        "stock": 100,
        "fecha_creacion": "2024-01-15T10:30:00Z"
    }


@pytest.fixture
def lista_productos_valida() -> List[Dict]:
    """Lista de productos que cumplen el esquema."""
    return [
        {
            "id": 1,
            "nombre": "Manzanas Orgánicas",
            "descripcion": "Manzanas frescas",
            "precio": 25.50,
            "categoria": "frutas",
            "stock": 100,
            "fecha_creacion": "2024-01-15T10:30:00Z"
        },
        {
            "id": 2,
            "nombre": "Leche Artesanal",
            "descripcion": "Leche de vaca",
            "precio": 30.00,
            "categoria": "lacteos",
            "stock": 50,
            "fecha_creacion": "2024-01-16T11:00:00Z"
        },
        {
            "id": 3,
            "nombre": "Miel de Abeja",
            "descripcion": "Miel pura",
            "precio": 80.00,
            "categoria": "miel",
            "stock": 20,
            "fecha_creacion": "2024-01-17T09:15:00Z"
        }
    ]


@pytest.fixture
def producto_invalido() -> Dict:
    """Producto que NO cumple el esquema (precio negativo)."""
    return {
        "id": 999,
        "nombre": "Producto Malicioso",
        "precio": -100,  # Precio negativo (inválido)
        "categoria": "test",
        "stock": 10
    }


@pytest.fixture
def datos_dashboard() -> Dict:
    """Datos completos de un dashboard exitoso."""
    return {
        "productos": [
            {"id": 1, "nombre": "Producto 1", "precio": 10.0, "categoria": "cat1", "stock": 5, "fecha_creacion": "2024-01-01T00:00:00Z"},
            {"id": 2, "nombre": "Producto 2", "precio": 20.0, "categoria": "cat2", "stock": 10, "fecha_creacion": "2024-01-02T00:00:00Z"}
        ],
        "categorias": ["frutas", "lacteos", "miel"],
        "perfil": {
            "id": 1,
            "nombre": "Usuario Test",
            "email": "test@ecomarket.com"
        }
    }
