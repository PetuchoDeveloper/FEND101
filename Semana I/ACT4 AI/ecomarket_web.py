"""
EcoMarket API Web Client
========================
Una interfaz web para interactuar con la API de EcoMarket.
Permite capturar el tráfico de red usando las DevTools del navegador.

Para ejecutar:
    pip install flask requests
    python ecomarket_web.py

Luego abre http://localhost:5000 en tu navegador y usa F12 para abrir DevTools.

Autor: Estudiante FEND101
Fecha: 2026-01-28
"""

from flask import Flask, render_template_string, jsonify, request
import requests

app = Flask(__name__)

# Configuración
BASE_URL = "https://api.ecomarket.com/v1"
MOCK_URL = "https://jsonplaceholder.typicode.com"
TIMEOUT = 10
X_CLIENT_VERSION = "1.0"

# =============================================================================
# PLANTILLA HTML CON INTERFAZ MODERNA
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoMarket API Client</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 2rem;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
        }
        
        .tip {
            background: rgba(0, 217, 255, 0.1);
            border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .tip code {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
        }
        
        .endpoints {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        .card h3 {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .method {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: bold;
        }
        
        .method.get { background: #00875a; }
        .method.post { background: #0052cc; }
        
        .endpoint {
            font-family: 'Consolas', monospace;
            color: #00d9ff;
            font-size: 0.9rem;
        }
        
        .card p {
            color: #888;
            margin: 0.75rem 0;
            font-size: 0.9rem;
        }
        
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.25rem;
            font-size: 0.85rem;
            color: #aaa;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            font-size: 0.9rem;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #00d9ff;
        }
        
        button {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        button.primary {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #1a1a2e;
        }
        
        button.primary:hover {
            opacity: 0.9;
            transform: scale(1.02);
        }
        
        .response {
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.4);
            border-radius: 8px;
            font-family: 'Consolas', monospace;
            font-size: 0.8rem;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .response.success { border-left: 3px solid #00ff88; }
        .response.error { border-left: 3px solid #ff4757; }
        
        .status {
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        
        .status.success { color: #00ff88; }
        .status.error { color: #ff4757; }
        
        .loading {
            text-align: center;
            color: #00d9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 EcoMarket API Client</h1>
        <p class="subtitle">Interfaz web para capturar tráfico de API</p>
        
        <div class="tip">
            💡 <strong>Tip:</strong> Presiona <code>F12</code> para abrir DevTools, 
            luego ve a la pestaña <code>Network</code> para ver las peticiones HTTP.
        </div>
        
        <div class="endpoints">
            <!-- GET /productos -->
            <div class="card">
                <h3><span class="method get">GET</span> Listar Productos</h3>
                <span class="endpoint">/productos</span>
                <p>Obtiene la lista de productos. Usa la API mock de JSONPlaceholder.</p>
                
                <div class="form-group">
                    <label>Filtrar por categoría (opcional)</label>
                    <select id="categoria">
                        <option value="">-- Todas --</option>
                        <option value="frutas">Frutas</option>
                        <option value="verduras">Verduras</option>
                        <option value="lacteos">Lácteos</option>
                        <option value="miel">Miel</option>
                        <option value="conservas">Conservas</option>
                    </select>
                </div>
                
                <button class="primary" onclick="listarProductos()">
                    📋 Listar Productos
                </button>
                
                <div id="response-list" class="response" style="display: none;"></div>
            </div>
            
            <!-- GET /productos/{id} -->
            <div class="card">
                <h3><span class="method get">GET</span> Obtener Producto</h3>
                <span class="endpoint">/productos/{id}</span>
                <p>Obtiene un producto específico por su ID.</p>
                
                <div class="form-group">
                    <label>ID del producto</label>
                    <input type="text" id="producto-id" placeholder="1, 2, 3..." value="1">
                </div>
                
                <button class="primary" onclick="obtenerProducto()">
                    🔍 Buscar Producto
                </button>
                
                <div id="response-get" class="response" style="display: none;"></div>
            </div>
            
            <!-- POST /productos -->
            <div class="card">
                <h3><span class="method post">POST</span> Crear Producto</h3>
                <span class="endpoint">/productos</span>
                <p>Crea un nuevo producto (simulado con JSONPlaceholder).</p>
                
                <div class="form-group">
                    <label>Nombre del producto</label>
                    <input type="text" id="nombre" placeholder="Manzanas Orgánicas" value="Manzanas Orgánicas">
                </div>
                
                <div class="form-group">
                    <label>Precio</label>
                    <input type="number" id="precio" placeholder="4.50" value="4.50" step="0.01">
                </div>
                
                <div class="form-group">
                    <label>Categoría</label>
                    <select id="categoria-new">
                        <option value="frutas">Frutas</option>
                        <option value="verduras">Verduras</option>
                        <option value="lacteos">Lácteos</option>
                    </select>
                </div>
                
                <button class="primary" onclick="crearProducto()">
                    ➕ Crear Producto
                </button>
                
                <div id="response-post" class="response" style="display: none;"></div>
            </div>
            
            <!-- Mock API Test -->
            <div class="card">
                <h3><span class="method get">GET</span> API Mock Test</h3>
                <span class="endpoint">jsonplaceholder.typicode.com</span>
                <p>Prueba con una API real que siempre funciona.</p>
                
                <button class="primary" onclick="mockQuery()">
                    🧪 Probar API Mock
                </button>
                
                <div id="response-mock" class="response" style="display: none;"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Función auxiliar para mostrar respuestas
        function showResponse(elementId, data, isError = false) {
            const el = document.getElementById(elementId);
            el.style.display = 'block';
            el.className = 'response ' + (isError ? 'error' : 'success');
            el.innerHTML = '<div class="status ' + (isError ? 'error' : 'success') + '">' + 
                           (isError ? '❌ Error' : '✅ Éxito') + '</div>' +
                           JSON.stringify(data, null, 2);
        }
        
        function showLoading(elementId) {
            const el = document.getElementById(elementId);
            el.style.display = 'block';
            el.className = 'response';
            el.innerHTML = '<div class="loading">⏳ Cargando...</div>';
        }
        
        // GET /productos
        async function listarProductos() {
            showLoading('response-list');
            const categoria = document.getElementById('categoria').value;
            const params = categoria ? `?categoria=${categoria}` : '';
            
            try {
                const response = await fetch(`/api/productos${params}`);
                const data = await response.json();
                showResponse('response-list', data, !response.ok);
            } catch (error) {
                showResponse('response-list', { error: error.message }, true);
            }
        }
        
        // GET /productos/{id}
        async function obtenerProducto() {
            showLoading('response-get');
            const id = document.getElementById('producto-id').value;
            
            try {
                const response = await fetch(`/api/productos/${id}`);
                const data = await response.json();
                showResponse('response-get', data, !response.ok);
            } catch (error) {
                showResponse('response-get', { error: error.message }, true);
            }
        }
        
        // POST /productos
        async function crearProducto() {
            showLoading('response-post');
            
            const body = {
                nombre: document.getElementById('nombre').value,
                precio: parseFloat(document.getElementById('precio').value),
                categoria: document.getElementById('categoria-new').value
            };
            
            try {
                const response = await fetch('/api/productos', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Client-Version': '1.0'
                    },
                    body: JSON.stringify(body)
                });
                const data = await response.json();
                showResponse('response-post', data, !response.ok);
            } catch (error) {
                showResponse('response-post', { error: error.message }, true);
            }
        }
        
        // Mock API Test
        async function mockQuery() {
            showLoading('response-mock');
            
            try {
                const response = await fetch('/api/mock');
                const data = await response.json();
                showResponse('response-mock', data, !response.ok);
            } catch (error) {
                showResponse('response-mock', { error: error.message }, true);
            }
        }
    </script>
</body>
</html>
"""

# =============================================================================
# RUTAS DE LA API (PROXY)
# =============================================================================

@app.route('/')
def index():
    """Página principal con la interfaz web."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/productos', methods=['GET'])
def api_listar_productos():
    """Proxy para GET /productos - Usa JSONPlaceholder como mock."""
    categoria = request.args.get('categoria', '')
    
    try:
        # Usamos JSONPlaceholder como API mock
        response = requests.get(
            f"{MOCK_URL}/posts",
            params={'userId': 1} if categoria else {},
            headers={'X-Client-Version': X_CLIENT_VERSION},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        # Transformamos la respuesta para simular productos
        posts = response.json()[:5]  # Solo 5 items
        productos = []
        for post in posts:
            productos.append({
                'id': f"prod-{post['id']}",
                'nombre': post['title'][:30] + '...',
                'precio': round(post['id'] * 2.5, 2),
                'categoria': categoria or 'general',
                'disponible': True
            })
        
        return jsonify(productos)
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/productos/<producto_id>', methods=['GET'])
def api_obtener_producto(producto_id):
    """Proxy para GET /productos/{id} - Usa JSONPlaceholder como mock."""
    try:
        response = requests.get(
            f"{MOCK_URL}/posts/{producto_id}",
            headers={'X-Client-Version': X_CLIENT_VERSION},
            timeout=TIMEOUT
        )
        
        if response.status_code == 404:
            return jsonify({
                'codigo': 'NOT_FOUND',
                'mensaje': f'Producto {producto_id} no encontrado'
            }), 404
        
        response.raise_for_status()
        post = response.json()
        
        producto = {
            'id': f"prod-{post['id']}",
            'nombre': post['title'],
            'descripcion': post['body'],
            'precio': round(post['id'] * 2.5, 2),
            'categoria': 'frutas',
            'disponible': True
        }
        
        return jsonify(producto)
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/productos', methods=['POST'])
def api_crear_producto():
    """Proxy para POST /productos - Usa JSONPlaceholder como mock."""
    try:
        data = request.get_json()
        
        # Simulamos enviar a la API
        response = requests.post(
            f"{MOCK_URL}/posts",
            json={
                'title': data.get('nombre'),
                'body': f"Precio: ${data.get('precio')} - Categoría: {data.get('categoria')}",
                'userId': 1
            },
            headers={
                'Content-Type': 'application/json',
                'X-Client-Version': X_CLIENT_VERSION
            },
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        post = response.json()
        producto = {
            'id': f"prod-{post['id']}",
            'nombre': data.get('nombre'),
            'precio': data.get('precio'),
            'categoria': data.get('categoria'),
            'disponible': True,
            'mensaje': '¡Producto creado exitosamente!'
        }
        
        return jsonify(producto), 201
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mock', methods=['GET'])
def api_mock():
    """Endpoint de prueba con JSONPlaceholder."""
    try:
        response = requests.get(
            f"{MOCK_URL}/posts/1",
            headers={'X-Client-Version': X_CLIENT_VERSION},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🌿 EcoMarket Web Client")
    print("=" * 60)
    print()
    print("Abre tu navegador en: http://localhost:5000")
    print()
    print("💡 TIP: Presiona F12 para abrir DevTools y ver el tráfico de red")
    print()
    print("=" * 60)
    
    # Ejecutar servidor Flask en modo debug
    app.run(debug=True, port=5000)
