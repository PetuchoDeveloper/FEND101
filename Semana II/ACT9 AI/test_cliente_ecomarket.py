"""
Suite de Pruebas Exhaustiva para Cliente HTTP EcoMarket

Este módulo contiene tests usando pytest y responses para mockear HTTP.
Cubre escenarios organizados en:
- Happy Path (6 tests): Operaciones exitosas
- Errores HTTP (8 tests): Códigos de error del servidor
- Edge Cases (6 tests): Casos límite y respuestas anómalas
- Seguridad (2 tests): Prevención de inyección de URLs

Ejecutar todos los tests:
    pytest test_cliente_ecomarket.py -v

Ejecutar por categoría:
    pytest -m happy_path
    pytest -m error_http
    pytest -m edge_case
    pytest -m security
"""

import pytest
import responses
import requests
from unittest.mock import patch

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
    URLSecurityException,
    NoAutorizado,
    ServicioNoDisponible,
)


# =============================================================================
# FIXTURES Y DATOS DE PRUEBA
# =============================================================================

@pytest.fixture
def producto_valido():
    """Fixture: Producto con todos los campos requeridos válidos."""
    return {
        "id": 1,
        "nombre": "Manzanas Orgánicas",
        "precio": 25.50,
        "categoria": "frutas",
        "disponible": True,
        "descripcion": "Manzanas frescas de producción local"
    }


@pytest.fixture
def producto_creado():
    """Fixture: Producto recién creado por el servidor (con ID generado)."""
    return {
        "id": 42,
        "nombre": "Miel de Abeja",
        "precio": 80.00,
        "categoria": "miel",
        "disponible": True
    }


@pytest.fixture
def lista_productos():
    """Fixture: Lista de productos para mock de listar."""
    return [
        {"id": 1, "nombre": "Manzanas", "precio": 25.50, "categoria": "frutas"},
        {"id": 2, "nombre": "Leche", "precio": 18.00, "categoria": "lacteos"},
        {"id": 3, "nombre": "Zanahorias", "precio": 12.00, "categoria": "verduras"}
    ]


# =============================================================================
# HAPPY PATH TESTS (6 tests)
# =============================================================================

@pytest.mark.happy_path
class TestHappyPath:
    """
    Tests de camino feliz: Todas las operaciones CRUD con datos válidos.
    Cada test verifica que la función retorna correctamente cuando el 
    servidor responde con éxito.
    """

    @responses.activate
    def test_listar_productos_con_filtros_retorna_lista(self, lista_productos):
        """
        Escenario: GET /productos con parámetros de filtro y ordenamiento.
        Verifica que listar_productos envía correctamente los query params
        y retorna la lista de productos del servidor.
        """
        # Setup del mock: Respuesta exitosa con lista de productos
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json=lista_productos,
            status=200,
            content_type="application/json"
        )
        
        # Ejecución
        resultado = listar_productos(categoria="frutas", orden="asc")
        
        # Aserciones
        assert isinstance(resultado, list)
        assert len(resultado) == 3
        assert resultado[0]["nombre"] == "Manzanas"
        # Verificar que se enviaron los query params
        assert "categoria=frutas" in responses.calls[0].request.url

    @responses.activate
    def test_obtener_producto_existente_retorna_producto(self, producto_valido):
        """
        Escenario: GET /productos/{id} para un producto que existe.
        Verifica que obtener_producto retorna el producto correcto.
        """
        # Setup del mock
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json=producto_valido,
            status=200,
            content_type="application/json"
        )
        
        # Ejecución
        resultado = obtener_producto(1)
        
        # Aserciones
        assert resultado["id"] == 1
        assert resultado["nombre"] == "Manzanas Orgánicas"
        assert resultado["precio"] == 25.50

    @responses.activate
    def test_crear_producto_valido_retorna_producto_creado(self, producto_creado):
        """
        Escenario: POST /productos con datos válidos.
        Verifica que crear_producto envía el JSON correctamente y
        retorna el producto creado con su ID generado.
        """
        # Setup del mock: 201 Created con el producto incluyendo ID
        responses.add(
            responses.POST,
            f"{BASE_URL}productos",
            json=producto_creado,
            status=201,
            content_type="application/json"
        )
        
        # Datos a enviar (sin ID, el servidor lo genera)
        datos_nuevo = {
            "nombre": "Miel de Abeja",
            "precio": 80.00,
            "categoria": "miel"
        }
        
        # Ejecución
        resultado = crear_producto(datos_nuevo)
        
        # Aserciones
        assert resultado["id"] == 42  # ID generado por el servidor
        assert resultado["nombre"] == "Miel de Abeja"

    @responses.activate
    def test_actualizar_producto_total_retorna_producto_actualizado(self, producto_valido):
        """
        Escenario: PUT /productos/{id} con todos los campos del producto.
        Verifica que actualizar_producto_total envía el body completo
        y retorna el producto actualizado.
        """
        producto_actualizado = producto_valido.copy()
        producto_actualizado["precio"] = 30.00
        
        # Setup del mock
        responses.add(
            responses.PUT,
            f"{BASE_URL}productos/1",
            json=producto_actualizado,
            status=200,
            content_type="application/json"
        )
        
        # Ejecución
        resultado = actualizar_producto_total(1, producto_actualizado)
        
        # Aserciones
        assert resultado["precio"] == 30.00
        assert resultado["id"] == 1

    @responses.activate
    def test_actualizar_producto_parcial_retorna_producto_modificado(self, producto_valido):
        """
        Escenario: PATCH /productos/{id} con solo algunos campos.
        Verifica que actualizar_producto_parcial envía solo los campos
        especificados y retorna el producto completo actualizado.
        """
        producto_modificado = producto_valido.copy()
        producto_modificado["disponible"] = False
        
        # Setup del mock
        responses.add(
            responses.PATCH,
            f"{BASE_URL}productos/1",
            json=producto_modificado,
            status=200,
            content_type="application/json"
        )
        
        # Ejecución: Solo cambiar disponibilidad
        resultado = actualizar_producto_parcial(1, {"disponible": False})
        
        # Aserciones
        assert resultado["disponible"] is False
        assert resultado["nombre"] == "Manzanas Orgánicas"  # Campos no modificados persisten

    @responses.activate
    def test_eliminar_producto_existente_retorna_true(self):
        """
        Escenario: DELETE /productos/{id} para un producto existente.
        Verifica que eliminar_producto retorna True cuando el servidor
        responde con 204 No Content.
        """
        # Setup del mock: 204 sin body
        responses.add(
            responses.DELETE,
            f"{BASE_URL}productos/1",
            status=204
        )
        
        # Ejecución
        resultado = eliminar_producto(1)
        
        # Aserciones
        assert resultado is True


# =============================================================================
# ERRORES HTTP TESTS (8 tests)
# =============================================================================

@pytest.mark.error_http
class TestErroresHTTP:
    """
    Tests de errores HTTP: Verifican que el cliente maneja correctamente
    los códigos de error del servidor (4xx y 5xx).
    """

    @responses.activate
    def test_crear_producto_con_datos_invalidos_retorna_400(self):
        """
        Escenario: POST /productos con datos que el servidor rechaza.
        El servidor retorna 400 Bad Request cuando los datos no cumplen
        las reglas de validación del backend.
        """
        # Setup del mock: 400 con mensaje de error
        responses.add(
            responses.POST,
            f"{BASE_URL}productos",
            json={"error": "El campo 'nombre' es requerido"},
            status=400,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(HTTPValidationError) as exc_info:
            crear_producto({"precio": -10})  # Datos incompletos/inválidos
        
        assert "400" in str(exc_info.value)

    @responses.activate
    def test_obtener_producto_sin_token_retorna_401(self):
        """
        Escenario: GET /productos/{id} sin autenticación válida.
        El servidor retorna 401 Unauthorized cuando falta el token
        o las credenciales son inválidas.
        """
        # Setup del mock
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            json={"error": "Token no proporcionado"},
            status=401,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(NoAutorizado) as exc_info:
            obtener_producto(1)
        
        assert "401" in str(exc_info.value)

    @responses.activate
    def test_obtener_producto_inexistente_retorna_404(self):
        """
        Escenario: GET /productos/{id} para un ID que no existe.
        Verifica que se lanza ProductoNoEncontrado con mensaje descriptivo.
        """
        # Setup del mock
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/9999",
            json={"error": "Producto no encontrado"},
            status=404,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(ProductoNoEncontrado) as exc_info:
            obtener_producto(9999)
        
        assert "9999" in str(exc_info.value)

    @responses.activate
    def test_actualizar_producto_total_inexistente_retorna_404(self):
        """
        Escenario: PUT /productos/{id} para un producto que no existe.
        El servidor retorna 404 al intentar actualizar un recurso inexistente.
        """
        # Setup del mock
        responses.add(
            responses.PUT,
            f"{BASE_URL}productos/9999",
            json={"error": "Producto no encontrado"},
            status=404,
            content_type="application/json"
        )
        
        datos = {"id": 9999, "nombre": "Test", "precio": 10.0, "categoria": "frutas"}
        
        # Ejecución y aserción
        with pytest.raises(ProductoNoEncontrado):
            actualizar_producto_total(9999, datos)

    @responses.activate
    def test_actualizar_producto_parcial_inexistente_retorna_404(self):
        """
        Escenario: PATCH /productos/{id} para un producto que no existe.
        Similar al PUT, pero para actualización parcial.
        """
        # Setup del mock
        responses.add(
            responses.PATCH,
            f"{BASE_URL}productos/9999",
            json={"error": "Producto no encontrado"},
            status=404,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(ProductoNoEncontrado):
            actualizar_producto_parcial(9999, {"precio": 15.0})

    @responses.activate
    def test_eliminar_producto_inexistente_retorna_404(self):
        """
        Escenario: DELETE /productos/{id} para un producto que no existe.
        Verifica que ProductoNoEncontrado se lanza correctamente.
        """
        # Setup del mock
        responses.add(
            responses.DELETE,
            f"{BASE_URL}productos/9999",
            json={"error": "Producto no encontrado"},
            status=404,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(ProductoNoEncontrado):
            eliminar_producto(9999)

    @responses.activate
    def test_crear_producto_duplicado_retorna_409(self):
        """
        Escenario: POST /productos con un producto que ya existe.
        El servidor retorna 409 Conflict cuando se intenta crear un
        producto que causaría duplicación (ej: mismo nombre).
        """
        # Setup del mock
        responses.add(
            responses.POST,
            f"{BASE_URL}productos",
            json={"error": "Ya existe un producto con ese nombre"},
            status=409,
            content_type="application/json"
        )
        
        datos = {"nombre": "Manzanas", "precio": 25.0, "categoria": "frutas"}
        
        # Ejecución y aserción
        with pytest.raises(ProductoDuplicado) as exc_info:
            crear_producto(datos)
        
        assert "existe" in str(exc_info.value).lower() or "conflicto" in str(exc_info.value).lower()

    @responses.activate
    def test_operacion_con_error_servidor_retorna_500(self):
        """
        Escenario: El servidor tiene un error interno.
        Verifica que ServerError se lanza para códigos 5xx, permitiendo
        que el cliente maneje reintentos si lo desea.
        """
        # Setup del mock
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json={"error": "Internal Server Error"},
            status=500,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(ServerError) as exc_info:
            listar_productos()
        
        assert "500" in str(exc_info.value)


# =============================================================================
# EDGE CASES TESTS (6 tests)
# =============================================================================

@pytest.mark.edge_case
class TestEdgeCases:
    """
    Tests de casos límite: Respuestas válidas pero inusuales,
    errores de red, y datos con tipos incorrectos.
    """

    @responses.activate
    def test_listar_productos_respuesta_vacia_retorna_lista_vacia(self):
        """
        Escenario: GET /productos retorna un array vacío [].
        Es una respuesta válida (status 200, JSON correcto) pero sin productos.
        El cliente debe retornar una lista vacía sin error.
        """
        # Setup del mock: Array vacío es válido
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json=[],
            status=200,
            content_type="application/json"
        )
        
        # Ejecución
        resultado = listar_productos()
        
        # Aserciones
        assert resultado == []
        assert isinstance(resultado, list)

    @responses.activate
    def test_obtener_producto_content_type_html_lanza_error(self):
        """
        Escenario: El servidor retorna HTML en lugar de JSON.
        Esto puede ocurrir si hay un proxy mal configurado, página de error
        del servidor web, o un redirect a una página de login.
        """
        # Setup del mock: Content-Type text/html
        responses.add(
            responses.GET,
            f"{BASE_URL}productos/1",
            body="<html><body>Error</body></html>",
            status=200,
            content_type="text/html"
        )
        
        # Ejecución y aserción
        with pytest.raises(HTTPValidationError) as exc_info:
            obtener_producto(1)
        
        assert "JSON" in str(exc_info.value) or "text/html" in str(exc_info.value)

    @responses.activate
    def test_crear_producto_estructura_json_incorrecta_lanza_error(self):
        """
        Escenario: El servidor retorna JSON válido pero con estructura incorrecta.
        Por ejemplo, retorna un objeto sin los campos requeridos (id, nombre, etc.)
        La validación de esquema debe detectar esto.
        """
        # Setup del mock: JSON válido pero estructura incorrecta
        responses.add(
            responses.POST,
            f"{BASE_URL}productos",
            json={"mensaje": "Producto creado", "timestamp": "2024-01-01"},
            status=201,
            content_type="application/json"
        )
        
        datos = {"nombre": "Test", "precio": 10.0, "categoria": "frutas"}
        
        # Ejecución y aserción: Debe fallar la validación del esquema
        with pytest.raises(ResponseValidationError) as exc_info:
            crear_producto(datos)
        
        # El error debe mencionar campos faltantes
        assert "id" in str(exc_info.value).lower() or "requerido" in str(exc_info.value).lower()

    @responses.activate
    def test_obtener_producto_timeout_lanza_excepcion(self):
        """
        Escenario: El servidor no responde a tiempo (timeout).
        Simula una situación donde el servidor está sobrecargado o hay
        problemas de red. El cliente debe propagar la excepción de timeout.
        """
        # Setup del mock: Simular timeout usando callback
        def timeout_callback(request):
            raise requests.exceptions.Timeout("Connection timed out")
        
        responses.add_callback(
            responses.GET,
            f"{BASE_URL}productos/1",
            callback=timeout_callback
        )
        
        # Ejecución y aserción
        with pytest.raises(requests.exceptions.Timeout):
            obtener_producto(1)

    @responses.activate
    def test_crear_producto_precio_como_string_lanza_error(self):
        """
        Escenario: El servidor retorna el precio como string en lugar de número.
        Este es un error común de serialización. La validación de tipos
        debe detectar que "25.50" (string) no es un número válido.
        """
        # Setup del mock: precio como string (tipo incorrecto)
        producto_con_error = {
            "id": 1,
            "nombre": "Test",
            "precio": "25.50",  # ¡String en lugar de float!
            "categoria": "frutas"
        }
        
        responses.add(
            responses.POST,
            f"{BASE_URL}productos",
            json=producto_con_error,
            status=201,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(ResponseValidationError) as exc_info:
            crear_producto({"nombre": "Test", "precio": 25.50, "categoria": "frutas"})
        
        assert "precio" in str(exc_info.value).lower()

    @responses.activate
    def test_servicio_no_disponible_retorna_503(self):
        """
        Escenario: El servicio está temporalmente no disponible.
        503 Service Unavailable indica que el servidor está sobrecargado
        o en mantenimiento. El cliente debe lanzar ServerError.
        """
        # Setup del mock
        responses.add(
            responses.GET,
            f"{BASE_URL}productos",
            json={"error": "Service temporarily unavailable"},
            status=503,
            content_type="application/json"
        )
        
        # Ejecución y aserción
        with pytest.raises(ServicioNoDisponible) as exc_info:
            listar_productos()
        
        assert "503" in str(exc_info.value)


# =============================================================================
# SECURITY TESTS (2 tests)
# =============================================================================

@pytest.mark.security
class TestSeguridad:
    """
    Tests de seguridad: Verifican que el cliente previene ataques comunes
    como path traversal e inyección de parámetros en URLs.
    """

    def test_obtener_producto_con_path_traversal_lanza_error_seguridad(self):
        """
        Escenario: Un atacante intenta usar path traversal en el ID.
        El ID "../../../etc/passwd" podría permitir acceder a archivos del sistema
        si el servidor no valida correctamente. El cliente debe prevenir esto.
        """
        # Ejecución y aserción: No debe hacer la petición, debe fallar antes
        with pytest.raises(URLSecurityException) as exc_info:
            obtener_producto("../../../etc/passwd")
        
        # El error debe mencionar path traversal o seguridad
        error_msg = str(exc_info.value).lower()
        assert "malicioso" in error_msg or "traversal" in error_msg

    @responses.activate
    def test_actualizar_producto_con_inyeccion_query_params_escapa_correctamente(self):
        """
        Escenario: Un atacante intenta inyectar query params en el ID.
        El ID "1?admin=true&delete=all" podría añadir parámetros maliciosos.
        El URLBuilder debe escapar los caracteres especiales (? -> %3F).
        Verificamos que la URL resultante está correctamente escapada.
        """
        # Setup: El URLBuilder escapa ? a %3F, entonces la URL resultante es segura
        # pero la petición aún se hace (con caracteres escapados)
        producto = {
            "id": 1,
            "nombre": "Test",
            "precio": 10.0,
            "categoria": "frutas"
        }
        
        # Mock para la URL con caracteres escapados
        # El ? se convierte en %3F, por lo que no hay inyección
        responses.add(
            responses.GET,
            # URL con el ? escapado como %3F
            f"{BASE_URL}productos/1%3Fadmin%3Dtrue",
            json=producto,
            status=200,
            content_type="application/json"
        )
        
        # Esta llamada debería funcionar porque el URLBuilder escapa correctamente
        # El servidor recibiría "1?admin=true" como parte del path, no como query params
        resultado = obtener_producto("1?admin=true")
        
        # Verificar que la petición se hizo con la URL escapada
        assert "%3F" in responses.calls[0].request.url
        assert "?admin=true" not in responses.calls[0].request.url  # ? literales NO deben aparecer


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
