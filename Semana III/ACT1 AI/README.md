# Modelos de Asincronía para Clientes HTTP

## 📚 Contenido

Este directorio contiene material educativo sobre **3 modelos de concurrencia** aplicados a clientes HTTP:

1. **Callbacks** (`cliente_callbacks.py`) - Usando `concurrent.futures` con callbacks
2. **Futures** (`cliente_futures.py`) - Usando `ThreadPoolExecutor` explícitamente  
3. **Async/Await** (`cliente_async.py`) - Usando `asyncio + aiohttp`

## 🎯 Escenario

Todos los clientes implementan el **mismo escenario**: cargar simultáneamente:
- Productos (`GET /api/productos`)
- Categorías (`GET /api/categorias`)
- Perfil de usuario (`GET /api/perfil`)

## 📂 Archivos

| Archivo | Propósito |
|---------|-----------|
| `cliente_callbacks.py` | Implementación con modelo de callbacks |
| `cliente_futures.py` | Implementación con modelo de futures |
| `cliente_async.py` | Implementación con modelo async/await |
| `benchmark_comparativo.py` | Script para medir y comparar rendimiento |
| `analisis_modelos.md` | **Documento principal** con análisis completo |
| `requirements.txt` | Dependencias necesarias |

## 🚀 Cómo Ejecutar

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Iniciar el servidor mock (en terminal separada)

```bash
cd ../..
python servidor_mock.py
```

El servidor se ejecutará en `http://localhost:3000/api/`

### 3. Ejecutar cada cliente individualmente

```bash
# Modelo de Callbacks
python cliente_callbacks.py

# Modelo de Futures
python cliente_futures.py

# Modelo Async/Await
python cliente_async.py
```

### 4. Ejecutar el benchmark comparativo

```bash
python benchmark_comparativo.py
```

Esto ejecutará los 3 modelos múltiples veces y mostrará una tabla comparativa de tiempos.

## 📖 Análisis Completo

Lee [`analisis_modelos.md`](analisis_modelos.md) para:
- Explicación detallada de cada modelo
- Ventajas y desventajas específicas para clientes HTTP
- Manejo de errores individuales (escenario: timeout en `/categorias`)
- Tabla comparativa de rendimiento
- **Recomendación final para EcoMarket**

## 🎓 Conceptos Clave por Modelo

### Callbacks
- `.submit()` lanza tarea, retorna `Future`
- `.add_done_callback()` registra función a ejecutar cuando termine
- Cada callback maneja su resultado independently

### Futures
- `.submit()` retorna `Future` object
- `as_completed()` itera sobre futures conforme terminan
- `.result()` obtiene el valor (bloquea si no terminó)
- `wait()` espera a conjunto completo de futures

### Async/Await
- `async def` define coroutine
- `await` pausa hasta que operación async termine
- `asyncio.gather()` lanza múltiples coroutines en paralelo
- `return_exceptions=True` retorna excepciones como valores

## ⚠️ Escenarios de Error

Todos los clientes incluyen ejemplos (comentados) de qué pasa cuando `/categorias` falla con timeout. Descomentalas funciones demo para verlo en acción.

**Respuesta**: En los 3 modelos, los resultados de `/productos` y `/perfil` **NO se pierden** si se maneja correctamente.

## 🏆 Resultado del Benchmark

Ejecuta el benchmark para ver resultados reales. En general:
- **Los 3 modelos tienen rendimiento similar** para pocas peticiones (3 endpoints)
- **Async/Await es ligeramente más rápido** por evitar overhead de threads
- **Async/Await escala mejor** con cientos/miles de peticiones concurrentes

## 💡 Recomendación

Para **EcoMarket**: **Async/Await** es la mejor opción por:
- Código más limpio y mantenible
- Escalabilidad superior
- Manejo de errores elegante
- Ecosistema moderno de Python

Ver justificación detallada en [`analisis_modelos.md`](analisis_modelos.md).
