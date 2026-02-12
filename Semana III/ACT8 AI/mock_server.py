"""
Mock Server para Tests del Cliente Async EcoMarket

Este servidor mock usa aiohttp.web para simular la API de EcoMarket.
Permite probar el cliente con HTTP real en lugar de mocks limitados.
"""

import asyncio
import aiohttp
from aiohttp import web
import json


# ============================================================
# HANDLERS DEL MOCK SERVER
# ============================================================

async def get_productos(request):
    """GET /productos - Retorna lista de productos"""
    # Simular categoría filter
    categoria = request.query.get('categoria')
    
    productos = [
        {"id": 1, "nombre": "Manzanas Orgánicas", "precio": 25.5, "categoria": "frutas", "stock": 100, "fecha_creacion": "2024-01-15T10:30:00Z"},
        {"id": 2, "nombre": "Leche Artesanal", "precio": 30.0, "categoria": "lacteos", "stock": 50, "fecha_creacion": "2024-01-16T11:00:00Z"},
        {"id": 3, "nombre": "Miel de Abeja", "precio": 80.0, "categoria": "miel", "stock": 20, "fecha_creacion": "2024-01-17T09:15:00Z"}
    ]
    
    if categoria:
        productos = [p for p in productos if p["categoria"] == categoria]
    
    return web.json_response(productos)


async def get_producto(request):
    """GET /productos/{id} - Retorna un producto específico"""
    producto_id = int(request.match_info['id'])

    
    # Producto simulado
    if producto_id == 999:
        # Producto inválido (para tests de validación)
        return web.json_response({
            "id": 999,
            "nombre": "Producto Malicioso",
            "precio": -100,  # Precio negativo (inválido)
            "categoria": "test",
            "stock": 10
        })
    elif producto_id == 404:
        return web.Response(status=404)
    else:
        return web.json_response({
            "id": producto_id,
            "nombre": f"Producto {producto_id}",
            "precio": 25.5,
            "categoria": "frutas",
            "stock": 100,
            "fecha_creacion": "2024-01-15T10:30:00Z"
        })


async def post_producto(request):
    """POST /productos - Crea un nuevo producto"""
    data = await request.json()
    
    # Simular que se creó con ID
    producto = {**data, "id": 123, "fecha_creacion": "2024-01-01T00:00:00Z"}
    
    return web.json_response(producto, status=201)


async def get_categorias(request):
    """GET /categorias - Retorna lista de categorías"""
    return web.json_response(["frutas", "lacteos", "miel"])


async def get_perfil(request):
    """GET /perfil - Retorna perfil del usuario"""
    return web.json_response({
        "id": 1,
        "nombre": "Usuario Test",
        "email": "test@ecomarket.com"
    })


async def handler_error_500(request):
    """Endpoint que siempre retorna 500"""
    return web.Response(status=500, text="Internal Server Error")


async def handler_error_401(request):
    """Endpoint que siempre retorna 401"""
    return web.Response(status=401, text="Unauthorized")


async def handler_timeout(request):
    """Endpoint que tarda mucho (para tests de timeout)"""
    await asyncio.sleep(10)  # Tarda 10 segundos
    return web.json_response({"delayed": True})


async def handler_invalid_json(request):
    """Endpoint que retorna HTML en lugar de JSON"""
    return web.Response(text="<html><body>Error</body></html>", content_type="text/html")


# ============================================================
# CONFIGURACIÓN Y STARTUP DEL SERVIDOR
# ============================================================

def create_app():
    """Crea la aplicación web con todas las rutas"""
    app = web.Application()
    
    # Rutas normales
    app.router.add_get('/api/productos', get_productos)
    app.router.add_get('/api/productos/{id}', get_producto)
    app.router.add_post('/api/productos', post_producto)
    app.router.add_get('/api/categorias', get_categorias)
    app.router.add_get('/api/perfil', get_perfil)
    
    # Rutas especiales para tests
    app.router.add_get('/api/test/error500', handler_error_500)
    app.router.add_get('/api/test/error401', handler_error_401)
    app.router.add_get('/api/test/timeout', handler_timeout)
    app.router.add_get('/api/test/invalid-json', handler_invalid_json)
    
    return app


async def start_server(host='127.0.0.1', port=3000):
    """Inicia el servidor mock"""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"✅ Mock server running at http://{host}:{port}/api/")
    return runner


async def stop_server(runner):
    """Detiene el servidor mock"""
    await runner.cleanup()
    print("🛑 Mock server stopped")


if __name__ == '__main__':
    # Ejecutar el servidor si se llama directamente
    async def main():
        runner = await start_server()
        try:
            # Mantener el servidor corriendo
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            await stop_server(runner)
    
    asyncio.run(main())
