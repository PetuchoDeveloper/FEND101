"""
Servidor Mock Simple para Testing de Throttling

Este servidor simula el API de EcoMarket para testing.
Responde a peticiones POST /api/productos con un delay aleatorio.
"""

from aiohttp import web
import asyncio
import random

productos_creados = []

async def crear_producto(request):
    """Endpoint POST /api/productos"""
    # Simular procesamiento variable
    delay = random.uniform(0.1, 0.3)
    await asyncio.sleep(delay)
    
    data = await request.json()
    
    # Agregar ID al producto
    producto = {
        "id": len(productos_creados) + 1,
        "nombre": data.get("nombre", ""),
        "descripcion": data.get("descripcion", ""),
        "precio": data.get("precio", 0),
        "categoria": data.get("categoria", ""),
        "stock": data.get("stock", 0),
        "fecha_creacion": "2026-02-11T23:43:00Z"
    }
    
    productos_creados.append(producto)
    
    return web.json_response(producto, status=201)

async def listar_productos(request):
    """Endpoint GET /api/productos"""
    await asyncio.sleep(0.1)
    return web.json_response(productos_creados)

async def stats(request):
    """Endpoint GET /stats para ver estadísticas"""
    return web.json_response({
        "total_productos": len(productos_creados),
        "productos": productos_creados[:10]  # Solo primeros 10
    })

def create_app():
    app = web.Application()
    app.router.add_post('/api/productos', crear_producto)
    app.router.add_get('/api/productos', listar_productos)
    app.router.add_get('/stats', stats)
    return app

if __name__ == '__main__':
    print("🚀 Servidor Mock iniciado en http://localhost:3000")
    print("   POST /api/productos - Crear producto")
    print("   GET  /api/productos - Listar productos")
    print("   GET  /stats - Ver estadísticas")
    
    app = create_app()
    web.run_app(app, host='localhost', port=3000)
