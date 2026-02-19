"""
Mock Server para Benchmarking de Clientes HTTP - Sync vs Async

Este servidor simula la API de EcoMarket con latencia configurable
para medir objetivamente el rendimiento de clientes síncronos y asíncronos.

Características:
- Latencia configurable por petición (0ms, 100ms, 500ms)
- Tracking de métricas (conexiones TCP, requests)
- Compatible con clientes sync (requests) y async (aiohttp)
"""

import asyncio
from aiohttp import web
import json
import time
from threading import Lock
from dataclasses import dataclass, field
from typing import Dict, List


# ============================================================
# CONFIGURACIÓN GLOBAL Y ESTADO DEL SERVIDOR
# ============================================================

@dataclass
class ServerMetrics:
    """Métricas del servidor para análisis"""
    total_requests: int = 0
    active_connections: int = 0
    request_timestamps: List[float] = field(default_factory=list)
    
    # Lock para operaciones thread-safe
    _lock: Lock = field(default_factory=Lock)
    
    def increment_requests(self):
        with self._lock:
            self.total_requests += 1
            self.request_timestamps.append(time.time())
    
    def increment_connections(self):
        with self._lock:
            self.active_connections += 1
    
    def decrement_connections(self):
        with self._lock:
            self.active_connections = max(0, self.active_connections - 1)
    
    def reset(self):
        with self._lock:
            self.total_requests = 0
            self.active_connections = 0
            self.request_timestamps.clear()


# Instancia global de métricas
metrics = ServerMetrics()

# Latencia configurable (en segundos)
# Se puede cambiar dinámicamente mediante endpoint /config
current_latency = 0.0


# ============================================================
# BASE DE DATOS SIMULADA
# ============================================================

# Productos en memoria para simular una base de datos
productos_db: Dict[int, dict] = {
    1: {
        "id": 1,
        "nombre": "Manzanas Orgánicas",
        "precio": 25.5,
        "categoria": "frutas",
        "stock": 100,
        "fecha_creacion": "2024-01-15T10:30:00Z"
    },
    2: {
        "id": 2,
        "nombre": "Leche Artesanal",
        "precio": 30.0,
        "categoria": "lacteos",
        "stock": 50,
        "fecha_creacion": "2024-01-16T11:00:00Z"
    },
    3: {
        "id": 3,
        "nombre": "Miel de Abeja",
        "precio": 80.0,
        "categoria": "miel",
        "stock": 20,
        "fecha_creacion": "2024-01-17T09:15:00Z"
    }
}

# Contador para IDs autoincrementales
next_product_id = 4


# ============================================================
# MIDDLEWARE PARA LATENCIA Y TRACKING
# ============================================================

@web.middleware
async def latency_middleware(request, handler):
    """Inyecta latencia configurable en cada petición"""
    global current_latency
    
    # Incrementar métricas
    metrics.increment_requests()
    metrics.increment_connections()
    
    try:
        # Simular latencia de red/procesamiento
        if current_latency > 0:
            await asyncio.sleep(current_latency)
        
        # Procesar la petición
        response = await handler(request)
        return response
    
    finally:
        # Decrementar conexiones activas
        metrics.decrement_connections()


# ============================================================
# HANDLERS DE LA API
# ============================================================

async def get_productos(request):
    """GET /api/productos - Listar productos con filtros opcionales"""
    categoria = request.query.get('categoria')
    orden = request.query.get('orden')
    
    # Filtrar por categoría
    productos = list(productos_db.values())
    if categoria:
        productos = [p for p in productos if p['categoria'] == categoria]
    
    # Ordenar si se solicita
    if orden == 'precio_asc':
        productos.sort(key=lambda p: p['precio'])
    elif orden == 'precio_desc':
        productos.sort(key=lambda p: p['precio'], reverse=True)
    
    return web.json_response(productos)


async def get_producto(request):
    """GET /api/productos/{id} - Obtener un producto específico"""
    producto_id = int(request.match_info['id'])
    
    producto = productos_db.get(producto_id)
    if not producto:
        return web.json_response(
            {"detail": f"Producto {producto_id} no encontrado"},
            status=404
        )
    
    return web.json_response(producto)


async def post_producto(request):
    """POST /api/productos - Crear un nuevo producto"""
    global next_product_id
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"detail": "JSON inválido"},
            status=400
        )
    
    # Validar campos requeridos
    required_fields = ['nombre', 'precio', 'categoria']
    for field in required_fields:
        if field not in data:
            return web.json_response(
                {"detail": f"Campo requerido: {field}"},
                status=400
            )
    
    # Crear nuevo producto
    producto = {
        "id": next_product_id,
        "nombre": data['nombre'],
        "precio": data['precio'],
        "categoria": data['categoria'],
        "stock": data.get('stock', 0),
        "fecha_creacion": "2024-02-12T16:00:00Z"
    }
    
    productos_db[next_product_id] = producto
    next_product_id += 1
    
    return web.json_response(producto, status=201)


async def patch_producto(request):
    """PATCH /api/productos/{id} - Actualizar parcialmente un producto"""
    producto_id = int(request.match_info['id'])
    
    producto = productos_db.get(producto_id)
    if not producto:
        return web.json_response(
            {"detail": f"Producto {producto_id} no encontrado"},
            status=404
        )
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"detail": "JSON inválido"},
            status=400
        )
    
    # Actualizar solo los campos proporcionados
    for key in ['nombre', 'precio', 'categoria', 'stock']:
        if key in data:
            producto[key] = data[key]
    
    productos_db[producto_id] = producto
    return web.json_response(producto)


async def put_producto(request):
    """PUT /api/productos/{id} - Actualizar completamente un producto"""
    producto_id = int(request.match_info['id'])
    
    if producto_id not in productos_db:
        return web.json_response(
            {"detail": f"Producto {producto_id} no encontrado"},
            status=404
        )
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"detail": "JSON inválido"},
            status=400
        )
    
    # Validar campos requeridos
    required_fields = ['nombre', 'precio', 'categoria']
    for field in required_fields:
        if field not in data:
            return web.json_response(
                {"detail": f"Campo requerido: {field}"},
                status=400
            )
    
    # Reemplazar producto completo
    producto = {
        "id": producto_id,
        "nombre": data['nombre'],
        "precio": data['precio'],
        "categoria": data['categoria'],
        "stock": data.get('stock', 0),
        "fecha_creacion": productos_db[producto_id]['fecha_creacion']
    }
    
    productos_db[producto_id] = producto
    return web.json_response(producto)


# ============================================================
# ENDPOINTS DE CONFIGURACIÓN Y MÉTRICAS
# ============================================================

async def get_config(request):
    """GET /config - Obtener configuración actual del servidor"""
    return web.json_response({
        "latency_ms": current_latency * 1000,
        "total_requests": metrics.total_requests,
        "active_connections": metrics.active_connections
    })


async def post_config(request):
    """POST /config - Configurar latencia del servidor"""
    global current_latency
    
    try:
        data = await request.json()
        latency_ms = data.get('latency_ms', 0)
        current_latency = latency_ms / 1000.0
        
        return web.json_response({
            "latency_ms": latency_ms,
            "message": f"Latencia configurada a {latency_ms}ms"
        })
    except (json.JSONDecodeError, ValueError):
        return web.json_response(
            {"detail": "Formato inválido. Usar: {\"latency_ms\": 100}"},
            status=400
        )


async def reset_metrics(request):
    """POST /metrics/reset - Reiniciar métricas del servidor"""
    metrics.reset()
    return web.json_response({
        "message": "Métricas reiniciadas"
    })


async def get_metrics(request):
    """GET /metrics - Obtener métricas actuales"""
    return web.json_response({
        "total_requests": metrics.total_requests,
        "active_connections": metrics.active_connections,
        "timestamps_count": len(metrics.request_timestamps)
    })


# ============================================================
# CONFIGURACIÓN Y STARTUP
# ============================================================

def create_app():
    """Crea la aplicación web con todas las rutas y middleware"""
    app = web.Application(middlewares=[latency_middleware])
    
    # Rutas de la API de productos
    app.router.add_get('/api/productos', get_productos)
    app.router.add_get('/api/productos/{id}', get_producto)
    app.router.add_post('/api/productos', post_producto)
    app.router.add_patch('/api/productos/{id}', patch_producto)
    app.router.add_put('/api/productos/{id}', put_producto)
    
    # Rutas de configuración y métricas
    app.router.add_get('/config', get_config)
    app.router.add_post('/config', post_config)
    app.router.add_get('/metrics', get_metrics)
    app.router.add_post('/metrics/reset', reset_metrics)
    
    return app


async def start_server(host='127.0.0.1', port=8888):
    """Inicia el servidor mock para benchmarking"""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    print(f"✅ Benchmark Mock Server corriendo en http://{host}:{port}")
    print(f"   - API: http://{host}:{port}/api/productos")
    print(f"   - Config: http://{host}:{port}/config")
    print(f"   - Métricas: http://{host}:{port}/metrics")
    print(f"   - Latencia actual: {current_latency * 1000}ms")
    
    return runner


async def stop_server(runner):
    """Detiene el servidor mock"""
    await runner.cleanup()
    print("🛑 Benchmark Mock Server detenido")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    async def main():
        runner = await start_server()
        try:
            print("\n💡 Usa Ctrl+C para detener el servidor")
            print("💡 Cambia la latencia con: curl -X POST http://127.0.0.1:8888/config -d '{\"latency_ms\": 100}'")
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n🔄 Deteniendo servidor...")
            await stop_server(runner)
    
    asyncio.run(main())
