"""
Cliente HTTP para la API de EcoMarket - Con Validación y URLs Seguras

Este módulo incluye:
- Validación de respuestas del servidor
- Construcción segura de URLs (previene path traversal, inyección de params)
"""

import requests
from validadores import validar_producto, validar_lista_productos, ValidationError as SchemaValidationError
from url_builder import URLBuilder, URLSecurityError

# Configuración centralizada
BASE_URL = "http://localhost:3000/api/"
TIMEOUT = 10  # segundos

# Constructor de URLs seguro (instancia global del módulo)
url_builder = URLBuilder(BASE_URL)


# ============================================================
# EXCEPCIONES
# ============================================================

class EcoMarketError(Exception):
    """Error base para el cliente de EcoMarket"""
    pass

class HTTPValidationError(EcoMarketError):
    """El servidor rechazó la petición (4xx)"""
    pass

class ServerError(EcoMarketError):
    """Error del servidor (5xx) - puede reintentarse"""
    pass

class ProductoNoEncontrado(EcoMarketError):
    """El producto solicitado no existe (404)"""
    pass

class ProductoDuplicado(EcoMarketError):
    """El producto ya existe o hay conflicto (409)"""
    pass

class ResponseValidationError(EcoMarketError):
    """La respuesta del servidor no cumple el esquema esperado"""
    pass


class URLSecurityException(EcoMarketError):
    """Se detectó un intento de ataque en los parámetros de URL"""
    pass


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _verificar_respuesta(response):
    """Verifica código de estado y Content-Type antes de procesar."""
    # Capa 1: Código de estado
    if response.status_code >= 500:
        raise ServerError(f"Error del servidor: {response.status_code}")
    if response.status_code >= 400:
        raise HTTPValidationError(f"Error de cliente: {response.status_code}")
    
    # Capa 2: Content-Type (si esperamos JSON)
    content_type = response.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        if response.status_code != 204:  # 204 no tiene body
            raise HTTPValidationError(f"Respuesta no es JSON: {content_type}")
    
    return response


def _validar_y_retornar_producto(data: dict) -> dict:
    """Valida un producto y convierte errores de esquema a ResponseValidationError."""
    try:
        return validar_producto(data)
    except SchemaValidationError as e:
        raise ResponseValidationError(f"Respuesta inválida del servidor: {e}")


def _validar_y_retornar_lista(data: list) -> list:
    """Valida una lista de productos y convierte errores de esquema."""
    try:
        return validar_lista_productos(data)
    except SchemaValidationError as e:
        raise ResponseValidationError(f"Respuesta inválida del servidor: {e}")


# ============================================================
# OPERACIONES DE LECTURA (GET)
# ============================================================

# Headers comunes para peticiones con body JSON
HEADERS_JSON = {"Content-Type": "application/json"}


def listar_productos(categoria=None, orden=None):
    """
    GET /productos con filtros opcionales.
    
    Args:
        categoria: Filtrar por categoría (opcional)
        orden: Ordenamiento (opcional)
    
    Returns:
        list: Lista de productos validados
    
    Raises:
        ResponseValidationError: Si la respuesta no cumple el esquema
    """
    # Construir query params dinámicamente
    params = {}
    if categoria:
        params['categoria'] = categoria
    if orden:
        params['orden'] = orden
    
    # URLBuilder construye la URL con query params escapados
    url = url_builder.build_url("productos", query_params=params if params else None)
    
    response = requests.get(url, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    # Validar la lista completa antes de retornar
    return _validar_y_retornar_lista(response.json())


def obtener_producto(producto_id):
    """
    GET /productos/{id}
    
    Args:
        producto_id: ID del producto a obtener (int o UUID)
    
    Returns:
        dict: Producto validado
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404)
        ResponseValidationError: Si la respuesta no cumple el esquema
        URLSecurityException: Si el ID contiene caracteres maliciosos
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    response = requests.get(url, timeout=TIMEOUT)
    
    if response.status_code == 404:
        raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
    
    _verificar_respuesta(response)
    
    # Validar el producto antes de retornar
    return _validar_y_retornar_producto(response.json())


# ============================================================
# OPERACIONES DE ESCRITURA (POST, PUT, PATCH, DELETE)
# ============================================================

def crear_producto(datos: dict) -> dict:
    """
    Crea un nuevo producto en EcoMarket.
    
    POST /productos - Envía datos como JSON en el body.
    
    Args:
        datos: Diccionario con los campos del producto.
               Campos típicos: nombre, precio, categoria, descripcion
    
    Returns:
        dict: El producto creado validado, incluyendo el ID generado.
    
    Raises:
        HTTPValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si ya existe un producto similar (409).
        ResponseValidationError: Si la respuesta no cumple el esquema.
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> nuevo = crear_producto({
        ...     "nombre": "Manzanas Orgánicas",
        ...     "precio": 25.50,
        ...     "categoria": "frutas"
        ... })
        >>> print(nuevo["id"])  # ID generado
        4
    """
    url = url_builder.build_url("productos")
    
    response = requests.post(
        url, 
        json=datos,
        headers=HEADERS_JSON,
        timeout=TIMEOUT
    )
    
    # Manejar caso especial: conflicto (producto duplicado)
    if response.status_code == 409:
        raise ProductoDuplicado(f"El producto ya existe o genera conflicto: {response.text}")
    
    # Verificar que sea 201 Created
    if response.status_code != 201:
        _verificar_respuesta(response)
    
    # Validar la respuesta antes de retornar
    return _validar_y_retornar_producto(response.json())


def actualizar_producto_total(producto_id: int, datos: dict) -> dict:
    """
    Actualiza COMPLETAMENTE un producto existente (reemplazo total).
    
    PUT /productos/{id} - El body debe contener TODOS los campos del recurso.
    
    Args:
        producto_id: ID del producto a actualizar.
        datos: Diccionario con TODOS los campos del producto.
    
    Returns:
        dict: El producto actualizado validado.
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404).
        HTTPValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si los datos causan conflicto (409).
        ResponseValidationError: Si la respuesta no cumple el esquema.
        URLSecurityException: Si el ID contiene caracteres maliciosos.
        ServerError: Si hay un error en el servidor (5xx).
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    response = requests.put(
        url,
        json=datos,
        headers=HEADERS_JSON,
        timeout=TIMEOUT
    )
    
    # Manejar casos especiales
    if response.status_code == 404:
        raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
    if response.status_code == 409:
        raise ProductoDuplicado(f"La actualización causa conflicto: {response.text}")
    
    # Verificar que sea 200 OK
    if response.status_code != 200:
        _verificar_respuesta(response)
    
    # Validar la respuesta antes de retornar
    return _validar_y_retornar_producto(response.json())


def actualizar_producto_parcial(producto_id: int, campos: dict) -> dict:
    """
    Actualiza PARCIALMENTE un producto (solo campos especificados).
    
    PATCH /productos/{id} - El body contiene SOLO los campos a modificar.
    
    Args:
        producto_id: ID del producto a actualizar.
        campos: Diccionario con SOLO los campos a modificar.
    
    Returns:
        dict: El producto actualizado validado (recurso completo).
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404).
        HTTPValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si los datos causan conflicto (409).
        ResponseValidationError: Si la respuesta no cumple el esquema.
        URLSecurityException: Si el ID contiene caracteres maliciosos.
        ServerError: Si hay un error en el servidor (5xx).
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    response = requests.patch(
        url,
        json=campos,
        headers=HEADERS_JSON,
        timeout=TIMEOUT
    )
    
    # Manejar casos especiales
    if response.status_code == 404:
        raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
    if response.status_code == 409:
        raise ProductoDuplicado(f"La actualización parcial causa conflicto: {response.text}")
    
    # Verificar que sea 200 OK
    if response.status_code != 200:
        _verificar_respuesta(response)
    
    # Validar la respuesta antes de retornar
    return _validar_y_retornar_producto(response.json())


def eliminar_producto(producto_id: int) -> bool:
    """
    Elimina un producto de EcoMarket.
    
    DELETE /productos/{id} - Elimina el recurso permanentemente.
    
    Args:
        producto_id: ID del producto a eliminar.
    
    Returns:
        bool: True si el producto fue eliminado exitosamente.
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404).
        HTTPValidationError: Si no se puede eliminar (400).
        URLSecurityException: Si el ID contiene caracteres maliciosos.
        ServerError: Si hay un error en el servidor (5xx).
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    response = requests.delete(url, timeout=TIMEOUT)
    
    # Manejar caso especial: producto no existe
    if response.status_code == 404:
        raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
    
    # Verificar que sea 204 No Content
    if response.status_code != 204:
        _verificar_respuesta(response)
    
    return True
