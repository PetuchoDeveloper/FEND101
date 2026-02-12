"""
Cliente HTTP Asíncrono con Control de Flujo Avanzado para EcoMarket

Este módulo extiende el cliente asíncrono básico con:
1. Timeout individual por petición (configurable por función)
2. Cancelación granular de tareas en grupo
3. Carga con prioridad usando asyncio.wait()
"""

import asyncio
import aiohttp
from typing import Any, Dict, List, Tuple, Optional, Set
from validadores import validar_producto, validar_lista_productos, ValidationError as SchemaValidationError
from url_builder import URLBuilder, URLSecurityError

# Configuración centralizada
BASE_URL = "http://localhost:3000/api/"
DEFAULT_TIMEOUT = 10  # segundos

# Constructor de URLs seguro
url_builder = URLBuilder(BASE_URL)

# Headers comunes para peticiones con body JSON
HEADERS_JSON = {"Content-Type": "application/json"}


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

class NoAutorizado(EcoMarketError):
    """No autorizado - Token faltante o inválido (401)"""
    pass

class ServicioNoDisponible(EcoMarketError):
    """Servicio temporalmente no disponible (503)"""
    pass

class TimeoutError(EcoMarketError):
    """La petición tardó demasiado tiempo"""
    pass

class ConexionError(EcoMarketError):
    """No se pudo conectar con el servidor"""
    pass

class ResponseValidationError(EcoMarketError):
    """La respuesta del servidor no cumple el esquema esperado"""
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
# FEATURE 1: TIMEOUT INDIVIDUAL POR PETICIÓN
# ============================================================

async def ejecutar_con_timeout(
    coroutine, 
    timeout_segundos: float,
    nombre_operacion: str = "operación"
) -> Any:
    """
    Wrapper que envuelve cualquier petición con asyncio.wait_for().
    
    Si una petición excede SU timeout, las demás continúan normalmente.
    
    Args:
        coroutine: Corutina a ejecutar
        timeout_segundos: Tiempo máximo en segundos
        nombre_operacion: Nombre descriptivo para mensajes de error
        
    Returns:
        Any: Resultado de la corutina
        
    Raises:
        TimeoutError: Si la operación excede el timeout
        
    Ejemplo:
        >>> async with aiohttp.ClientSession() as session:
        ...     productos = await ejecutar_con_timeout(
        ...         listar_productos(session),
        ...         timeout_segundos=5.0,
        ...         nombre_operacion="listar_productos"
        ...     )
    """
    try:
        return await asyncio.wait_for(coroutine, timeout=timeout_segundos)
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"La operación '{nombre_operacion}' excedió el timeout de {timeout_segundos}s"
        )


# ============================================================
# OPERACIONES BÁSICAS (CON TIMEOUT CONFIGURABLE)
# ============================================================

async def listar_productos(
    session: aiohttp.ClientSession, 
    categoria=None, 
    orden=None,
    timeout: float = DEFAULT_TIMEOUT
) -> list:
    """
    GET /productos con filtros opcionales y timeout configurable.
    
    Args:
        session: ClientSession de aiohttp
        categoria: Filtrar por categoría (opcional)
        orden: Ordenamiento (opcional)
        timeout: Timeout en segundos para esta petición específica
        
    Returns:
        list: Lista de productos validados
    """
    params = {}
    if categoria:
        params['categoria'] = categoria
    if orden:
        params['orden'] = orden
    
    url = url_builder.build_url("productos", query_params=params if params else None)
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            await _verificar_respuesta(response)
            data = await response.json()
            return _validar_y_retornar_lista(data)
    
    except aiohttp.ClientTimeout:
        raise TimeoutError(f"listar_productos tardó más de {timeout}s")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def obtener_categorias(session: aiohttp.ClientSession, timeout: float = DEFAULT_TIMEOUT) -> list:
    """
    GET /categorias - Obtiene la lista de categorías disponibles.
    
    Args:
        session: ClientSession de aiohttp
        timeout: Timeout en segundos para esta petición específica
    """
    url = url_builder.build_url("categorias")
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            await _verificar_respuesta(response)
            return await response.json()
    
    except aiohttp.ClientTimeout:
        raise TimeoutError(f"obtener_categorias tardó más de {timeout}s")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def obtener_perfil(session: aiohttp.ClientSession, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """
    GET /perfil - Obtiene el perfil del usuario autenticado.
    
    Args:
        session: ClientSession de aiohttp
        timeout: Timeout en segundos para esta petición específica
    """
    url = url_builder.build_url("perfil")
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            await _verificar_respuesta(response)
            return await response.json()
    
    except aiohttp.ClientTimeout:
        raise TimeoutError(f"obtener_perfil tardó más de {timeout}s")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


async def obtener_notificaciones(session: aiohttp.ClientSession, timeout: float = DEFAULT_TIMEOUT) -> list:
    """
    GET /notificaciones - Obtiene las notificaciones del usuario.
    
    Args:
        session: ClientSession de aiohttp
        timeout: Timeout en segundos para esta petición específica
    """
    url = url_builder.build_url("notificaciones")
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            await _verificar_respuesta(response)
            return await response.json()
    
    except aiohttp.ClientTimeout:
        raise TimeoutError(f"obtener_notificaciones tardó más de {timeout}s")
    except aiohttp.ClientConnectorError as e:
        raise ConexionError(f"No se pudo conectar con el servidor: {e}")
    except asyncio.CancelledError:
        raise EcoMarketError("La tarea fue cancelada")


# ============================================================
# FEATURE 2: CANCELACIÓN DE TAREAS EN GRUPO
# ============================================================

def cancel_remaining(tareas: Set[asyncio.Task]) -> int:
    """
    Cancela todas las tareas pendientes del conjunto.
    
    Args:
        tareas: Conjunto de tareas asyncio.Task
        
    Returns:
        int: Número de tareas canceladas
        
    Ejemplo:
        >>> tareas_pendientes = {tarea1, tarea2, tarea3}
        >>> canceladas = cancel_remaining(tareas_pendientes)
        >>> print(f"Se cancelaron {canceladas} tareas")
    """
    canceladas = 0
    for tarea in tareas:
        if not tarea.done():
            tarea.cancel()
            canceladas += 1
    return canceladas


async def cargar_dashboard_con_cancelacion() -> dict:
    """
    Carga el dashboard con cancelación condicional.
    
    ESCENARIO: Si obtener_perfil falla con 401 (no autorizado), 
    cancela las demás peticiones (no tiene sentido continuar sin autenticación).
    
    Returns:
        dict: {
            "datos": {
                "productos": [...] o None,
                "categorias": [...] o None,
                "perfil": {...} o None
            },
            "errores": [{"endpoint": str, "error": str, "cancelada": bool}, ...],
            "canceladas_por_auth": bool
        }
        
    Ejemplo:
        >>> resultado = await cargar_dashboard_con_cancelacion()
        >>> if resultado["canceladas_por_auth"]:
        ...     print("Dashboard cancelado por falta de autenticación")
    """
    async with aiohttp.ClientSession() as session:
        # Crear tareas con timeouts específicos
        tarea_productos = asyncio.create_task(
            listar_productos(session, timeout=5.0)
        )
        tarea_categorias = asyncio.create_task(
            obtener_categorias(session, timeout=3.0)
        )
        tarea_perfil = asyncio.create_task(
            obtener_perfil(session, timeout=2.0)
        )
        
        todas_las_tareas = {tarea_productos, tarea_categorias, tarea_perfil}
        tareas_nombres = {
            tarea_productos: "productos",
            tarea_categorias: "categorias",
            tarea_perfil: "perfil"
        }
        
        datos = {
            "productos": None,
            "categorias": None,
            "perfil": None
        }
        errores = []
        canceladas_por_auth = False
        
        # Esperar resultados conforme llegan
        pendientes = todas_las_tareas.copy()
        
        while pendientes:
            # Esperar a que al menos una tarea termine
            done, pendientes = await asyncio.wait(
                pendientes, 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for tarea in done:
                nombre = tareas_nombres[tarea]
                
                try:
                    resultado = await tarea
                    datos[nombre] = resultado
                    
                except NoAutorizado as e:
                    # Error 401: Cancelar todas las tareas pendientes
                    errores.append({
                        "endpoint": nombre,
                        "error": str(e),
                        "cancelada": False
                    })
                    
                    # Cancelar las demás
                    if pendientes:
                        num_canceladas = cancel_remaining(pendientes)
                        canceladas_por_auth = True
                        
                        # Agregar las tareas canceladas a los errores
                        for tarea_pendiente in pendientes:
                            nombre_cancelada = tareas_nombres[tarea_pendiente]
                            errores.append({
                                "endpoint": nombre_cancelada,
                                "error": "Cancelada por falta de autenticación",
                                "cancelada": True
                            })
                        
                        break  # Salir del loop
                
                except asyncio.CancelledError:
                    # Esta tarea fue cancelada por otra
                    errores.append({
                        "endpoint": nombre,
                        "error": "Tarea cancelada",
                        "cancelada": True
                    })
                
                except Exception as e:
                    # Otros errores no cancelan las demás tareas
                    errores.append({
                        "endpoint": nombre,
                        "error": str(e),
                        "cancelada": False
                    })
            
            # Si cancelamos por auth, salir del loop
            if canceladas_por_auth:
                break
        
        return {
            "datos": datos,
            "errores": errores,
            "canceladas_por_auth": canceladas_por_auth
        }


# ============================================================
# FEATURE 3: CARGA CON PRIORIDAD USANDO asyncio.wait()
# ============================================================

async def cargar_con_prioridad() -> dict:
    """
    Carga el dashboard procesando resultados conforme llegan.
    
    ESTRATEGIA:
    1. Lanza 4 peticiones simultáneas
    2. Procesa resultados conforme llegan (no espera a todas)
    3. Si las 2 peticiones CRÍTICAS (productos y perfil) llegan, 
       puede mostrar dashboard parcial inmediatamente
    4. Las peticiones SECUNDARIAS (categorías, notificaciones) 
       se procesan cuando lleguen
    
    Returns:
        dict: {
            "criticas_completas": bool,  # ¿productos y perfil listos?
            "tiempo_dashboard_parcial": float,  # segundos hasta dashboard parcial
            "datos": {
                "productos": [...] o None,
                "categorias": [...] o None,
                "perfil": {...} o None,
                "notificaciones": [...] o None
            },
            "errores": [{"endpoint": str, "error": str}, ...],
            "orden_llegada": [str, ...]  # Orden en que llegaron las respuestas
        }
        
    Ejemplo:
        >>> import time
        >>> inicio = time.time()
        >>> resultado = await cargar_con_prioridad()
        >>> 
        >>> if resultado["criticas_completas"]:
        ...     print(f"Dashboard parcial listo en {resultado['tiempo_dashboard_parcial']:.2f}s")
        ...     print(f"  - Productos: {len(resultado['datos']['productos'])}")
        ...     print(f"  - Perfil: {resultado['datos']['perfil']['nombre']}")
        >>> 
        >>> print(f"Orden de llegada: {resultado['orden_llegada']}")
    """
    import time
    inicio = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Crear tareas con timeouts específicos
        tarea_productos = asyncio.create_task(
            listar_productos(session, timeout=5.0)
        )
        tarea_categorias = asyncio.create_task(
            obtener_categorias(session, timeout=3.0)
        )
        tarea_perfil = asyncio.create_task(
            obtener_perfil(session, timeout=2.0)
        )
        tarea_notificaciones = asyncio.create_task(
            obtener_notificaciones(session, timeout=4.0)
        )
        
        todas_las_tareas = {
            tarea_productos, 
            tarea_categorias, 
            tarea_perfil, 
            tarea_notificaciones
        }
        
        tareas_nombres = {
            tarea_productos: "productos",
            tarea_categorias: "categorias",
            tarea_perfil: "perfil",
            tarea_notificaciones: "notificaciones"
        }
        
        # Peticiones críticas vs secundarias
        tareas_criticas = {tarea_productos, tarea_perfil}
        criticas_completadas = set()
        
        datos = {
            "productos": None,
            "categorias": None,
            "perfil": None,
            "notificaciones": None
        }
        errores = []
        orden_llegada = []
        tiempo_dashboard_parcial = None
        
        # Procesar resultados conforme llegan
        pendientes = todas_las_tareas.copy()
        
        while pendientes:
            # Esperar a que al menos una tarea termine
            done, pendientes = await asyncio.wait(
                pendientes,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for tarea in done:
                nombre = tareas_nombres[tarea]
                orden_llegada.append(nombre)
                
                try:
                    resultado = await tarea
                    datos[nombre] = resultado
                    
                    # Marcar críticas completadas
                    if tarea in tareas_criticas:
                        criticas_completadas.add(tarea)
                        
                        # ¿Ya podemos mostrar dashboard parcial?
                        if criticas_completadas == tareas_criticas and tiempo_dashboard_parcial is None:
                            tiempo_dashboard_parcial = time.time() - inicio
                
                except Exception as e:
                    errores.append({
                        "endpoint": nombre,
                        "error": str(e)
                    })
        
        return {
            "criticas_completas": len(criticas_completadas) == len(tareas_criticas),
            "tiempo_dashboard_parcial": tiempo_dashboard_parcial,
            "datos": datos,
            "errores": errores,
            "orden_llegada": orden_llegada
        }
