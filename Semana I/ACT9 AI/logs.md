# Auditoría de Logs (Capa de Observabilidad)

A continuación se presentan ejemplos reales de logs capturados durante las pruebas de la capa de observabilidad implementada en `EcoMarketClient v3.0`.

## 1. Petición Exitosa (Happy Path)
**Nivel:** INFO / DEBUG (Detalle)

```text
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | Initiating GET transaction to https://api.ecomarket.com/v1/productos
2026-01-28 22:40:01-0700 | INFO  | EcoMarketClient | GET https://api.ecomarket.com/v1/productos | Status: 200 | Time: 0.15ms | Size: 9b
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | >>> Request Headers: {'User-Agent': 'EcoMarketClient/3.0-obs', 'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': '******'}
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | <<< Response Headers: {'Content-Type': 'application/json'}
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | <<< Response Body: {"id": 1}
```

> **Nota:** La cabecera `Authorization` fue correctamente ofuscada como `******`.

## 2. Error de Seguridad (401 Unauthorized)
**Nivel:** WARNING

```text
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | Initiating GET transaction to https://api.ecomarket.com/v1/productos
2026-01-28 22:40:01-0700 | WARNING | EcoMarketClient | GET https://api.ecomarket.com/v1/productos | Status: 401 | Time: 0.12ms | Size: 25b | Error: [401] Unauthorized
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | >>> Request Headers: {'User-Agent': 'EcoMarketClient/3.0-obs', 'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': '******'}
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | <<< Response Headers: {}
2026-01-28 22:40:01-0700 | DEBUG | EcoMarketClient | <<< Response Body: {"mensaje": "Unauthorized"}
```

## 3. Integración con Servicios de Cloud Logging

Para llevar estos logs a la nube (AWS CloudWatch, Datadog, ELK), no es necesario modificar el código del cliente. Se recomienda usar la configuración de logging de la aplicación consumidora:

### Estrategia Recomendada: JSON Formatter en Stdout

Configurar el `logging` de la app principal para emitir JSON en lugar de texto plano. Esto permite que agentes como Fluentd o Datadog Agent parseen automáticamente los campos.

**Ejemplo de configuración externa:**

```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

**Resultado:**
```json
{
  "asctime": "2026-01-28 22:40:01-0700",
  "name": "EcoMarketClient",
  "levelname": "INFO",
  "message": "GET https://api.ecomarket.com/v1/productos | Status: 200 | Time: 0.15ms | Size: 9b",
  "method": "GET",
  "url": "https://api.ecomarket.com/v1/productos",
  "status_code": 200,
  "duration_ms": 0.15
}
```
*(Nota: Para obtener campos separados como `method` y `duration_ms` en el JSON root, se debe usar `extra={...}` en la llamada al logger dentro de `run_transaction`)*
