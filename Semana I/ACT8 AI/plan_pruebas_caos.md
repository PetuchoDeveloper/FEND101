# Plan de Pruebas de Caos: EcoMarket Client

Este plan define 5 escenarios de fallas controladas para verificar la robustez del cliente `ecomarket_client.py`.

## Escenarios de Prueba

### 1. Red Lenta (High Latency)
- **Simulación:** Servidor espera 5 segundos antes de responder.
- **Herramienta:** Mock server (`ecomarket_web.py`) con `time.sleep(5)`.
- **Comportamiento Esperado (Cliente Bien Diseñado):** La aplicación no se congela indefinidamente; el usuario recibe feedback visual de "Cargando...". Eventualmente completa exitosamente.
- **Comportamiento Mal Diseñado:** Interfaz congelada, usuario piensa que la app murió.

### 2. Servidor Intermitente (Flaky Server)
- **Simulación:** El servidor devuelve error 503 (Service Unavailable) en 1 de cada 3 peticiones de forma aleatoria.
- **Herramienta:** Contador de estado en Mock server o randomizado.
- **Comportamiento Esperado:** El cliente captura el 503 y muestra un mensaje amigable ("Servidor ocupado, intenta de nuevo") o reintenta automáticamente (Retry pattern).
- **Comportamiento Mal Diseñado:** Crash de la aplicación o pantalla en blanco.

### 3. Respuesta Truncada (Connection Severed)
- **Simulación:** El servidor cierra la conexión enviando un `Content-Length` erróneo o un JSON incompleto (ej. `{"id": 1, "nom...`).
- **Herramienta:** Mock server devuelve string JSON inválido manualmente.
- **Comportamiento Esperado:** `EcoMarketDataError` o error de parsing. El cliente no intenta usar datos corruptos.
- **Comportamiento Mal Diseñado:** `JSONDecodeError` no capturado (crash) o uso de datos parciales.

### 4. Respuesta con Formato Inesperado
- **Simulación:** El servidor devuelve HTML (página de error de Nginx/Apache) con status 200 OK.
- **Herramienta:** Mock server devuelve `<!DOCTYPE html>...` con header `Content-Type: text/html`.
- **Comportamiento Esperado:** El cliente detecta el `Content-Type` inválido o falla al parsear JSON, lanzando excepción controlada (`EcoMarketDataError`).
- **Comportamiento Mal Diseñado:** Intenta parsear HTML como JSON y crashea.

### 5. Timeout del Servidor
- **Simulación:** El servidor no responde nunca (o tarda 61 segundos, superando el timeout del cliente de 10s).
- **Herramienta:** `time.sleep(65)` en el endpoint.
- **Comportamiento Esperado:** El cliente aborta la conexión a los 10s (o el configurado) lanzando `EcoMarketNetworkError`.
- **Comportamiento Mal Diseñado:** El cliente se queda colgado para siempre (hang) bloqueando el hilo principal.

## Estrategia de Ejecución
1. Se levantará `ecomarket_web.py` que actuará como **Mock Server del Caos** en `/api/chaos`.
2. Se ejecutará `tests_caos.py` que instanciará `EcoMarketClient` apuntando a este servidor local.
3. Se verificarán las excepciones lanzadas.
