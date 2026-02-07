"""
Módulo de Retry para Clientes HTTP

Implementa reintentos automáticos con exponential backoff y jitter
para manejar errores transitorios de servidor (5xx) y timeouts.

NO reintenta en errores 4xx (son errores del cliente).
"""

import time
import random
import logging
import functools
from typing import Tuple, Type, Callable, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# EXCEPCIONES
# ============================================================

class RetryableError(Exception):
    """Error base para errores que pueden reintentarse."""
    pass


class ServerError(RetryableError):
    """Error del servidor (5xx) - transitorio, reintentar."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class TimeoutError(RetryableError):
    """La petición excedió el tiempo límite - reintentar."""
    pass


class ClientError(Exception):
    """Error del cliente (4xx) - NO reintentar."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class RetryExhaustedError(Exception):
    """Se agotaron todos los reintentos disponibles."""
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


# ============================================================
# CONFIGURACIÓN DE RETRY
# ============================================================

class RetryConfig:
    """
    Configuración para el comportamiento de retry.
    
    Attributes:
        max_retries: Número máximo de reintentos (default: 4)
        base_delay: Delay base en segundos para exponential backoff (default: 1.0)
        max_delay: Delay máximo permitido en segundos (default: 60.0)
        jitter_range: Rango de variación aleatoria 0-1 (default: 0.25)
        retry_on: Tuple de excepciones que deben reintentarse
    """
    
    def __init__(
        self,
        max_retries: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter_range: float = 0.25,
        retry_on: Tuple[Type[Exception], ...] = (RetryableError,)
    ):
        if max_retries < 0:
            raise ValueError("max_retries debe ser >= 0")
        if base_delay <= 0:
            raise ValueError("base_delay debe ser > 0")
        if max_delay < base_delay:
            raise ValueError("max_delay debe ser >= base_delay")
        if not 0 <= jitter_range <= 1:
            raise ValueError("jitter_range debe estar entre 0 y 1")
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_range = jitter_range
        self.retry_on = retry_on


# ============================================================
# FUNCIONES DE CÁLCULO DE DELAY
# ============================================================

def calculate_exponential_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """
    Calcula el delay con exponential backoff.
    
    delay = min(base_delay * 2^attempt, max_delay)
    
    Args:
        attempt: Número de intento (0-indexed)
        base_delay: Delay base en segundos
        max_delay: Delay máximo permitido
    
    Returns:
        Delay en segundos (sin jitter)
    """
    exponential_delay = base_delay * (2 ** attempt)
    return min(exponential_delay, max_delay)


def apply_jitter(delay: float, jitter_range: float) -> float:
    """
    Aplica variación aleatoria (jitter) al delay.
    
    Esto previene el "thundering herd" problem donde múltiples
    clientes reintentan simultáneamente.
    
    Args:
        delay: Delay base en segundos
        jitter_range: Rango de variación (0-1)
    
    Returns:
        Delay con jitter aplicado
    """
    if jitter_range == 0:
        return delay
    
    # Jitter simétrico: delay * (1 ± jitter_range)
    jitter_factor = 1 + random.uniform(-jitter_range, jitter_range)
    return delay * jitter_factor


def calculate_delay_with_jitter(
    attempt: int,
    base_delay: float,
    max_delay: float,
    jitter_range: float
) -> float:
    """
    Calcula el delay completo con exponential backoff y jitter.
    
    Args:
        attempt: Número de intento (0-indexed)
        base_delay: Delay base en segundos
        max_delay: Delay máximo permitido
        jitter_range: Rango de variación aleatoria
    
    Returns:
        Delay final en segundos
    """
    base = calculate_exponential_delay(attempt, base_delay, max_delay)
    return apply_jitter(base, jitter_range)


# ============================================================
# DECORADOR PRINCIPAL
# ============================================================

def with_retry(
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_range: float = 0.25,
    retry_on: Tuple[Type[Exception], ...] = (RetryableError,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
):
    """
    Decorador que agrega lógica de retry con exponential backoff y jitter.
    
    Reintenta automáticamente cuando la función lanza una excepción
    que está en retry_on (por default: ServerError, TimeoutError).
    
    NO reintenta en errores 4xx (ClientError) - esos son errores del
    cliente que no se resolverán reintentando.
    
    Args:
        max_retries: Número máximo de reintentos (default: 4)
        base_delay: Delay base en segundos (default: 1.0)
        max_delay: Delay máximo en segundos (default: 60.0)
        jitter_range: Variación aleatoria 0-1 (default: 0.25)
        retry_on: Tuple de excepciones a reintentar
        on_retry: Callback opcional llamado antes de cada reintento
                  Signature: (attempt, exception, delay) -> None
    
    Returns:
        Función decorada con lógica de retry
    
    Raises:
        RetryExhaustedError: Si se agotan todos los reintentos
        ClientError: Si ocurre un error 4xx (no se reintenta)
    
    Example:
        >>> @with_retry(max_retries=3, base_delay=1.0)
        ... def fetch_data():
        ...     response = requests.get(url)
        ...     if response.status_code >= 500:
        ...         raise ServerError("Server error", response.status_code)
        ...     return response.json()
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter_range=jitter_range,
        retry_on=retry_on
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            # Intento inicial + reintentos
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except config.retry_on as e:
                    last_exception = e
                    
                    # Si es el último intento, no esperar
                    if attempt >= config.max_retries:
                        break
                    
                    # Calcular delay
                    delay = calculate_delay_with_jitter(
                        attempt,
                        config.base_delay,
                        config.max_delay,
                        config.jitter_range
                    )
                    
                    # Log del reintento
                    logger.warning(
                        f"[Retry {attempt + 1}/{config.max_retries}] "
                        f"{func.__name__} falló con {type(e).__name__}: {e}. "
                        f"Reintentando en {delay:.2f}s..."
                    )
                    
                    # Callback opcional
                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    
                    # Esperar antes de reintentar
                    time.sleep(delay)
                
                except Exception as e:
                    # Errores no configurados para retry (incluyendo ClientError)
                    # se propagan inmediatamente
                    raise
            
            # Se agotaron los reintentos
            raise RetryExhaustedError(
                f"Reintentos agotados después de {config.max_retries + 1} intentos. "
                f"Último error: {last_exception}",
                last_exception=last_exception,
                attempts=config.max_retries + 1
            )
        
        return wrapper
    return decorator


# ============================================================
# UTILIDADES ADICIONALES
# ============================================================

def is_retryable_status(status_code: int) -> bool:
    """
    Determina si un código de estado HTTP es reintentalbe.
    
    5xx → Reintentar (error del servidor, típicamente transitorio)
    4xx → NO reintentar (error del cliente, reintentar no ayuda)
    
    Casos especiales:
    - 429 Too Many Requests: Podría reintentarse con más delay
    - 503 Service Unavailable: Definitivamente reintentar
    
    Args:
        status_code: Código de estado HTTP
    
    Returns:
        True si el error debería reintentarse
    """
    return 500 <= status_code < 600


def raise_for_status_with_retry(status_code: int, message: str = ""):
    """
    Lanza la excepción apropiada basada en el código de estado.
    
    Útil para convertir códigos HTTP a excepciones del módulo retry.
    
    Args:
        status_code: Código de estado HTTP
        message: Mensaje de error opcional
    
    Raises:
        ServerError: Si status_code >= 500
        ClientError: Si status_code >= 400 y < 500
    """
    if status_code >= 500:
        raise ServerError(message or f"Error del servidor: {status_code}", status_code)
    elif status_code >= 400:
        raise ClientError(message or f"Error del cliente: {status_code}", status_code)
