"""
Servidor Mock para EcoMarket - Solo para pruebas locales
Ejecutar: python servidor_mock.py
Endpoint: http://localhost:3000/api/productos
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Base de datos en memoria (se reinicia al detener el servidor)
productos_db = {
    1: {
        "id": 1,
        "nombre": "Bolsa Reutilizable",
        "precio": 15.99,
        "categoria": "accesorios",
        "descripcion": "Bolsa ecológica de algodón",
        "stock": 100
    },
    2: {
        "id": 2,
        "nombre": "Botella de Acero",
        "precio": 29.99,
        "categoria": "bebidas",
        "descripcion": "Botella térmica 500ml",
        "stock": 50
    },
    3: {
        "id": 3,
        "nombre": "Cepillo de Bambú",
        "precio": 8.50,
        "categoria": "higiene",
        "descripcion": "Cepillo dental biodegradable",
        "stock": 200
    }
}

# Contador para IDs autoincrementales
next_id = 4


def log_request(method, path, status):
    """Imprime información de la petición en consola"""
    status_emoji = "✅" if status < 400 else "❌"
    print(f"{status_emoji} [{method}] {path} -> {status}")

# ============================================================
# ENDPOINT ESPECIAL: Producto con datos inválidos (para testing)
# ============================================================

@app.route('/api/productos/invalido', methods=['GET'])
def obtener_producto_invalido():
    """
    GET /api/productos/invalido - Retorna un producto con PRECIO NEGATIVO.
    Usado para probar que el cliente detecta respuestas inválidas.
    """
    producto_corrupto = {
        "id": 999,
        "nombre": "Producto Corrupto",
        "precio": -15.00,  # ❌ PRECIO NEGATIVO INVÁLIDO
        "categoria": "frutas",
        "descripcion": "Este producto tiene precio negativo para testing"
    }
    
    log_request('GET', '/api/productos/invalido', 200)
    return jsonify(producto_corrupto), 200

# ============================================================
# ENDPOINTS CRUD
# ============================================================

@app.route('/api/productos', methods=['GET'])
def listar_productos():
    """GET /api/productos - Lista todos los productos"""
    categoria = request.args.get('categoria')
    orden = request.args.get('orden')
    delay = request.args.get('delay', type=int)
    
    # Simular delay si se especifica (para pruebas de timeout)
    if delay:
        import time
        time.sleep(delay)
    
    resultado = list(productos_db.values())
    
    # Filtrar por categoría si se especifica
    if categoria:
        resultado = [p for p in resultado if p.get('categoria') == categoria]
    
    # Ordenar si se especifica
    if orden == 'precio_asc':
        resultado.sort(key=lambda x: x.get('precio', 0))
    elif orden == 'precio_desc':
        resultado.sort(key=lambda x: x.get('precio', 0), reverse=True)
    
    log_request('GET', '/api/productos', 200)
    return jsonify(resultado), 200


@app.route('/api/categorias', methods=['GET'])
def listar_categorias():
    """GET /api/categorias - Lista todas las categorías disponibles"""
    delay = request.args.get('delay', type=int)
    
    # Simular delay si se especifica (para pruebas de timeout)
    if delay:
        import time
        time.sleep(delay)
    
    categorias = [
        {
            "id": 1,
            "nombre": "accesorios",
            "descripcion": "Accesorios ecológicos",
            "total_productos": len([p for p in productos_db.values() if p.get('categoria') == 'accesorios'])
        },
        {
            "id": 2,
            "nombre": "bebidas",
            "descripcion": "Contenedores para bebidas",
            "total_productos": len([p for p in productos_db.values() if p.get('categoria') == 'bebidas'])
        },
        {
            "id": 3,
            "nombre": "higiene",
            "descripcion": "Productos de higiene personal",
            "total_productos": len([p for p in productos_db.values() if p.get('categoria') == 'higiene'])
        }
    ]
    
    log_request('GET', '/api/categorias', 200)
    return jsonify(categorias), 200


@app.route('/api/perfil', methods=['GET'])
def obtener_perfil():
    """GET /api/perfil - Obtiene el perfil del usuario actual"""
    delay = request.args.get('delay', type=int)
    
    # Simular delay si se especifica (para pruebas de timeout)
    if delay:
        import time
        time.sleep(delay)
    
    perfil = {
        "id": 1,
        "nombre": "Usuario Demo",
        "email": "demo@ecomarket.com",
        "preferencias": {
            "categoria_favorita": "accesorios",
            "notificaciones": True
        },
        "direccion": {
            "calle": "Av. Ecológica 123",
            "ciudad": "Ciudad Verde",
            "codigo_postal": "12345"
        },
        "fecha_registro": "2024-01-15T10:30:00Z"
    }
    
    log_request('GET', '/api/perfil', 200)
    return jsonify(perfil), 200


@app.route('/api/productos/<int:producto_id>', methods=['GET'])
def obtener_producto(producto_id):
    """GET /api/productos/{id} - Obtiene un producto específico"""
    if producto_id not in productos_db:
        log_request('GET', f'/api/productos/{producto_id}', 404)
        return jsonify({"error": "Producto no encontrado"}), 404
    
    log_request('GET', f'/api/productos/{producto_id}', 200)
    return jsonify(productos_db[producto_id]), 200


@app.route('/api/productos', methods=['POST'])
def crear_producto():
    """POST /api/productos - Crea un nuevo producto"""
    global next_id
    
    if not request.is_json:
        log_request('POST', '/api/productos', 400)
        return jsonify({"error": "Content-Type debe ser application/json"}), 400
    
    datos = request.get_json()
    
    # Validar campos requeridos
    if not datos.get('nombre'):
        log_request('POST', '/api/productos', 400)
        return jsonify({"error": "El campo 'nombre' es requerido"}), 400
    
    # Verificar duplicados por nombre
    for p in productos_db.values():
        if p['nombre'].lower() == datos.get('nombre', '').lower():
            log_request('POST', '/api/productos', 409)
            return jsonify({"error": f"Ya existe un producto con el nombre '{datos['nombre']}'"}), 409
    
    # Crear producto
    nuevo_producto = {
        "id": next_id,
        "nombre": datos.get('nombre'),
        "precio": datos.get('precio', 0),
        "categoria": datos.get('categoria', 'general'),
        "descripcion": datos.get('descripcion', ''),
        "stock": datos.get('stock', 0)
    }
    
    productos_db[next_id] = nuevo_producto
    next_id += 1
    
    log_request('POST', '/api/productos', 201)
    return jsonify(nuevo_producto), 201


@app.route('/api/productos/<int:producto_id>', methods=['PUT'])
def actualizar_producto_total(producto_id):
    """PUT /api/productos/{id} - Actualización total del producto"""
    if producto_id not in productos_db:
        log_request('PUT', f'/api/productos/{producto_id}', 404)
        return jsonify({"error": "Producto no encontrado"}), 404
    
    if not request.is_json:
        log_request('PUT', f'/api/productos/{producto_id}', 400)
        return jsonify({"error": "Content-Type debe ser application/json"}), 400
    
    datos = request.get_json()
    
    # Verificar conflicto de nombre con otros productos
    for pid, p in productos_db.items():
        if pid != producto_id and p['nombre'].lower() == datos.get('nombre', '').lower():
            log_request('PUT', f'/api/productos/{producto_id}', 409)
            return jsonify({"error": f"Ya existe otro producto con el nombre '{datos['nombre']}'"}), 409
    
    # Reemplazo total (PUT semántica)
    productos_db[producto_id] = {
        "id": producto_id,
        "nombre": datos.get('nombre', ''),
        "precio": datos.get('precio', 0),
        "categoria": datos.get('categoria', 'general'),
        "descripcion": datos.get('descripcion', ''),
        "stock": datos.get('stock', 0)
    }
    
    log_request('PUT', f'/api/productos/{producto_id}', 200)
    return jsonify(productos_db[producto_id]), 200


@app.route('/api/productos/<int:producto_id>', methods=['PATCH'])
def actualizar_producto_parcial(producto_id):
    """PATCH /api/productos/{id} - Actualización parcial del producto"""
    if producto_id not in productos_db:
        log_request('PATCH', f'/api/productos/{producto_id}', 404)
        return jsonify({"error": "Producto no encontrado"}), 404
    
    if not request.is_json:
        log_request('PATCH', f'/api/productos/{producto_id}', 400)
        return jsonify({"error": "Content-Type debe ser application/json"}), 400
    
    datos = request.get_json()
    
    # Verificar conflicto de nombre si se está actualizando
    if 'nombre' in datos:
        for pid, p in productos_db.items():
            if pid != producto_id and p['nombre'].lower() == datos['nombre'].lower():
                log_request('PATCH', f'/api/productos/{producto_id}', 409)
                return jsonify({"error": f"Ya existe otro producto con el nombre '{datos['nombre']}'"}), 409
    
    # Actualización parcial (solo campos enviados)
    for campo, valor in datos.items():
        if campo != 'id':  # No permitir cambiar el ID
            productos_db[producto_id][campo] = valor
    
    log_request('PATCH', f'/api/productos/{producto_id}', 200)
    return jsonify(productos_db[producto_id]), 200


@app.route('/api/productos/<int:producto_id>', methods=['DELETE'])
def eliminar_producto(producto_id):
    """DELETE /api/productos/{id} - Elimina un producto"""
    if producto_id not in productos_db:
        log_request('DELETE', f'/api/productos/{producto_id}', 404)
        return jsonify({"error": "Producto no encontrado"}), 404
    
    del productos_db[producto_id]
    
    log_request('DELETE', f'/api/productos/{producto_id}', 204)
    return '', 204


# ============================================================
# SERVIDOR
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🌿 EcoMarket Mock Server")
    print("=" * 50)
    print(f"📍 URL Base: http://localhost:3000/api/")
    print(f"📦 Productos iniciales: {len(productos_db)}")
    print("-" * 50)
    print("Endpoints disponibles:")
    print("  GET    /api/productos          - Listar productos")
    print("  GET    /api/productos/{id}     - Obtener producto")
    print("  POST   /api/productos          - Crear producto")
    print("  PUT    /api/productos/{id}     - Actualizar (total)")
    print("  PATCH  /api/productos/{id}     - Actualizar (parcial)")
    print("  DELETE /api/productos/{id}     - Eliminar producto")
    print("  GET    /api/categorias         - Listar categorías")
    print("  GET    /api/perfil             - Obtener perfil usuario")
    print("-" * 50)
    print("Presiona Ctrl+C para detener el servidor\n")
    
    app.run(host='localhost', port=3000, debug=True)

