# Propuestas de Mejora - Post Chaos Testing

Tras ejecutar el plan de pruebas de caos (5 escenarios), el cliente `EcoMarketClient v2.0` demostró ser robusto, manejando correctamente:
- Latencia alta (sin colgarse indefinidamente).
- Errores 503 intermitentes (lanzando `EcoMarketApiError`).
- JSON truncado y HTML inesperado (lanzando `EcoMarketDataError`).
- Timeouts extremos (abortando la conexión).

Sin embargo, para un entorno de producción de misión crítica, se proponen las siguientes mejoras:

## 1. Implementación de Retry con Backoff Exponencial
**Problema:** En el escenario de "Servidor Intermitente", el cliente falla inmediatamente. Si el usuario reintenta manualmente, funciona, pero esto afecta la UX.
**Propuesta:** Implementar un mecanismo de reintento automático para códigos 503, 502 y 504.
- **Detalle:** Usar `urllib3.util.retry.Retry` montado en la sesión de `requests`.
- **Configuración Sugerida:** 3 reintentos, factor de backoff de 0.5s (0.5s, 1s, 2s).

## 2. Circuit Breaker Pattern
**Problema:** Si el servidor está caído (Timeout continuo), el cliente sigue intentando y esperando el timeout completo en cada petición, consumiendo recursos.
**Propuesta:** Implementar un Circuit Breaker.
- **Detalle:** Si fallan X peticiones seguidas, "abrir el circuito" y fallar inmediatamente sin conectar durante un tiempo Y.

## 3. Streaming para Grandes Volúmenes
**Problema:** Aunque no se probó explícitamente, si el servidor devuelve una lista gigante, cargar todo en memoria con `response.json()` es ineficiente.
**Propuesta:** Añadir soporte para respuestas en streaming, parseando el JSON incrementalmente (usando `ijson` o similar).

## 4. Validaciones de esquema más estrictas
**Problema:** Actualmente solo validamos que sea JSON válido. Si el JSON es válido pero le faltan campos obligatorios (`id`, `precio`), el cliente podría fallar después.
**Propuesta:** Usar **Pydantic** para validar que la respuesta cumpla con el esquema esperado antes de retornarla.

## 5. Instrumentación y Métricas
**Propuesta:** Añadir hooks para emitir métricas (ej. Prometheus o StatsD) sobre latencia y tasa de errores, para monitoreo en tiempo real.
