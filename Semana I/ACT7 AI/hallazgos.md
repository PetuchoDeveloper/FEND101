# Hallazgos de Auditoría: Cliente EcoMarket

## Resumen Ejecutivo
El código actual es funcional para casos felices pero frágil en entornos de producción. Carece de manejo robusto de errores, permitiendo que problemas de red o del servidor pasen desapercibidos o resulten en estados inconsistentes. La seguridad es laxa en cuanto a validación de tipos de contenido.

## Detalle de Hallazgos

### 1. Manejo de Errores

🔴 **CRÍTICO**
- **Línea 75, 103, 138, 219:** `response.json()` se llama sin validar que la respuesta sea realmente JSON.
  - **Problema:** Si el servidor devuelve 500 (HTML) o la conexión es interceptada por un proxy, esto lanzará `json.decoder.JSONDecodeError` y hará crash del programa, ya que no está capturado en el bloque `try/except` (solo se capturan excepciones de `requests`).
  - **Solución:** Envolver `response.json()` en un bloque try-except específico o validar `Content-Type` antes de parsear.

🔴 **CRÍTICO**
- **Línea 91, 96, 107, 133, 154:** El uso de `return []` o `return None` ante errores ("swallowing exceptions").
  - **Problema:** El "código cliente" no tiene forma de distinguir entre "no hay productos" (lista vacía válida) y "error de red" (falla). Esto lleva a fallos silenciosos y difíciles de depurar.
  - **Solución:** Levantar excepciones personalizadas (`EcoMarketError`) para que quien use la librería decida cómo manejar el fallo.

🟡 **MEJORA**
- **Línea 31:** `TIMEOUT = 10`.
  - **Problema:** Un timeout global de 10 segundos puede ser mucho para operaciones rápidas o poco para subidas de archivos grandes.
  - **Solución:** Permitir configurar el timeout por llamada o tener defaults más granulares (connect vs read timeouts).

### 2. Seguridad Básica

🟡 **MEJORA**
- **Línea 300+:** Tokens hardcodeados en ejemplos o falta de manejo de tokens como secretos.
  - **Problema:** Fomenta malas prácticas. Si bien es un ejemplo, debería sugerir el uso de variables de entorno.
  - **Solución:** Usar `os.getenv('ECOMARKET_TOKEN')` en los ejemplos.

🔴 **CRÍTICO**
- **General:** Falta de validación del Content-Type de respuesta.
  - **Problema:** El cliente asume ciegamente que el servidor habla JSON.
  - **Solución:** Verificar `response.headers.get('Content-Type')` antes de procesar.

### 3. Mantenibilidad

🟢 **SUGERENCIA**
- **Línea 67, 127, 215:** Duplicación de lógica de headers y timeouts.
  - **Problema:** Si se necesita añadir un header global (ej. User-Agent), hay que editar todas las funciones.
  - **Solución:** Usar una clase `EcoMarketClient` con un objeto `requests.Session()` que mantenga configuración persistente.

🟢 **SUGERENCIA**
- **Línea 78-84, 141-148:** `print()` dentro de la lógica de negocio.
  - **Problema:** Viola la separación de responsabilidades. Una librería no debería "ensuciar" la salida estándar (`stdout`) a menos que sea una CLI explícita.
  - **Solución:** Usar el módulo `logging` para mensajes de diagnóstico y dejar que el consumidor decida si imprimir o guardar en archivo.

### 4. Conformidad

🟡 **MEJORA**
- **General:** Hardcoding de códigos de estado (201, 400, etc.).
  - **Solución:** Usar constantes o `requests.codes` para mayor legibilidad.
