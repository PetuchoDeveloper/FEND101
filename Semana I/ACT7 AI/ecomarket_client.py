"""
EcoMarket API Client - Python (Refactorizado)
=============================================
Cliente HTTP robusto para la API de EcoMarket.

Mejoras en esta versión (v2.0):
- Manejo de errores explícito con excepciones personalizadas.
- Uso de `requests.Session` para reuso de conexiones.
- Validación de Content-Type.
- Logging en lugar de prints.
- Configuración centralizada.

Autor: Antigravity AI (Auditor Senior)
Fecha: 2026-01-28
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any, Union

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EcoMarketClient")

# =============================================================================
# EXCEPCIONES PERSONALIZADAS
# =============================================================================

class EcoMarketError(Exception):
    """Excepción base para errores del cliente EcoMarket."""
    pass

class EcoMarketNetworkError(EcoMarketError):
    """Error de conexión o timeout."""
    pass

class EcoMarketApiError(EcoMarketError):
    """Error devuelto por la API (4xx, 5xx)."""
    def __init__(self, message: str, status_code: int, details: Optional[Dict] = None):
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.details = details

class EcoMarketDataError(EcoMarketError):
    """Error al procesar datos (ej. JSON inválido)."""
    pass

# =============================================================================
# CLIENTE PRINCIPAL
# =============================================================================

class EcoMarketClient:
    """Cliente para interactuar con la API de EcoMarket."""

    DEFAULT_BASE_URL = "https://api.ecomarket.com/v1"
    DEFAULT_TIMEOUT = 10  # Segundos
    CLIENT_VERSION = "2.0"

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        """
        Inicializa el cliente.

        Args:
            base_url: URL base de la API. Si es None, usa la default.
            token: Token Bearer opcional para autenticación global.
            timeout: Timeout global para peticiones.
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Headers por defecto (Mejora: User-Agent propio)
        self.session.headers.update({
            "User-Agent": f"EcoMarketClient/{self.CLIENT_VERSION}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Método interno centralizado para realizar peticiones.
        Maneja errores, timeouts y validación de respuesta.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            # Mejora: Timeout configurable por llamada si es necesario
            timeout = kwargs.pop('timeout', self.timeout)
            
            logger.debug(f"Haciendo {method} a {url}")
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            
            # 1. Validar status codes
            if 400 <= response.status_code < 600:
                try:
                    error_data = response.json()
                    mensaje = error_data.get('mensaje', response.reason)
                    detalles = error_data.get('detalles')
                except ValueError:
                    # Si falla el parseo de error, usamos el texto crudo (puede ser HTML de un proxy)
                    mensaje = response.text[:200] # Truncar para no llenar logs
                    detalles = None
                
                logger.error(f"Error API {response.status_code}: {mensaje}")
                raise EcoMarketApiError(mensaje, response.status_code, detalles)

            # 2. Validar Content-Type antes de parsear JSON
            # Nota: 204 No Content no tiene cuerpo
            if response.status_code == 204:
                return None

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                # Mejora: Advertir si el servidor devuelve algo que no declaramos aceptar
                logger.warning(f"Respuesta exitosa ({response.status_code}) pero Content-Type inesperado: {content_type}")

            try:
                return response.json()
            except ValueError as e:
                logger.error("Error decodificando JSON de respuesta")
                raise EcoMarketDataError(f"Respuesta inválida del servidor: {str(e)}") from e

        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando a {url}")
            raise EcoMarketNetworkError(f"La petición excedió el tiempo límite de {timeout}s")
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión a {url}")
            raise EcoMarketNetworkError("No se pudo conectar al servidor")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error inesperado en petición: {str(e)}")
            raise EcoMarketNetworkError(f"Error de red inesperado: {str(e)}")


    # =========================================================================
    # MÉTODOS PÚBLICOS
    # =========================================================================

    def listar_productos(self, categoria: Optional[str] = None, productor_id: Optional[str] = None) -> List[Dict]:
        """
        Obtiene la lista de productos.
        """
        params = {}
        if categoria: params["categoria"] = categoria
        if productor_id: params["productor_id"] = productor_id

        return self._request("GET", "productos", params=params)

    def obtener_producto(self, producto_id: str) -> Dict:
        """
        Obtiene un producto específico.
        Lanza EcoMarketApiError(404) si no existe.
        """
        return self._request("GET", f"productos/{producto_id}")

    def crear_producto(self, nombre: str, precio: float, categoria: str, 
                       productor_id: str, descripcion: str = "", 
                       disponible: bool = True) -> Dict:
        """
        Crea un nuevo producto. 
        Nota: Requiere que el cliente se haya inicializado con token.
        """
        datos = {
            "nombre": nombre,
            "precio": precio,
            "categoria": categoria,
            "productor_id": productor_id,
            "disponible": disponible
        }
        if descripcion:
            datos["descripcion"] = descripcion

        return self._request("POST", "productos", json=datos)


# =============================================================================
# EJEMPLOS DE USO
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("EcoMarket API Client v2.0 - Ejemplos (Seguro)")
    print("=" * 60)
    
    # Usar variables de entorno para secretos (Seguridad)
    token = os.getenv("ECOMARKET_TOKEN", "token_dummy_para_demo")
    
    # Instanciar cliente
    # Nota: Usamos JSONPlaceholder para que el script no falle al ejecutarlo
    # Para producción usar: client = EcoMarketClient(token=token)
    MOCK_URL = "https://jsonplaceholder.typicode.com" 
    print(f"\n📡 Conectando a Mock API: {MOCK_URL}")
    
    # Hack para demo: Sobreescribimos la URL base para que funcionen los ejemplos con Typicode
    client = EcoMarketClient(base_url=MOCK_URL, token=token)
    
    # Ejemplo 1: Manejo de errores correcto
    print("\n📋 EJEMPLO 1: Listar (adaptado a mock)")
    try:
        # En el mock, /posts es equivalente a /productos
        posts = client._request("GET", "posts", params={"_limit": 3})
        print(f"✅ Se obtuvieron {len(posts)} items")
        for p in posts:
            print(f"   - {p['title'][:30]}...")
            
    except EcoMarketError as e:
        print(f"❌ Error controlado: {e}")

    # Ejemplo 2: Recurso no encontrado (404)
    print("\n📋 EJEMPLO 2: Error 404 atrapado")
    try:
        client._request("GET", "posts/999999")
    except EcoMarketApiError as e:
        if e.status_code == 404:
            print("✅ Excepción 404 capturada correctamente")
        else:
            print(f"⚠️ Otro error API: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {type(e)}")

    # Ejemplo 3: Timeout
    print("\n📋 EJEMPLO 3: Timeout forzado")
    try:
        # Forzamos timeout de 0.001s
        client._request("GET", "posts", timeout=0.001)
    except EcoMarketNetworkError as e:
        print(f"✅ Excepción de timeout capturada: {e}")

    print("\n" + "=" * 60)
    print("¡Auditoría completada!")
    print("=" * 60)
