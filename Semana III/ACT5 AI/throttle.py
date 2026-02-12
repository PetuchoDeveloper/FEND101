"""
Sistema de Control de Tráfico HTTP para EcoMarket

Este módulo implementa tres componentes principales:
1. ConcurrencyLimiter: Limita peticiones simultáneas usando asyncio.Semaphore
2. RateLimiter: Limita peticiones por segundo usando token bucket algorithm
3. ThrottledClient: Combina ambos limitadores para control completo de tráfico

Diseñado como ingeniero de control de tráfico para:
- Prevenir sobrecarga del servidor (límite de conexiones)
- Evitar agotar file descriptors del cliente
- Respetar rate limits del API
"""

import asyncio
import aiohttp
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from validadores import validar_producto, validar_lista_productos, ValidationError as SchemaValidationError
from url_builder import URLBuilder, URLSecurityError

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configuración centralizada
BASE_URL = "http://localhost:3000/api/"
DEFAULT_TIMEOUT = 10

# Constructor de URLs seguro
url_builder = URLBuilder(BASE_URL)

# Headers comunes
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
    """Error del servidor (5xx)"""
    pass

class ProductoNoEncontrado(EcoMarketError):
    """El producto solicitado no existe (404)"""
    pass

class TimeoutError(EcoMarketError):
    """La petición tardó demasiado tiempo"""
    pass

class ConexionError(EcoMarketError):
    """No se pudo conectar con el servidor"""
    pass


# ============================================================
# 1. CONCURRENCY LIMITER (usando asyncio.Semaphore)
# ============================================================

class ConcurrencyLimiter:
    """
    Limita el número de peticiones HTTP concurrentes.
    
    Usa asyncio.Semaphore para garantizar que nunca haya más de
    max_concurrent peticiones ejecutándose al mismo tiempo.
    
    Ejemplo:
        >>> limiter = ConcurrencyLimiter(max_concurrent=10)
        >>> async with limiter.acquire():
        ...     # Tu petición HTTP aquí
        ...     response = await session.get(url)
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        Args:
            max_concurrent: Número máximo de peticiones simultáneas
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._in_flight = 0  # Contador de peticiones en vuelo
        self._lock = asyncio.Lock()  # Para actualizar contador de forma segura
        self.logger = logging.getLogger("ConcurrencyLimiter")
        
    class AcquireContext:
        """Context manager para adquirir/liberar el semáforo"""
        
        def __init__(self, limiter: 'ConcurrencyLimiter'):
            self.limiter = limiter
            
        async def __aenter__(self):
            await self.limiter.semaphore.acquire()
            async with self.limiter._lock:
                self.limiter._in_flight += 1
                self.limiter.logger.info(
                    f"Petición iniciada. En vuelo: {self.limiter._in_flight}/{self.limiter.max_concurrent}"
                )
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            async with self.limiter._lock:
                self.limiter._in_flight -= 1
                self.limiter.logger.info(
                    f"Petición completada. En vuelo: {self.limiter._in_flight}/{self.limiter.max_concurrent}"
                )
            self.limiter.semaphore.release()
            return False
    
    def acquire(self):
        """Retorna un context manager para usar con async with"""
        return self.AcquireContext(self)
    
    @property
    def in_flight(self) -> int:
        """Número actual de peticiones en vuelo"""
        return self._in_flight


# ============================================================
# 2. RATE LIMITER (usando token bucket algorithm)
# ============================================================

@dataclass
class TokenBucket:
    """
    Implementación del algoritmo Token Bucket para rate limiting.
    
    Conceptos:
    - Bucket tiene capacidad máxima de tokens
    - Se añaden tokens a rate constante (tokens_per_second)
    - Cada petición consume 1 token
    - Si no hay tokens, la petición espera
    
    Ejemplo:
        >>> bucket = TokenBucket(max_tokens=20, tokens_per_second=20)
        >>> await bucket.acquire()  # Consume 1 token
    """
    max_tokens: int
    tokens_per_second: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    
    def __post_init__(self):
        self.tokens = self.max_tokens
        self.last_refill = time.time()
    
    async def acquire(self) -> float:
        """
        Adquiere un token (espera si es necesario).
        
        Returns:
            float: Tiempo en segundos que la petición esperó
        """
        inicio_espera = time.time()
        
        while True:
            # Rellenar tokens según tiempo transcurrido
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.max_tokens,
                self.tokens + elapsed * self.tokens_per_second
            )
            self.last_refill = now
            
            # ¿Hay tokens disponibles?
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                tiempo_esperado = time.time() - inicio_espera
                return tiempo_esperado
            
            # Calcular cuánto tiempo esperar hasta el siguiente token
            deficit = 1.0 - self.tokens
            sleep_time = deficit / self.tokens_per_second
            await asyncio.sleep(sleep_time)


class RateLimiter:
    """
    Limita el rate de peticiones por segundo.
    
    Usa el algoritmo token bucket para garantizar que no se exceda
    max_per_second peticiones por segundo.
    
    Ejemplo:
        >>> limiter = RateLimiter(max_per_second=20)
        >>> async with limiter.acquire():
        ...     # Tu petición HTTP aquí
        ...     response = await session.get(url)
    """
    
    def __init__(self, max_per_second: float = 20):
        """
        Args:
            max_per_second: Número máximo de peticiones por segundo
        """
        self.max_per_second = max_per_second
        self.bucket = TokenBucket(
            max_tokens=int(max_per_second),
            tokens_per_second=max_per_second
        )
        self.logger = logging.getLogger("RateLimiter")
        self._total_wait_time = 0.0
        self._requests_made = 0
        
    class AcquireContext:
        """Context manager para rate limiting"""
        
        def __init__(self, limiter: 'RateLimiter'):
            self.limiter = limiter
            self.wait_time = 0.0
            
        async def __aenter__(self):
            self.wait_time = await self.limiter.bucket.acquire()
            self.limiter._requests_made += 1
            self.limiter._total_wait_time += self.wait_time
            
            if self.wait_time > 0.001:  # Solo log si esperó más de 1ms
                self.limiter.logger.info(
                    f"Petición esperó {self.wait_time:.3f}s por rate limit. "
                    f"Rate actual: {self.limiter.max_per_second}/s"
                )
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False
    
    def acquire(self):
        """Retorna un context manager para usar con async with"""
        return self.AcquireContext(self)
    
    @property
    def average_wait_time(self) -> float:
        """Tiempo promedio de espera por petición"""
        if self._requests_made == 0:
            return 0.0
        return self._total_wait_time / self._requests_made


# ============================================================
# 3. THROTTLED CLIENT (combinando ambos limitadores)
# ============================================================

class ThrottledClient:
    """
    Cliente HTTP con control de tráfico completo.
    
    Combina ConcurrencyLimiter y RateLimiter para garantizar:
    1. No más de max_concurrent peticiones simultáneas
    2. No más de max_per_second peticiones por segundo
    
    ORDEN DE APLICACIÓN:
    1. Primero aplica rate limiting (espera por token)
    2. Luego aplica concurrency limiting (espera por slot)
    3. Finalmente ejecuta la petición
    
    Ejemplo:
        >>> client = ThrottledClient(max_concurrent=10, max_per_second=20)
        >>> productos = await client.listar_productos()
        >>> cliente.close()
    """
    
    def __init__(
        self, 
        max_concurrent: int = 10,
        max_per_second: float = 20,
        base_url: str = BASE_URL
    ):
        """
        Args:
            max_concurrent: Número máximo de peticiones simultáneas
            max_per_second: Número máximo de peticiones por segundo
            base_url: URL base del API
        """
        self.concurrency_limiter = ConcurrencyLimiter(max_concurrent)
        self.rate_limiter = RateLimiter(max_per_second)
        self.base_url = base_url
        self.url_builder = URLBuilder(base_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("ThrottledClient")
        
        # Métricas
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0
        }
        
    async def _ensure_session(self):
        """Crea sesión si no existe"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: float = DEFAULT_TIMEOUT
    ) -> Any:
        """
        Ejecuta una petición HTTP con throttling completo.
        
        Esta es la función principal que aplica AMBOS limitadores.
        """
        await self._ensure_session()
        
        url = self.url_builder.build_url(endpoint, query_params=params)
        
        # PASO 1: Esperar por rate limit
        async with self.rate_limiter.acquire():
            # PASO 2: Esperar por slot de concurrencia
            async with self.concurrency_limiter.acquire():
                # PASO 3: Ejecutar petición
                try:
                    self.metrics['total_requests'] += 1
                    
                    kwargs = {
                        'timeout': aiohttp.ClientTimeout(total=timeout)
                    }
                    
                    if json_data is not None:
                        kwargs['json'] = json_data
                        kwargs['headers'] = HEADERS_JSON
                        self.metrics['total_bytes_sent'] += len(str(json_data))
                    
                    async with self.session.request(method, url, **kwargs) as response:
                        # Verificar código de estado
                        if response.status >= 500:
                            raise ServerError(f"Error del servidor: {response.status}")
                        if response.status >= 400:
                            raise HTTPValidationError(f"Error de cliente: {response.status}")
                        
                        # Parsear respuesta
                        if response.status == 204:  # No Content
                            result = None
                        else:
                            result = await response.json()
                            self.metrics['total_bytes_received'] += len(str(result))
                        
                        self.metrics['successful_requests'] += 1
                        return result
                
                except aiohttp.ClientTimeout:
                    self.metrics['failed_requests'] += 1
                    raise TimeoutError(f"{method} {endpoint} tardó más de {timeout}s")
                except aiohttp.ClientConnectorError as e:
                    self.metrics['failed_requests'] += 1
                    raise ConexionError(f"No se pudo conectar: {e}")
    
    # ============================================================
    # OPERACIONES CRUD (con throttling automático)
    # ============================================================
    
    async def listar_productos(
        self, 
        categoria: Optional[str] = None,
        orden: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT
    ) -> List[Dict]:
        """GET /productos con filtros opcionales"""
        params = {}
        if categoria:
            params['categoria'] = categoria
        if orden:
            params['orden'] = orden
        
        result = await self._request('GET', 'productos', params=params, timeout=timeout)
        return validar_lista_productos(result)
    
    async def obtener_producto(
        self,
        producto_id: int,
        timeout: float = DEFAULT_TIMEOUT
    ) -> Dict:
        """GET /productos/{id}"""
        result = await self._request('GET', f'productos/{producto_id}', timeout=timeout)
        return validar_producto(result)
    
    async def crear_producto(
        self,
        producto: Dict,
        timeout: float = DEFAULT_TIMEOUT
    ) -> Dict:
        """POST /productos - Crea un nuevo producto"""
        result = await self._request('POST', 'productos', json_data=producto, timeout=timeout)
        return validar_producto(result)
    
    async def actualizar_producto(
        self,
        producto_id: int,
        producto: Dict,
        timeout: float = DEFAULT_TIMEOUT
    ) -> Dict:
        """PUT /productos/{id} - Actualización completa"""
        result = await self._request(
            'PUT', 
            f'productos/{producto_id}', 
            json_data=producto,
            timeout=timeout
        )
        return validar_producto(result)
    
    async def actualizar_producto_parcial(
        self,
        producto_id: int,
        cambios: Dict,
        timeout: float = DEFAULT_TIMEOUT
    ) -> Dict:
        """PATCH /productos/{id} - Actualización parcial"""
        result = await self._request(
            'PATCH',
            f'productos/{producto_id}',
            json_data=cambios,
            timeout=timeout
        )
        return validar_producto(result)
    
    async def eliminar_producto(
        self,
        producto_id: int,
        timeout: float = DEFAULT_TIMEOUT
    ) -> bool:
        """DELETE /productos/{id}"""
        await self._request('DELETE', f'productos/{producto_id}', timeout=timeout)
        return True
    
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_metrics(self) -> Dict:
        """
        Retorna métricas de uso del cliente.
        
        Returns:
            dict: Métricas incluyendo:
                - total_requests: Total de peticiones hechas
                - successful_requests: Peticiones exitosas
                - failed_requests: Peticiones fallidas
                - in_flight: Peticiones actualmente en ejecución
                - average_wait_time: Tiempo promedio de espera por rate limit
        """
        return {
            **self.metrics,
            'in_flight': self.concurrency_limiter.in_flight,
            'average_wait_time': self.rate_limiter.average_wait_time,
            'max_concurrent': self.concurrency_limiter.max_concurrent,
            'max_per_second': self.rate_limiter.max_per_second
        }
    
    async def __aenter__(self):
        """Context manager support"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        await self.close()
        return False


# ============================================================
# FUNCIÓN DE DEMOSTRACIÓN
# ============================================================

async def crear_multiples_productos(
    num_productos: int = 50,
    max_concurrent: int = 10,
    max_per_second: float = 20
) -> Dict:
    """
    Crea múltiples productos de forma throttled.
    
    Esta función demuestra el uso del ThrottledClient para crear
    muchos productos sin sobrecargar el servidor.
    
    Args:
        num_productos: Número de productos a crear
        max_concurrent: Límite de concurrencia
        max_per_second: Límite de rate
        
    Returns:
        dict: Resultados con métricas y productos creados
    """
    inicio = time.time()
    
    async with ThrottledClient(max_concurrent, max_per_second) as client:
        # Generar productos de prueba
        tareas = []
        for i in range(num_productos):
            producto = {
                "nombre": f"Producto Test {i+1}",
                "descripcion": f"Producto de prueba #{i+1}",
                "precio": 100 + i,
                "categoria": "test",
                "stock": 10
            }
            tareas.append(client.crear_producto(producto))
        
        # Ejecutar todas las creaciones
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        
        # Analizar resultados
        exitosos = [r for r in resultados if not isinstance(r, Exception)]
        errores = [r for r in resultados if isinstance(r, Exception)]
        
        tiempo_total = time.time() - inicio
        
        return {
            'num_productos': num_productos,
            'exitosos': len(exitosos),
            'errores': len(errores),
            'tiempo_total': tiempo_total,
            'throughput': num_productos / tiempo_total,
            'metrics': client.get_metrics(),
            'productos': exitosos[:10]  # Solo primeros 10 para no saturar
        }
