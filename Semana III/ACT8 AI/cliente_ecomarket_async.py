"""
Cliente HTTP Asíncrono para la API de EcoMarket usando aiohttp

Este módulo convierte el cliente síncrono a asíncrono para permitir:
- Ejecución paralela de múltiples peticiones
- Mejor rendimiento en operaciones I/O
- Carga concurrente de datos (dashboard)
- Creación masiva de productos con límite de concurrencia
"""

import asyncio
import aiohttp
from validadores import validar_producto, validar_lista_productos, ValidationError as SchemaValidationError
from url_builder import URLBuilder, URLSecurityError

# Configuración centralizada
BASE_URL = "http://localhost:3000/api/"
TIMEOUT = 10  # segundos

# Constructor de URLs seguro
url_builder = URLBuilder(BASE_URL)


# ============================================================
# EXCEPCIONES (mismas que el cliente síncrono)
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

class TimeoutError(EcoMarketError):
    """La petición tardó demasiado tiempo"""
    pass

class ConexionError(EcoMarketError):
    """No se pudo conectar con el servidor"""
    pass


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

async def _verificar_respuesta(response):
    """Verifica código de estado y Content-Type antes de procesar."""
    # Capa 1: Código de estado con manejo específico
    if response.status == 503:
        raise ServicioNoDisponible(f"Servicio no disponible: {response.status}")
    if response.status >= 500:
        raise ServerError(f"Error del servidor: {response.status}")
    if response.status == 401:
        raise NoAutorizado(f"No autorizado: {response.status}")
    if response.status >= 400:
        raise HTTPValidationError(f"Error de cliente: {response.status}")
    
    # Capa 2: Content-Type (si esperamos JSON)
    content_type = response.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        if response.status != 204:  # 204 no tiene body
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
# OPERACIONES DE LECTURA (GET) - VERSIONES ASÍNCRONAS
# ============================================================

# Headers comunes para peticiones con body JSON
HEADERS_JSON = {"Content-Type": "application/json"}


async def listar_productos(session: aiohttp.ClientSession, categoria=None, orden=None, timeout=None):
    """
    GET /productos con filtros opcionales (versión asíncrona).
    
    Args:
        session: ClientSession de aiohttp para reutilizar conexiones
        categoria: Filtrar por categoría (opcional)
        orden: Ordenamiento (opcional)
        timeout: Timeout en segundos (opcional, usa TIMEOUT global por defecto)
    
    Returns:
        list: Lista de productos validados
    
    Raises:
        ResponseValidationError: Si la respuesta no cumple el esquema
        TimeoutError: Si la petición tarda demasiado
        ConexionError: Si no se puede conectar con el servidor
    """
    # Construir query params dinámicamente
    params = {}
    if categoria:
        params['categoria'] = categoria
    if orden:
        params['orden'] = orden
    
    # URLBuilder construye la URL con query params escapados
    url = url_builder.build_url("productos", query_params=params if params else None)
    
    # Usar timeout proporcionado o default global
    timeout_total = timeout if timeout is not None else TIMEOUT
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_total)) as response:
            await _verificar_respuesta(response)
            data = await response.json()
            
            # Validar la lista completa antes de retornar
            return _validar_y_retornar_lista(data)
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a listar_productos tardó más de {timeout_total} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def obtener_producto(session: aiohttp.ClientSession, producto_id):
    """
    GET /productos/{id} (versión asíncrona)
    
    Args:
        session: ClientSession de aiohttp
        producto_id: ID del producto a obtener (int o UUID)
    
    Returns:
        dict: Producto validado
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404)
        ResponseValidationError: Si la respuesta no cumple el esquema
        URLSecurityException: Si el ID contiene caracteres maliciosos
        TimeoutError: Si la petición tarda demasiado
        ConexionError: Si no se puede conectar con el servidor
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
            if response.status == 404:
                raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
            
            await _verificar_respuesta(response)
            data = await response.json()
            
            # Validar el producto antes de retornar
            return _validar_y_retornar_producto(data)
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a obtener_producto({producto_id}) tardó más de {TIMEOUT} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


# ============================================================
# OPERACIONES DE ESCRITURA (POST, PUT, PATCH, DELETE)
# ============================================================

async def crear_producto(session: aiohttp.ClientSession, datos: dict) -> dict:
    """
    Crea un nuevo producto en EcoMarket (versión asíncrona).
    
    POST /productos - Envía datos como JSON en el body.
    
    Args:
        session: ClientSession de aiohttp
        datos: Diccionario con los campos del producto.
               Campos típicos: nombre, precio, categoria, descripcion
    
    Returns:
        dict: El producto creado validado, incluyendo el ID generado.
    
    Raises:
        HTTPValidationError: Si los datos son inválidos (400).
        ProductoDuplicado: Si ya existe un producto similar (409).
        ResponseValidationError: Si la respuesta no cumple el esquema.
        ServerError: Si hay un error en el servidor (5xx).
        TimeoutError: Si la petición tarda demasiado
        ConexionError: Si no se puede conectar con el servidor
    
    Ejemplo:
        >>> async with aiohttp.ClientSession() as session:
        ...     nuevo = await crear_producto(session, {
        ...         "nombre": "Manzanas Orgánicas",
        ...         "precio": 25.50,
        ...         "categoria": "frutas"
        ...     })
        ...     print(nuevo["id"])
        4
    """
    url = url_builder.build_url("productos")
    
    try:
        async with session.post(
            url, 
            json=datos,
            headers=HEADERS_JSON,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as response:
            # Manejar caso especial: conflicto (producto duplicado)
            if response.status == 409:
                text = await response.text()
                raise ProductoDuplicado(f"El producto ya existe o genera conflicto: {text}")
            
            # Verificar que sea 201 Created
            if response.status != 201:
                await _verificar_respuesta(response)
            
            data = await response.json()
            # Validar la respuesta antes de retornar
            return _validar_y_retornar_producto(data)
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a crear_producto tardó más de {TIMEOUT} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def actualizar_producto_total(session: aiohttp.ClientSession, producto_id: int, datos: dict) -> dict:
    """
    Actualiza COMPLETAMENTE un producto existente (versión asíncrona).
    
    PUT /productos/{id} - El body debe contener TODOS los campos del recurso.
    
    Args:
        session: ClientSession de aiohttp
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
        TimeoutError: Si la petición tarda demasiado
        ConexionError: Si no se puede conectar con el servidor
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    try:
        async with session.put(
            url,
            json=datos,
            headers=HEADERS_JSON,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as response:
            # Manejar casos especiales
            if response.status == 404:
                raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
            if response.status == 409:
                text = await response.text()
                raise ProductoDuplicado(f"La actualización causa conflicto: {text}")
            
            # Verificar que sea 200 OK
            if response.status != 200:
                await _verificar_respuesta(response)
            
            data = await response.json()
            # Validar la respuesta antes de retornar
            return _validar_y_retornar_producto(data)
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a actualizar_producto_total({producto_id}) tardó más de {TIMEOUT} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def actualizar_producto_parcial(session: aiohttp.ClientSession, producto_id: int, campos: dict) -> dict:
    """
    Actualiza PARCIALMENTE un producto (versión asíncrona).
    
    PATCH /productos/{id} - El body contiene SOLO los campos a modificar.
    
    Args:
        session: ClientSession de aiohttp
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
        TimeoutError: Si la petición tarda demasiado
        ConexionError: Si no se puede conectar con el servidor
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    try:
        async with session.patch(
            url,
            json=campos,
            headers=HEADERS_JSON,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        ) as response:
            # Manejar casos especiales
            if response.status == 404:
                raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
            if response.status == 409:
                text = await response.text()
                raise ProductoDuplicado(f"La actualización parcial causa conflicto: {text}")
            
            # Verificar que sea 200 OK
            if response.status != 200:
                await _verificar_respuesta(response)
            
            data = await response.json()
            # Validar la respuesta antes de retornar
            return _validar_y_retornar_producto(data)
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a actualizar_producto_parcial({producto_id}) tardó más de {TIMEOUT} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def eliminar_producto(session: aiohttp.ClientSession, producto_id: int) -> bool:
    """
    Elimina un producto de EcoMarket (versión asíncrona).
    
    DELETE /productos/{id} - Elimina el recurso permanentemente.
    
    Args:
        session: ClientSession de aiohttp
        producto_id: ID del producto a eliminar.
    
    Returns:
        bool: True si el producto fue eliminado exitosamente.
    
    Raises:
        ProductoNoEncontrado: Si el producto no existe (404).
        HTTPValidationError: Si no se puede eliminar (400).
        URLSecurityException: Si el ID contiene caracteres maliciosos.
        ServerError: Si hay un error en el servidor (5xx).
        TimeoutError: Si la petición tarda demasiado
        ConexionError: Si no se puede conectar con el servidor
    """
    try:
        url = url_builder.build_url(
            "productos/{id}",
            path_params={"id": producto_id}
        )
    except URLSecurityError as e:
        raise URLSecurityException(f"ID de producto malicioso detectado: {e}")
    
    try:
        async with session.delete(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
            # Manejar caso especial: producto no existe
            if response.status == 404:
                raise ProductoNoEncontrado(f"Producto con ID {producto_id} no encontrado")
            
            # Verificar que sea 204 No Content
            if response.status != 204:
                await _verificar_respuesta(response)
            
            return True
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a eliminar_producto({producto_id}) tardó más de {TIMEOUT} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


# ============================================================
# FUNCIONES PARALELAS (NUEVAS FUNCIONALIDADES ASYNC)
# ============================================================

async def obtener_categorias(session: aiohttp.ClientSession, timeout=None) -> list:
    """
    GET /categorias - Obtiene la lista de categorías disponibles.
    
    Esta función es simulada para demostración del dashboard.
    En una API real, este endpoint existiría.
    
    Args:
        session: ClientSession de aiohttp
        timeout: Timeout en segundos (opcional, usa TIMEOUT global por defecto)
    """
    url = url_builder.build_url("categorias")
    timeout_total = timeout if timeout is not None else TIMEOUT
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_total)) as response:
            await _verificar_respuesta(response)
            return await response.json()
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a obtener_categorias tardó más de {timeout_total} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def obtener_perfil(session: aiohttp.ClientSession, timeout=None) -> dict:
    """
    GET /perfil - Obtiene el perfil del usuario autenticado.
    
    Esta función es simulada para demostración del dashboard.
    En una API real, este endpoint existiría.
    
    Args:
        session: ClientSession de aiohttp
        timeout: Timeout en segundos (opcional, usa TIMEOUT global por defecto)
    """
    url = url_builder.build_url("perfil")
    timeout_total = timeout if timeout is not None else TIMEOUT
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_total)) as response:
            await _verificar_respuesta(response)
            return await response.json()
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"La petición a obtener_perfil tardó más de {timeout_total} segundos")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def cargar_dashboard() -> dict:
    """
    Carga todos los datos del dashboard en paralelo.
    
    Esta función demuestra las ventajas de async/await:
    - Crea UNA sola ClientSession para todas las peticiones
    - Ejecuta 3 peticiones simultáneamente (no secuenciales)
    - Usa return_exceptions=True para capturar errores sin detener otras tareas
    - Procesa resultados separando éxitos de errores
    
    Returns:
        dict: {
            "datos": {
                "productos": [...] o None,
                "categorias": [...] o None,
                "perfil": {...} o None
            },
            "errores": [
                {"endpoint": "productos", "error": "mensaje"},
                ...
            ]
        }
    
    Ejemplo:
        >>> resultado = await cargar_dashboard()
        >>> if resultado["errores"]:
        ...     print(f"Hubo {len(resultado['errores'])} errores")
        >>> else:
        ...     print(f"Todo cargado: {len(resultado['datos']['productos'])} productos")
    """
    # Crear una sola sesión para todas las peticiones
    async with aiohttp.ClientSession() as session:
        # Ejecutar las 3 peticiones en paralelo
        # return_exceptions=True hace que los errores se retornen como valores en lugar de propagarse
        resultados = await asyncio.gather(
            listar_productos(session),
            obtener_categorias(session),
            obtener_perfil(session),
            return_exceptions=True
        )
        
        # Procesar resultados
        productos_result, categorias_result, perfil_result = resultados
        
        datos = {
            "productos": None,
            "categorias": None,
            "perfil": None
        }
        errores = []
        
        # Procesar productos
        if isinstance(productos_result, Exception):
            errores.append({
                "endpoint": "productos",
                "error": str(productos_result)
            })
        else:
            datos["productos"] = productos_result
        
        # Procesar categorías
        if isinstance(categorias_result, Exception):
            errores.append({
                "endpoint": "categorias",
                "error": str(categorias_result)
            })
        else:
            datos["categorias"] = categorias_result
        
        # Procesar perfil
        if isinstance(perfil_result, Exception):
            errores.append({
                "endpoint": "perfil",
                "error": str(perfil_result)
            })
        else:
            datos["perfil"] = perfil_result
        
        return {
            "datos": datos,
            "errores": errores
        }


async def crear_multiples_productos(lista_productos: list, max_concurrencia: int = 5) -> tuple:
    """
    Crea múltiples productos en paralelo con límite de concurrencia.
    
    Esta función demuestra:
    - Control de concurrencia con asyncio.Semaphore
    - Creación masiva de recursos
    - Manejo de errores individuales sin detener el resto
    
    Args:
        lista_productos: Lista de diccionarios con datos de productos
        max_concurrencia: Máximo número de peticiones simultáneas (default: 5)
    
    Returns:
        tuple: (productos_creados, productos_fallidos)
            - productos_creados: lista de productos creados exitosamente
            - productos_fallidos: lista de dicts {"datos": {...}, "error": "..."}
    
    Ejemplo:
        >>> productos_a_crear = [
        ...     {"nombre": "Manzanas", "precio": 25.0, "categoria": "frutas"},
        ...     {"nombre": "Leche", "precio": 30.0, "categoria": "lacteos"},
        ...     {"nombre": "Miel", "precio": 80.0, "categoria": "miel"}
        ... ]
        >>> creados, fallidos = await crear_multiples_productos(productos_a_crear)
        >>> print(f"Creados: {len(creados)}, Fallidos: {len(fallidos)}")
        Creados: 3, Fallidos: 0
    """
    # Semáforo para limitar concurrencia
    semaforo = asyncio.Semaphore(max_concurrencia)
    
    async def crear_con_semaforo(session, datos_producto):
        """Función auxiliar que respeta el límite de concurrencia"""
        async with semaforo:
            try:
                producto_creado = await crear_producto(session, datos_producto)
                return {"exito": True, "producto": producto_creado}
            except Exception as e:
                return {
                    "exito": False,
                    "datos": datos_producto,
                    "error": str(e)
                }
    
    # Crear una sola sesión
    async with aiohttp.ClientSession() as session:
        # Ejecutar todas las creaciones en paralelo (respetando el semáforo)
        tareas = [crear_con_semaforo(session, datos) for datos in lista_productos]
        resultados = await asyncio.gather(*tareas)
        
        # Separar éxitos de fallos
        productos_creados = []
        productos_fallidos = []
        
        for resultado in resultados:
            if resultado["exito"]:
                productos_creados.append(resultado["producto"])
            else:
                productos_fallidos.append({
                    "datos": resultado["datos"],
                    "error": resultado["error"]
                })
        
        return productos_creados, productos_fallidos
