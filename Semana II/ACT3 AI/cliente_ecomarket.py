import requests
from urllib.parse import urljoin, urlencode

# Configuración centralizada
BASE_URL = "http://localhost:3000/api/"
TIMEOUT = 10  # segundos

class EcoMarketError(Exception):
    """Error base para el cliente de EcoMarket"""
    pass

class ValidationError(EcoMarketError):
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

def _verificar_respuesta(response):
    """Verifica código de estado y Content-Type antes de procesar."""
    # Capa 1: Código de estado
    if response.status_code >= 500:
        raise ServerError(f"Error del servidor: {response.status_code}")
    if response.status_code >= 400:
        raise ValidationError(f"Error de cliente: {response.status_code}")
    
    # Capa 2: Content-Type (si esperamos JSON)
    content_type = response.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        if response.status_code != 204:  # 204 no tiene body
            raise ValidationError(f"Respuesta no es JSON: {content_type}")
    
    return response

def listar_productos(categoria=None, orden=None):
    """GET /productos con filtros opcionales."""
    url = urljoin(BASE_URL, "productos")
    
    # Construir query params dinámicamente
    params = {}
    if categoria:
        params['categoria'] = categoria
    if orden:
        params['orden'] = orden
    
    response = requests.get(url, params=params, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    return response.json()  # TODO: Añadir validación de esquema

def obtener_producto(producto_id):
    """GET /productos/{id}"""
    url = urljoin(BASE_URL, f"productos/{producto_id}")
    
    response = requests.get(url, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    return response.json()

# Headers comunes para peticiones con body JSON
HEADERS_JSON = {"Content-Type": "application/json"}

def crear_producto(datos: dict) -> dict:
    """
    Crea un nuevo producto en EcoMarket.
    
    POST /productos - Envía datos como JSON en el body.
    
    Args:
        datos: Diccionario con los campos del producto.
               Campos típicos: nombre, precio, categoria, descripcion, stock
    
    Returns:
        dict: El producto creado, incluyendo el ID generado por el servidor.
    
    Raises:
        ValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si ya existe un producto con el mismo identificador (409).
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> nuevo = crear_producto({
        ...     "nombre": "Bolsa Reutilizable",
        ...     "precio": 15.99,
        ...     "categoria": "accesorios",
        ...     "stock": 100
        ... })
        >>> print(nuevo["id"])  # ID generado
        42
    """
    url = urljoin(BASE_URL, "productos")
    
    response = requests.post(
        url, 
        json=datos,  # requests serializa automáticamente a JSON
        headers=HEADERS_JSON,
        timeout=TIMEOUT
    )
    
    # Manejar caso especial: conflicto (producto duplicado)
    if response.status_code == 409:
        raise ProductoDuplicado(f"El producto ya existe o genera conflicto: {response.text}")
    
    # Verificar que sea 201 Created
    if response.status_code != 201:
        _verificar_respuesta(response)  # Lanza excepción apropiada
    
    return response.json()


def actualizar_producto_total(producto_id: int, datos: dict) -> dict:
    """
    Actualiza COMPLETAMENTE un producto existente (reemplazo total).
    
    PUT /productos/{id} - El body debe contener TODOS los campos del recurso.
    
    Args:
        producto_id: ID del producto a actualizar.
        datos: Diccionario con TODOS los campos del producto.
               Campos faltantes serán eliminados o puestos a null.
    
    Returns:
        dict: El producto actualizado.
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404).
        ValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si los datos causan conflicto (409).
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> actualizado = actualizar_producto_total(42, {
        ...     "nombre": "Bolsa Ecológica Premium",
        ...     "precio": 19.99,
        ...     "categoria": "accesorios",
        ...     "descripcion": "Bolsa 100% algodón orgánico",
        ...     "stock": 50
        ... })
        >>> print(actualizado["precio"])
        19.99
    """
    url = urljoin(BASE_URL, f"productos/{producto_id}")
    
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
    
    return response.json()


def actualizar_producto_parcial(producto_id: int, campos: dict) -> dict:
    """
    Actualiza PARCIALMENTE un producto (solo campos especificados).
    
    PATCH /productos/{id} - El body contiene SOLO los campos a modificar.
    Los campos no incluidos mantienen su valor actual.
    
    Args:
        producto_id: ID del producto a actualizar.
        campos: Diccionario con SOLO los campos a modificar.
    
    Returns:
        dict: El producto actualizado (recurso completo).
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404).
        ValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si los datos causan conflicto (409).
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> # Solo actualizar el precio, mantener otros campos
        >>> actualizado = actualizar_producto_parcial(42, {"precio": 24.99})
        >>> print(actualizado["precio"])
        24.99
        >>> # El nombre y otros campos permanecen sin cambios
    """
    url = urljoin(BASE_URL, f"productos/{producto_id}")
    
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
    
    return response.json()


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
        ValidationError: Si no se puede eliminar (400, ej: dependencias).
        ServerError: Si hay un error en el servidor (5xx).
    
    Ejemplo:
        >>> if eliminar_producto(42):
        ...     print("Producto eliminado correctamente")
        Producto eliminado correctamente
        >>> 
        >>> # Si el producto no existe:
        >>> eliminar_producto(9999)
        ProductoNoEncontrado: Producto con ID 9999 no encontrado
    """
    url = urljoin(BASE_URL, f"productos/{producto_id}")
    
    response = requests.delete(url, timeout=TIMEOUT)
    
    # Manejar caso especial: producto no existe
    if response.status_code == 404:
        raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
    
    # Verificar que sea 204 No Content
    if response.status_code != 204:
        _verificar_respuesta(response)
    
    return True