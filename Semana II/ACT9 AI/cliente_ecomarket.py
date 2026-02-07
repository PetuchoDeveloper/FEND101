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


class NoAutorizado(EcoMarketError):
    """No autorizado - Token faltante o inválido (401)"""
    pass


class ServicioNoDisponible(EcoMarketError):
    """Servicio temporalmente no disponible (503)"""
    pass


class ProductorNoEncontrado(EcoMarketError):
    """El productor solicitado no existe (404)"""
    pass


class BusquedaInvalida(EcoMarketError):
    """Término de búsqueda inválido (400)"""
    pass


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _verificar_respuesta(response):
    """Verifica código de estado y Content-Type antes de procesar."""
    # Capa 1: Código de estado con manejo específico
    if response.status_code == 503:
        raise ServicioNoDisponible(f"Servicio no disponible: {response.status_code}")
    if response.status_code >= 500:
        raise ServerError(f"Error del servidor: {response.status_code}")
    if response.status_code == 401:
        raise NoAutorizado(f"No autorizado: {response.status_code}")
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


# ============================================================
# NUEVAS FUNCIONALIDADES (OpenAPI Contract Expansion)
# ============================================================

def buscar_productos(query: str, limite: int = 20, categoria: str = None) -> dict:
    """
    Busca productos por texto en nombre y descripción.
    
    GET /productos/buscar - Búsqueda full-text de productos.
    
    Args:
        query: Término de búsqueda (mínimo 2 caracteres)
        limite: Número máximo de resultados (1-100, default: 20)
        categoria: Filtrar búsqueda por categoría (opcional)
    
    Returns:
        dict: Objeto con 'total' y 'resultados' (lista de productos con relevancia)
    
    Raises:
        BusquedaInvalida: Si el término de búsqueda es inválido (400).
        ResponseValidationError: Si la respuesta no cumple el esquema.
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> resultado = buscar_productos("manzana", limite=10)
        >>> print(resultado["total"])
        3
        >>> print(resultado["resultados"][0]["nombre"])
        'Manzanas Orgánicas'
    """
    # Validar query localmente
    if not query or len(query) < 2:
        raise BusquedaInvalida("El término de búsqueda debe tener al menos 2 caracteres")
    
    if limite < 1 or limite > 100:
        raise BusquedaInvalida("El límite debe estar entre 1 y 100")
    
    # Construir query params
    params = {
        'q': query,
        'limite': limite
    }
    if categoria:
        params['categoria'] = categoria
    
    url = url_builder.build_url("productos/buscar", query_params=params)
    
    response = requests.get(url, timeout=TIMEOUT)
    
    # Manejar caso especial: query inválida
    if response.status_code == 400:
        error_msg = "Búsqueda inválida"
        try:
            error_msg = response.json().get('error', error_msg)
        except Exception:
            pass
        raise BusquedaInvalida(error_msg)
    
    _verificar_respuesta(response)
    
    # Validar estructura de respuesta
    data = response.json()
    if not isinstance(data, dict):
        raise ResponseValidationError("Respuesta de búsqueda debe ser un objeto")
    if 'total' not in data or 'resultados' not in data:
        raise ResponseValidationError("Respuesta debe contener 'total' y 'resultados'")
    if not isinstance(data['resultados'], list):
        raise ResponseValidationError("'resultados' debe ser una lista")
    
    # Validar cada producto en resultados (pueden tener campos extra como 'relevancia')
    for i, producto in enumerate(data['resultados']):
        try:
            # Validar campos base del producto
            validar_producto(producto, contexto=f"Resultado[{i}]: ")
        except SchemaValidationError as e:
            raise ResponseValidationError(f"Respuesta inválida del servidor: {e}")
    
    return data


def listar_productos_productor(productor_id: int, disponibles_solo: bool = False) -> dict:
    """
    Lista todos los productos de un productor específico.
    
    GET /productores/{productorId}/productos - Catálogo de un proveedor.
    
    Args:
        productor_id: ID del productor
        disponibles_solo: Si True, solo retorna productos disponibles
    
    Returns:
        dict: Objeto con 'productor', 'productos' y 'total_productos'
    
    Raises:
        ProductorNoEncontrado: Si el productor no existe (404).
        ResponseValidationError: Si la respuesta no cumple el esquema.
        URLSecurityException: Si el ID contiene caracteres maliciosos.
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> resultado = listar_productos_productor(101)
        >>> print(resultado["productor"]["nombre"])
        'Granja El Valle'
        >>> print(resultado["total_productos"])
        12
    """
    try:
        url = url_builder.build_url(
            "productores/{productorId}/productos",
            path_params={"productorId": productor_id},
            query_params={"disponibles_solo": str(disponibles_solo).lower()} if disponibles_solo else None
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de productor malicioso detectado: {e}")
    
    response = requests.get(url, timeout=TIMEOUT)
    
    # Manejar caso especial: productor no encontrado
    if response.status_code == 404:
        raise ProductorNoEncontrado(f"Productor con ID {productor_id} no encontrado")
    
    _verificar_respuesta(response)
    
    # Validar estructura de respuesta
    data = response.json()
    if not isinstance(data, dict):
        raise ResponseValidationError("Respuesta debe ser un objeto")
    
    required_fields = ['productor', 'productos', 'total_productos']
    for field in required_fields:
        if field not in data:
            raise ResponseValidationError(f"Campo requerido '{field}' no encontrado")
    
    # Validar productor
    productor = data['productor']
    if not isinstance(productor, dict):
        raise ResponseValidationError("'productor' debe ser un objeto")
    if 'id' not in productor or 'nombre' not in productor:
        raise ResponseValidationError("'productor' debe tener 'id' y 'nombre'")
    
    # Validar lista de productos
    if not isinstance(data['productos'], list):
        raise ResponseValidationError("'productos' debe ser una lista")
    
    for i, producto in enumerate(data['productos']):
        try:
            validar_producto(producto, contexto=f"Producto[{i}]: ")
        except SchemaValidationError as e:
            raise ResponseValidationError(f"Respuesta inválida del servidor: {e}")
    
    return data
