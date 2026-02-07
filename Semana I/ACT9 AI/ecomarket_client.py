"""
EcoMarket API Client - Python (v3.0 - Observability)
====================================================
Cliente HTTP con capa de logging profesional (Observability Layer).

Características:
- Logging estructurado de transacciones (Request/Response).
- Ofuscación de datos sensibles (Tokens).
- Métricas de duración y tamaño.
- Niveles de log según criticidad.

Autor: Antigravity AI (Architect)
Fecha: 2026-01-28
"""

import os
import logging
import requests
import time
import json
from typing import Optional, List, Dict, Any, Union, Callable
from functools import wraps

# Configuración de logs para la demo (salida a consola)
# En producción, esto se configuraría externamente (ej. fileHandler o JSON formatter)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-5s | %(name)s | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger("EcoMarketClient")

# =============================================================================
# EXCEPCIONES (Mismas de v2)
# =============================================================================

class EcoMarketError(Exception):
    pass

class EcoMarketNetworkError(EcoMarketError):
    pass

class EcoMarketApiError(EcoMarketError):
    def __init__(self, message: str, status_code: int, details: Optional[Dict] = None):
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.details = details

class EcoMarketDataError(EcoMarketError):
    pass

# =============================================================================
# CAPA DE OBSERVABILIDAD (LOGGING WRAPPER)
# =============================================================================

class AuditLogger:
    """Clase auxiliar para manejar el logging estructurado y sanitizado."""
    
    SENSITIVE_HEADERS = {'Authorization', 'X-Api-Key', 'Cookie'}
    
    @staticmethod
    def sanitize_headers(headers: Dict) -> Dict:
        """Oculta valores de headers sensibles."""
        clean = {}
        for k, v in headers.items():
            if k in AuditLogger.SENSITIVE_HEADERS:
                clean[k] = "******" # Masked
            else:
                clean[k] = v
        return clean

    @staticmethod
    def log_transaction(method: str, url: str, kwargs: Dict, response: Optional[requests.Response], duration_ms: float, error: Optional[Exception] = None):
        """Genera el log basado en el resultado de la transacción."""
        
        # 1. Preparar datos
        status_code = response.status_code if response else "N/A"
        resp_size = len(response.content) if response else 0
        
        # 2. Definir Nivel de Log
        level = logging.INFO
        
        if error:
            level = logging.ERROR
        elif response and response.status_code >= 500:
            level = logging.ERROR
        elif response and response.status_code >= 400:
            level = logging.WARNING # 4xx suele ser error de cliente, warning es apropiado
        elif duration_ms > 2000:
            level = logging.WARNING # Slow request
            
        # 3. Mensaje Resumido (Structured-like text)
        msg = f"{method} {url} | Status: {status_code} | Time: {duration_ms:.2f}ms | Size: {resp_size}b"
        
        if error:
            msg += f" | Error: {str(error)}"
            
        # 4. Emitir Log Principal
        logger.log(level, msg)
        
        # 5. Log Detallado (DEBUG only)
        if logger.isEnabledFor(logging.DEBUG):
            # Request details
            req_headers = AuditLogger.sanitize_headers(kwargs.get('headers', {}))
            logger.debug(f">>> Request Headers: {req_headers}")
            if kwargs.get('json'):
                logger.debug(f">>> Request Body: {json.dumps(kwargs['json'])}")
            
            # Response details
            if response:
                resp_headers = AuditLogger.sanitize_headers(dict(response.headers))
                logger.debug(f"<<< Response Headers: {resp_headers}")
                # Truncate body if too large for logs
                if resp_size < 1000: 
                    logger.debug(f"<<< Response Body: {response.text}")
                else:
                    logger.debug(f"<<< Response Body: (Truncated {resp_size} bytes)")


# Decorador para aplicar observability
def observe_request(func):
    @wraps(func)
    def wrapper(self, method, endpoint, **kwargs):
        # Preparación
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()
        response = None
        error = None
        
        # Inyectar headers globales aquí para que salgan en el log (si no están ya)
        # (Esto es una simplificación, idealmente se mezcla session.headers)
        if 'headers' not in kwargs:
            kwargs['headers'] = dict(self.session.headers)
        else:
            # Merge with session headers
            full_headers = dict(self.session.headers)
            full_headers.update(kwargs['headers'])
            kwargs['headers'] = full_headers

        try:
            # Ejecución real (llamando al request de requests.Session directamente o super)
            # Como estamos decorando _request, 'self' es la instancia de EcoMarketClient
            # PERO: EcoMarketClient._request v2 llama a self.session.request
            # Aquí interceptamos ANTES de llamar a self.session.request si decoramos el método interno
            # O podemos envolver la llamada dentro de _request.
            
            # Para este diseño, vamos a modificar _request para que use el AuditLogger directamente
            # en lugar de usar un decorador externo complejo, para tener acceso a variables locales.
            # (Ver implementación de clase abajo)
            pass 
        except Exception:
            pass
            
    return wrapper

# =============================================================================
# CLIENTE PRINCIPAL (Refactorizado con Observability)
# =============================================================================

class EcoMarketClient:
    DEFAULT_BASE_URL = "https://api.ecomarket.com/v1"
    DEFAULT_TIMEOUT = 10
    CLIENT_VERSION = "3.0-obs"

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"EcoMarketClient/{self.CLIENT_VERSION}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Preparar headers completos para el log
        # requests lo hace internamente, pero para loguear "lo que se va a enviar" necesitamos simularlo
        req_headers = dict(self.session.headers)
        if 'headers' in kwargs:
            req_headers.update(kwargs['headers'])
            
        # OBSERVABILITY: Start Timer
        start_time = time.time()
        response = None
        error_captured = None

        try:
            logger.debug(f"Initiating {method} transaction to {url}")
            
            # Ejecución
            response = self.session.request(method, url, **kwargs)
            
            # Validación
            if 400 <= response.status_code < 600:
                try:
                    payload = response.json()
                    msg = payload.get('mensaje', response.reason)
                except:
                    msg = response.text[:100]
                raise EcoMarketApiError(msg, response.status_code)

            if response.status_code != 204:
                return response.json()
            return None

        except Exception as e:
            error_captured = e
            # Re-lanzar excepciones conocidas o empaquetar desconocidas
            if isinstance(e, (EcoMarketError, requests.exceptions.RequestException)):
                raise e
            raise EcoMarketNetworkError(f"Unexpected: {e}")

        finally:
            # OBSERVABILITY: End Timer & Log
            duration = (time.time() - start_time) * 1000 # ms
            
            # Usamos kwargs modificado con headers merged si quisiéramos ser exactos, 
            # o pasamos lo que tenemos.
            log_kwargs = kwargs.copy()
            log_kwargs['headers'] = req_headers
            
            AuditLogger.log_transaction(
                method, url, log_kwargs, response, duration, error_captured
            )

    # Métodos públicos (API)
    def listar_productos(self) -> List[Dict]:
        return self._request("GET", "productos")

    def obtener_producto(self, pid: str) -> Dict:
        return self._request("GET", f"productos/{pid}")

    def crear_producto(self, data: Dict) -> Dict:
        return self._request("POST", "productos", json=data)

# =============================================================================
# DEMO
# =============================================================================
if __name__ == "__main__":
    print("--- Demo de Observabilidad ---")
    # Para probar esto sin servidor real, usaríamos mock, pero el script de test lo hará.
