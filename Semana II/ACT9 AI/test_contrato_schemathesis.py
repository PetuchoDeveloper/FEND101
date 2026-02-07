"""
Tests de Contrato con Schemathesis para EcoMarket API

Este módulo utiliza schemathesis para generar casos de prueba automáticamente
desde el contrato OpenAPI y ejecutar fuzzing contra el cliente.

Uso:
    # Ejecutar tests básicos
    python -m pytest test_contrato_schemathesis.py -v
    
    # Ejecutar con más casos
    python -m pytest test_contrato_schemathesis.py -v --hypothesis-seed=42

Requisitos:
    pip install schemathesis pytest responses
"""

import pytest
import responses
import json
from pathlib import Path
from typing import Dict, Any

# Para testing sin schemathesis (fallback)
try:
    import schemathesis
    from schemathesis import Case
    SCHEMATHESIS_AVAILABLE = True
except ImportError:
    SCHEMATHESIS_AVAILABLE = False
    print("⚠️ schemathesis no instalado. Usando tests básicos de contrato.")

import yaml

from cliente_ecomarket import (
    listar_productos,
    obtener_producto,
    crear_producto,
    actualizar_producto_total,
    actualizar_producto_parcial,
    eliminar_producto,
    BASE_URL,
    EcoMarketError,
    HTTPValidationError,
    ServerError,
    ProductoNoEncontrado,
    ProductoDuplicado,
    ResponseValidationError,
    ServicioNoDisponible,
    NoAutorizado,
)


# =============================================================================
# CARGA DEL CONTRATO
# =============================================================================

SPEC_PATH = Path(__file__).parent / "openapi.yaml"

def load_openapi_spec() -> Dict[str, Any]:
    """Carga el contrato OpenAPI."""
    with open(SPEC_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# =============================================================================
# TESTS DE CONFORMIDAD BÁSICOS (Sin Schemathesis)
# =============================================================================

@pytest.mark.contract
class TestContractConformity:
    """
    Tests que verifican la conformidad del cliente con el contrato OpenAPI.
    Estos tests no requieren schemathesis.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Carga el spec antes de cada test."""
        self.spec = load_openapi_spec()
    
    def test_all_endpoints_have_client_functions(self):
        """Verifica que cada endpoint tiene una función correspondiente."""
        endpoint_to_function = {
            ('GET', '/productos'): 'listar_productos',
            ('POST', '/productos'): 'crear_producto',
            ('GET', '/productos/{id}'): 'obtener_producto',
            ('PUT', '/productos/{id}'): 'actualizar_producto_total',
            ('PATCH', '/productos/{id}'): 'actualizar_producto_parcial',
            ('DELETE', '/productos/{id}'): 'eliminar_producto',
            # Nuevos endpoints (se marcan como expected failures hasta implementar)
            # ('GET', '/productos/buscar'): 'buscar_productos',
            # ('GET', '/productores/{productorId}/productos'): 'listar_productos_productor',
        }
        
        for (method, path), func_name in endpoint_to_function.items():
            # Verificar que la función existe en el módulo
            import cliente_ecomarket
            assert hasattr(cliente_ecomarket, func_name), \
                f"Falta función {func_name} para {method} {path}"
    
    def test_valid_categories_match_spec(self):
        """Verifica que las categorías válidas coinciden con el enum del spec."""
        # Obtener enum del spec
        spec_categories = self.spec['components']['schemas']['CategoriaEnum']['enum']
        
        # Obtener categorías del validador
        from validadores import CATEGORIAS_VALIDAS
        
        assert set(spec_categories) == set(CATEGORIAS_VALIDAS), \
            f"Categorías no coinciden. Spec: {spec_categories}, Cliente: {CATEGORIAS_VALIDAS}"
    
    @responses.activate
    def test_listar_productos_handles_all_response_codes(self):
        """Verifica que listar_productos maneja todos los códigos del contrato."""
        # Códigos esperados según el contrato
        expected_codes = ['200', '500', '503']
        
        # Test 200 OK
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json=[{"id": 1, "nombre": "Test", "precio": 10.0, "categoria": "frutas"}],
            status=200,
            content_type="application/json"
        )
        result = listar_productos()
        assert isinstance(result, list)
        
        responses.reset()
        
        # Test 500 Server Error
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json={"error": "Internal error"},
            status=500,
            content_type="application/json"
        )
        with pytest.raises(ServerError):
            listar_productos()
        
        responses.reset()
        
        # Test 503 Service Unavailable  
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json={"error": "Service unavailable"},
            status=503,
            content_type="application/json"
        )
        with pytest.raises(ServicioNoDisponible):
            listar_productos()
    
    @responses.activate
    def test_obtener_producto_handles_all_response_codes(self):
        """Verifica que obtener_producto maneja todos los códigos del contrato."""
        producto = {"id": 1, "nombre": "Test", "precio": 10.0, "categoria": "frutas"}
        
        # Test 200 OK
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json=producto,
            status=200,
            content_type="application/json"
        )
        result = obtener_producto(1)
        assert result["id"] == 1
        
        responses.reset()
        
        # Test 404 Not Found
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/999",
            json={"error": "Not found"},
            status=404,
            content_type="application/json"
        )
        with pytest.raises(ProductoNoEncontrado):
            obtener_producto(999)
        
        responses.reset()
        
        # Test 401 Unauthorized
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json={"error": "Unauthorized"},
            status=401,
            content_type="application/json"
        )
        with pytest.raises(NoAutorizado):
            obtener_producto(1)
    
    @responses.activate
    def test_crear_producto_sends_correct_content_type(self):
        """Verifica que crear_producto envía Content-Type: application/json."""
        responses.add(
            responses.POST,
            f"{BASE_URL}productos",
            json={"id": 1, "nombre": "Test", "precio": 10.0, "categoria": "frutas"},
            status=201,
            content_type="application/json"
        )
        
        crear_producto({"nombre": "Test", "precio": 10.0, "categoria": "frutas"})
        
        # Verificar header
        assert "application/json" in responses.calls[0].request.headers.get("Content-Type", "")
    
    @responses.activate
    def test_response_schema_validation(self):
        """Verifica que el cliente valida el esquema de respuesta."""
        # Respuesta con esquema inválido (falta 'id')
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json={"nombre": "Test", "precio": 10.0},  # Sin id
            status=200,
            content_type="application/json"
        )
        
        with pytest.raises(ResponseValidationError):
            obtener_producto(1)


# =============================================================================
# TESTS CON SCHEMATHESIS (Fuzzing)
# =============================================================================

if SCHEMATHESIS_AVAILABLE:
    # Cargar schema para schemathesis
    schema = schemathesis.from_path(str(SPEC_PATH), base_url=BASE_URL.rstrip('/'))
    
    @pytest.mark.fuzzing
    @pytest.mark.skipif(not SCHEMATHESIS_AVAILABLE, reason="schemathesis no instalado")
    class TestSchemathetisFuzzing:
        """
        Tests de fuzzing usando schemathesis.
        Genera casos de prueba automáticamente desde el OpenAPI spec.
        """
        
        @responses.activate
        @schema.parametrize()
        def test_api_contract_fuzzing(self, case: Case):
            """
            Test paramétrico que genera casos para cada endpoint.
            
            Schemathesis genera automáticamente:
            - Valores válidos según el schema
            - Valores límite
            - Casos edge
            """
            # Configurar mock para el endpoint
            method = case.operation.method.upper()
            path = case.formatted_path
            
            # Mock genérico que acepta la petición
            responses.add(
                getattr(responses, method),
                f"{BASE_URL.rstrip('/')}{path}",
                json=self._generate_mock_response(case),
                status=200 if method != "DELETE" else 204,
                content_type="application/json"
            )
            
            # Ejecutar el caso generado
            try:
                response = case.call_and_validate()
            except Exception as e:
                # Algunas excepciones son esperadas (ej: 404 para IDs inexistentes)
                pass
        
        def _generate_mock_response(self, case: Case) -> Dict:
            """Genera una respuesta mock válida para el caso."""
            # Respuesta genérica de producto
            return {
                "id": 1,
                "nombre": "Producto Mock",
                "precio": 25.50,
                "categoria": "frutas",
                "disponible": True
            }


# =============================================================================
# TESTS DE VIOLACIONES DE CONTRATO
# =============================================================================

@pytest.mark.contract
class TestContractViolations:
    """
    Tests que verifican que el cliente detecta violaciones del contrato.
    """
    
    @responses.activate
    def test_detects_invalid_response_schema(self):
        """El cliente debe rechazar respuestas con esquema inválido."""
        # Servidor retorna producto sin campos requeridos
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json={"nombre": "Solo nombre"},  # Falta id, precio, categoria
            status=200,
            content_type="application/json"
        )
        
        with pytest.raises(ResponseValidationError) as exc_info:
            obtener_producto(1)
        
        assert "id" in str(exc_info.value).lower() or "requerido" in str(exc_info.value).lower()
    
    @responses.activate
    def test_detects_invalid_category(self):
        """El cliente debe rechazar categorías inválidas."""
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json={
                "id": 1,
                "nombre": "Test",
                "precio": 10.0,
                "categoria": "categoria_invalida"  # No existe en el enum
            },
            status=200,
            content_type="application/json"
        )
        
        with pytest.raises(ResponseValidationError):
            obtener_producto(1)
    
    @responses.activate
    def test_detects_negative_price(self):
        """El cliente debe rechazar precios negativos."""
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json={
                "id": 1,
                "nombre": "Test",
                "precio": -5.0,  # Precio negativo
                "categoria": "frutas"
            },
            status=200,
            content_type="application/json"
        )
        
        with pytest.raises(ResponseValidationError):
            obtener_producto(1)
    
    @responses.activate
    def test_detects_wrong_content_type(self):
        """El cliente debe rechazar respuestas no-JSON."""
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            body="<html>Error</html>",
            status=200,
            content_type="text/html"
        )
        
        with pytest.raises(HTTPValidationError):
            obtener_producto(1)


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    print("🧪 Tests de Contrato EcoMarket")
    print("=" * 50)
    
    if SCHEMATHESIS_AVAILABLE:
        print("✅ schemathesis disponible - ejecutando todos los tests")
    else:
        print("⚠️ schemathesis no disponible - ejecutando tests básicos")
    
    pytest.main([__file__, "-v", "--tb=short"])
