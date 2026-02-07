"""
EcoMarket Chaos Web Client & Mock Server
=======================================
Interfaz web para probar el cliente robusto ante escenarios de caos.
Actúa también como un "Chaos Mock Server".

Autor: Antigravity AI
Fecha: 2026-01-28
"""

import time
import random
from flask import Flask, render_template_string, jsonify, request, Response
from ecomarket_client import EcoMarketClient, EcoMarketError

app = Flask(__name__)

# Configuración del Cliente para apuntar A SÍ MISMO (Mock del caos)
# Cuando el cliente de Python haga request, le pegará a /api/chaos
LOCAL_CHAOS_URL = "http://localhost:5000/api/chaos"

# Instancia global del cliente (apuntando al caos)
# Nota: En una app real no usaríamos una instancia global si guardara estado de usuario
client = EcoMarketClient(base_url=LOCAL_CHAOS_URL)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoMarket Chaos Lab</title>
    <style>
        body { font-family: sans-serif; background: #222; color: #eee; padding: 2rem; }
        .container { max-width: 800px; margin: 0 auto; }
        .card { background: #333; padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px; border: 1px solid #444; }
        h1 { color: #f66; text-align: center; }
        button { padding: 0.8rem; background: #f66; border: none; font-weight: bold; cursor: pointer; color: white; width: 100%; font-size: 1rem; border-radius: 4px;}
        button:hover { background: #f44; }
        select, input { padding: 0.5rem; width: 100%; margin-bottom: 1rem; background: #444; color: white; border: 1px solid #555; }
        .response { background: #111; padding: 1rem; font-family: monospace; white-space: pre-wrap; margin-top: 1rem; border-radius: 4px; min-height: 100px; }
        .row { display: flex; gap: 1rem; }
        .col { flex: 1; }
        .badge { display: inline-block; padding: 0.2rem 0.5rem; background: #555; font-size: 0.8rem; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 EcoMarket Chaos Lab</h1>
        
        <div class="card">
            <h3>⚙️ Configuración del Escenario</h3>
            <p>Elige qué desastre quieres simular en el servidor.</p>
            
            <div class="form-group">
                <label>Escenario de Caos:</label>
                <select id="scenario">
                    <option value="normal">✅ Normal (Sin fallos)</option>
                    <option value="latency">🐢 Red Lenta (Delay 3s)</option>
                    <option value="flaky">🎲 Servidor Intermitente (1/3 fail)</option>
                    <option value="truncated">✂️ JSON Truncado</option>
                    <option value="html">📄 HTML Inesperado</option>
                    <option value="timeout">⏱️ Timeout Extremo (15s)</option>
                </select>
            </div>
        </div>

        <div class="card">
            <h3>🚀 Ejecutar Prueba (Vía Python Client)</h3>
            <p>Esto enviará una instrucción al servidor Flask, el cual usará <code>ecomarket_client.py</code> para intentar conectarse al endpoint de caos.</p>
            <button onclick="runTest()">Disparar Petición</button>
            
            <div id="output" class="response">Esperando ejecución...</div>
        </div>
    </div>

    <script>
        async function runTest() {
            const scenario = document.getElementById('scenario').value;
            const output = document.getElementById('output');
            
            output.innerHTML = '⏳ Ejecutando cliente... (puede tardar si hay latencia)';
            
            try {
                // Llamamos a nuestro backend, diciéndole qué escenario de caos atacar
                const res = await fetch(`/run-client-test?scenario=${scenario}`);
                const data = await res.json();
                
                let log = `Status: ${data.status}\n\n`;
                if (data.error) {
                    log += `❌ Excepción Capturada:\n${data.error}\n\n`;
                    log += `Tipo: ${data.error_type}`;
                } else {
                    log += `✅ Resultado:\n${JSON.stringify(data.result, null, 2)}`;
                }
                output.innerText = log;
                
            } catch (e) {
                output.innerText = '❌ Error fatal en la UI: ' + e.message;
            }
        }
    </script>
</body>
</html>
"""

# =============================================================================
# RUTAS UI Y PROXY
# =============================================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/run-client-test')
def run_client_test():
    """
    Endpoint que ejecuta el cliente de Python real.
    """
    scenario = request.args.get('scenario', 'normal')
    
    # Configuramos el cliente para que apunte al endpoint con el escenario específico
    # Usamos query params para pasar el escenario al mock server
    # NOTA: En un caso real, la URL base no cambiaría, pero aquí "paramtrizamos" el caos
    
    try:
        # Hacemos la llamada usando el cliente refactorizado
        # Pasamos el escenario como query param para que el mock sepa qué hacer
        # (Esto es un truco para que el mismo endpoint /productos se comporte diferente)
        
        # OJO: Los kwargs extra se pasan a request, así que podemos enviar params
        # pero ecomarket_client.listar_productos solo acepta categoria/productor_id
        # Vamos a usar una categoría falsa para inyectar el escenario si es necesario
        # O simplemente hackeamos el _request para este test.
        
        # Mejor opción: El cliente permite params libres en _request, pero listar_productos no.
        # Vamos a llamar a una función privada para este test o usar 'categoria' como carrier.
        
        logger_params = {"chaos_scenario": scenario}
        
        # Hack: Pasamos el escenario como un parámetro extra que el cliente pasará al servidor
        # Necesitamos acceder a _request o usar un método público
        # Usaremos listar_productos y pasaremos el escenario en 'categoria' con un prefijo especial
        # o simplemente modificamos el mock para que lea header si pudiéramos.
        
        # Vamos a instanciar un cliente fresco para este request con un header custom si fuera posible,
        # pero el cliente v2.0 no expone headers dinámicos fácilmente sin tocar _request.
        
        # Solución simple: El Mock Server mirará un parámetro 'categoria' 
        # Si scenario != normal, lo inyectamos en la llamada
        
        cat_param = None
        if scenario != 'normal':
            cat_param = f"CHAOS:{scenario}"
            
        start_time = time.time()
        productos = client.listar_productos(categoria=cat_param)
        elapsed = time.time() - start_time
        
        return jsonify({
            "status": "success",
            "time": f"{elapsed:.2f}s",
            "result": productos
        })
        
    except EcoMarketError as e:
        return jsonify({
            "status": "handled_error",
            "error": str(e),
            "error_type": type(e).__name__
        })
    except Exception as e:
        return jsonify({
            "status": "unexpected_error",
            "error": str(e),
            "error_type": type(e).__name__
        })

# =============================================================================
# MOCK SERVER DEL CAOS (Backend)
# =============================================================================

@app.route('/api/chaos/productos', methods=['GET'])
def chaos_endpoint():
    """
    Endpoint que simula fallos según el parámetro 'categoria'.
    Formato de trigger: categoria="CHAOS:tipo"
    """
    start_time = time.time()
    categoria = request.args.get('categoria', '')
    
    scenario = "normal"
    if categoria.startswith("CHAOS:"):
        scenario = categoria.split(":")[1]
        
    print(f"👻 Chaos Server: Ejecutando escenario '{scenario}'")

    # 1. LATENCIA
    if scenario == "latency":
        time.sleep(3) # Espera 3s
        return jsonify([{"id": 1, "nombre": "Producto Lento"}])

    # 2. FLAKY (Intermitente)
    if scenario == "flaky":
        # Fallamos aleatoriamente (simulamos falla forzada para la demo)
        # Para garantizar que el test lo vea, vamos a fallar siempre si se pide flaky
        return jsonify({"mensaje": "Servidor sobrecargado", "codigo": "SERVICE_UNAVAILABLE"}), 503

    # 3. TRUNCATED (JSON Incompleto)
    if scenario == "truncated":
        # Devolvemos un string que parece JSON pero se corta
        # Flask Response directo
        return Response('{"items": [{"id": 1, "nombre": "Cortado...', content_type="application/json")

    # 4. HTML (Formato inesperado)
    if scenario == "html":
        return Response("<html><body><h1>Error de Gateway 502</h1></body></html>", status=200, mimetype="text/html")

    # 5. TIMEOUT
    if scenario == "timeout":
        time.sleep(15) # Más que el timeout del cliente (que es 10 por defecto en web o el que venga)
        return jsonify([{"id": 1, "nombre": "Nunca llegaré"}])

    # NORMAL
    return jsonify([
        {"id": 1, "nombre": "Manzanas Frescas", "precio": 1.50},
        {"id": 2, "nombre": "Pan Artesanal", "precio": 3.00}
    ])

if __name__ == '__main__':
    print("😈 Chaos Server Running on port 5000")
    app.run(debug=True, port=5000)
