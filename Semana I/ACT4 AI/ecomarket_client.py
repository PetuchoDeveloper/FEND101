"""
EcoMarket API Client - Python
=============================
Este cliente HTTP consume la API de EcoMarket usando la biblioteca 'requests'.

¿Por qué 'requests'?
- Es la biblioteca HTTP más popular y fácil de usar en Python
- Tiene una sintaxis intuitiva y legible
- Maneja automáticamente headers, JSON y encoding
- Es el estándar de la industria para clientes HTTP en Python

Instalación:
    pip install requests

Autor: Estudiante FEND101
Fecha: 2026-01-28
"""

import requests
from typing import Optional

# =============================================================================
# CONFIGURACIÓN BASE
# =============================================================================

# URL base de la API (cambiar según el entorno)
BASE_URL = "https://api.ecomarket.com/v1"

# Timeout en segundos para las peticiones
# Evita que el programa se quede colgado si el servidor no responde
TIMEOUT = 10

# Header personalizado para identificar la versión del cliente
# El RFC 6648 desaprueba el uso de X-Client-Version por contaminacion de namespaces
X_CLIENT_VERSION = "1.0"

# =============================================================================
# FUNCIÓN 1: Listar todos los productos
# =============================================================================

def listar_productos(categoria: Optional[str] = None, productor_id: Optional[str] = None) -> list:
    """
    Obtiene la lista de productos disponibles en EcoMarket.
    
    Args:
        categoria: Filtrar por categoría (frutas, verduras, lacteos, miel, conservas)
        productor_id: Filtrar por ID del productor
    
    Returns:
        Lista de productos o lista vacía si hay error
    """
    # Construir la URL del endpoint
    url = f"{BASE_URL}/productos"
    
    # Parámetros de query opcionales para filtrar
    params = {}
    if categoria:
        params["categoria"] = categoria
    if productor_id:
        params["productor_id"] = productor_id
    
    try:
        # Realizar la petición GET
        # - params: se añaden automáticamente a la URL como ?categoria=frutas&...
        # - timeout: tiempo máximo de espera
        # - headers: se añaden automáticamente a la petición
        response = requests.get(url, params=params, timeout=TIMEOUT, headers={"X-Client-Version": X_CLIENT_VERSION})
        
        # Verificar si la respuesta fue exitosa (código 2xx)
        # Si no lo fue, lanza una excepción
        response.raise_for_status()
        
        # Parsear el JSON de la respuesta
        # requests hace esto automáticamente con .json()
        productos = response.json()
        
        # Imprimir los productos de forma legible
        print(f"\n✅ Se encontraron {len(productos)} productos:\n")
        for i, producto in enumerate(productos, 1):
            print(f"  {i}. {producto['nombre']}")
            print(f"     Precio: ${producto['precio']:.2f}")
            print(f"     Categoría: {producto['categoria']}")
            print(f"     Disponible: {'Sí' if producto['disponible'] else 'No'}")
            print()
        
        return productos
        
    except requests.exceptions.Timeout:
        # El servidor tardó más del timeout configurado
        print("❌ Error: El servidor tardó demasiado en responder. Intenta más tarde.")
        return []
        
    except requests.exceptions.ConnectionError:
        # No se pudo conectar al servidor (sin internet, servidor caído, etc.)
        print("❌ Error: No se pudo conectar al servidor. Verifica tu conexión a internet.")
        return []
        
    except requests.exceptions.HTTPError as e:
        # El servidor respondió con un código de error (4xx, 5xx)
        print(f"❌ Error del servidor: {e.response.status_code}")
        # Intentar mostrar el mensaje de error del servidor
        try:
            error_data = e.response.json()
            print(f"   Mensaje: {error_data.get('mensaje', 'Sin detalles')}")
        except:
            pass
        return []


# =============================================================================
# FUNCIÓN 2: Obtener un producto específico
# =============================================================================

def obtener_producto(producto_id: str) -> Optional[dict]:
    """
    Obtiene los detalles de un producto específico.
    
    Args:
        producto_id: UUID del producto a buscar
    
    Returns:
        Diccionario con los datos del producto, o None si no existe
    """
    url = f"{BASE_URL}/productos/{producto_id}"
    
    try:
        response = requests.get(url, timeout=TIMEOUT, headers={"X-Client-Version": X_CLIENT_VERSION})
        
        # Manejar específicamente el caso 404
        if response.status_code == 404:
            print(f"⚠️ El producto con ID '{producto_id}' no fue encontrado.")
            print("   Verifica que el ID sea correcto o que el producto no haya sido eliminado.")
            return None
        
        # Verificar otros errores
        response.raise_for_status()
        
        producto = response.json()
        
        # Mostrar el producto de forma amigable
        print(f"\n✅ Producto encontrado:\n")
        print(f"   📦 Nombre: {producto['nombre']}")
        print(f"   📝 Descripción: {producto.get('descripcion', 'Sin descripción')}")
        print(f"   💰 Precio: ${producto['precio']:.2f}")
        print(f"   🏷️ Categoría: {producto['categoria']}")
        print(f"   ✓ Disponible: {'Sí' if producto['disponible'] else 'No'}")
        print(f"   🆔 ID: {producto['id']}")
        print()
        
        return producto
        
    except requests.exceptions.Timeout:
        print("❌ Error: El servidor tardó demasiado en responder.")
        return None
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor.")
        return None
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error inesperado: {e.response.status_code}")
        return None


# =============================================================================
# FUNCIÓN 3: Crear un producto nuevo
# =============================================================================

def crear_producto(nombre: str, precio: float, categoria: str, 
                   productor_id: str, descripcion: str = "", 
                   disponible: bool = True, token: str = "") -> Optional[dict]:
    """
    Crea un nuevo producto en el catálogo de EcoMarket.
    
    Args:
        nombre: Nombre del producto (mínimo 3 caracteres)
        precio: Precio del producto (mínimo 0.01)
        categoria: Una de: frutas, verduras, lacteos, miel, conservas
        productor_id: UUID del productor
        descripcion: Descripción opcional del producto
        disponible: Si el producto está disponible (default: True)
        token: Token JWT de autenticación
    
    Returns:
        Diccionario con el producto creado, o None si hay error
    """
    url = f"{BASE_URL}/productos"
    
    # Construir el cuerpo de la petición (body)
    # Este diccionario se enviará como JSON
    datos = {
        "nombre": nombre,
        "precio": precio,
        "categoria": categoria,
        "productor_id": productor_id,
        "disponible": disponible
    }
    
    # Solo incluir descripción si se proporcionó
    if descripcion:
        datos["descripcion"] = descripcion
    
    # Headers necesarios para la petición
    headers = {
        # Content-Type indica que enviamos JSON
        "Content-Type": "application/json",
        # Authorization con el token Bearer (JWT)
        "Authorization": f"Bearer {token}"
    }
    
    try:
        # Realizar la petición POST
        # - json=datos: convierte automáticamente el dict a JSON
        # - headers: incluye Content-Type y Authorization
        response = requests.post(url, json=datos, timeout=TIMEOUT, headers={"X-Client-Version": X_CLIENT_VERSION, "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        
        # Manejar respuesta exitosa (201 Created)
        if response.status_code == 201:
            producto = response.json()
            print(f"\n✅ ¡Producto creado exitosamente!")
            print(f"   🆔 ID asignado: {producto['id']}")
            print(f"   📦 Nombre: {producto['nombre']}")
            print(f"   💰 Precio: ${producto['precio']:.2f}")
            return producto
        
        # Manejar error de validación (400 Bad Request)
        if response.status_code == 400:
            error = response.json()
            print(f"\n❌ Error de validación:")
            print(f"   Código: {error.get('codigo', 'UNKNOWN')}")
            print(f"   Mensaje: {error.get('mensaje', 'Sin detalles')}")
            # Mostrar detalles adicionales si existen
            if error.get('detalles'):
                print("   Detalles:")
                for detalle in error['detalles']:
                    print(f"     - {detalle}")
            return None
        
        # Manejar falta de autenticación (401 Unauthorized)
        if response.status_code == 401:
            print("\n❌ Error: No estás autenticado o tu token expiró.")
            print("   Obtén un nuevo token de acceso e intenta de nuevo.")
            return None
        
        # Manejar permisos insuficientes (403 Forbidden)
        if response.status_code == 403:
            print("\n❌ Error: No tienes permisos para crear productos.")
            print("   Solo los productores registrados pueden añadir productos.")
            return None
        
        # Otros errores
        response.raise_for_status()
        
    except requests.exceptions.Timeout:
        print("❌ Error: El servidor tardó demasiado. El producto podría haberse creado.")
        return None
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor.")
        return None
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error inesperado: {e.response.status_code}")
        return None

def mock_query():
    """
    Simula una consulta a una API externa.
    """
    url = "https://jsonplaceholder.typicode.com/posts/1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print("userId:",data['userId'])
        print("id:",data['id'])
        print("title:",data['title'])
        print("body:",data['body'])
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener datos: {e}")
        return None

# =============================================================================
# EJEMPLOS DE USO
# =============================================================================

if __name__ == "__main__":
    """
    Esta sección solo se ejecuta si corres este archivo directamente:
        python ecomarket_client.py
    
    No se ejecuta si importas las funciones desde otro archivo.
    """
    
    print("=" * 60)
    print("EcoMarket API Client - Ejemplos de uso")
    print("=" * 60)
    
    # -----------------------------------------
    # Ejemplo 1: Listar todos los productos
    # -----------------------------------------
    print("\n📋 EJEMPLO 1: Listar todos los productos")
    print("-" * 40)
    productos = listar_productos()
    
    # -----------------------------------------
    # Ejemplo 2: Listar productos filtrados
    # -----------------------------------------
    print("\n📋 EJEMPLO 2: Listar solo frutas")
    print("-" * 40)
    frutas = listar_productos(categoria="frutas")
    
    # -----------------------------------------
    # Ejemplo 3: Obtener un producto específico
    # -----------------------------------------
    print("\n📋 EJEMPLO 3: Buscar producto por ID")
    print("-" * 40)
    # Usar un ID de ejemplo (en producción usarías un ID real)
    producto = obtener_producto("550e8400-e29b-41d4-a716-446655440000")
    
    # -----------------------------------------
    # Ejemplo 4: Intentar obtener producto inexistente
    # -----------------------------------------
    print("\n📋 EJEMPLO 4: Buscar producto que no existe")
    print("-" * 40)
    producto_inexistente = obtener_producto("id-que-no-existe-12345")
    
    # -----------------------------------------
    # Ejemplo 5: Crear un producto nuevo
    # -----------------------------------------
    print("\n📋 EJEMPLO 5: Crear un producto nuevo")
    print("-" * 40)
    nuevo_producto = crear_producto(
        nombre="Naranjas Orgánicas Valencia",
        precio=3.50,
        categoria="frutas",
        productor_id="123e4567-e89b-12d3-a456-426614174000",
        descripcion="Naranjas dulces sin semillas, perfectas para jugo.",
        token="tu_token_jwt_aqui"  # Reemplazar con un token real
    )
    
    print("\n📋 EJEMPLO 6: Mock query")
    print("-" * 40)
    mock_query()
    
    print("\n" + "=" * 60)
    print("¡Ejemplos completados!")
    print("=" * 60)
