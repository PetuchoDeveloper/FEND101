# Sistema de Control de Tráfico HTTP - ACT5 AI

## 🎯 Objetivo

Implementar un sistema robusto de **limitación de concurrencia** y **rate limiting** para el cliente HTTP asíncrono de EcoMarket, diseñado como un ingeniero de control de tráfico profesional.

## 🚨 El Problema

Cuando `crear_multiples_productos()` lanza 100 peticiones POST simultáneas, puede causar:

1. **Sobrecarga del Servidor**: El servidor tiene límite de 20 conexiones concurrentes
2. **Agotamiento de File Descriptors**: El cliente puede quedarse sin file handles
3. **Violación de Rate Limits**: El API tiene máximo de 30 peticiones por segundo
4. **Conexiones fallidas**: Timeouts y errores por saturación

### Ejemplo del Problema

```python
# ❌ Sin control de tráfico
async def crear_100_productos():
    tareas = [crear_producto(p) for p in productos]  
    # ¡100 peticiones simultáneas! 💥
    return await asyncio.gather(*tareas)
```

**Resultado**: Servidor saturado, errores de conexión, peticiones rechazadas.

## ✅ La Solución

Sistema de throttling con **tres componentes reutilizables**:

### 1. **ConcurrencyLimiter** (usando `asyncio.Semaphore`)

Limita el número de peticiones **simultáneas**:

```python
limiter = ConcurrencyLimiter(max_concurrent=10)

async with limiter.acquire():
    # Máximo 10 peticiones aquí simultáneamente
    response = await session.get(url)
```

**Características**:
- ✅ Context manager: `async with limiter.acquire()`
- ✅ Logging de peticiones en vuelo
- ✅ Thread-safe usando `asyncio.Lock`

### 2. **RateLimiter** (algoritmo Token Bucket)

Limita el **rate de peticiones por segundo**:

```python
limiter = RateLimiter(max_per_second=20)

async with limiter.acquire():
    # Máximo 20 peticiones por segundo
    response = await session.get(url)
```

**Algoritmo Token Bucket**:
1. Bucket tiene capacidad máxima de tokens (ej: 20)
2. Se regeneran tokens a rate constante (20/segundo)
3. Cada petición consume 1 token
4. Si no hay tokens disponibles, la petición **espera** (no se rechaza)

**Ventajas**:
- ✅ Maneja bursts controlados
- ✅ Las peticiones esperan en cola, no fallan
- ✅ Logging de tiempo de espera por petición

### 3. **ThrottledClient** (combinación de ambos)

Cliente completo que aplica **ambos límites simultáneamente**:

```python
client = ThrottledClient(
    max_concurrent=10,      # Máximo 10 peticiones simultáneas
    max_per_second=20       # Máximo 20 peticiones por segundo
)

# Todas las operaciones CRUD respetan los límites automáticamente
productos = await client.listar_productos()
nuevo = await client.crear_producto(datos)
```

**Orden de aplicación**:
1. Primero: Rate limiting (espera por token)
2. Segundo: Concurrency limiting (espera por slot)
3. Finalmente: Ejecuta la petición

## 📊 Demostración

### Test Completo con Visualización

```bash
python test_throttle_demo.py --test=full --num=50 --concurrent=10 --rate=20
```

**Genera**:
- 📈 Gráfica 1: Peticiones en vuelo vs tiempo (nunca excede límite)
- 📊 Gráfica 2: Peticiones por segundo (respeta rate limit)
- ⏱️ Gráfica 3: Duración y tiempo de espera por petición
- 📝 Reporte detallado en consola

### Comparación Con/Sin Throttling

```bash
python test_throttle_demo.py --test=compare --num=50
```

**Muestra**:
- Tiempo total de ejecución
- Throughput efectivo
- Número de errores (sin throttling típicamente tiene más errores)
- Verificación de cumplimiento de límites

## 🔍 Ejemplo de Uso

```python
import asyncio
from throttle import ThrottledClient

async def main():
    # Configurar límites
    async with ThrottledClient(
        max_concurrent=10,      # Límite de concurrencia
        max_per_second=20       # Límite de rate
    ) as client:
        
        # Crear 50 productos
        productos = []
        for i in range(50):
            producto = {
                "nombre": f"Producto {i}",
                "precio": 100 + i,
                "categoria": "test",
                "stock": 10
            }
            productos.append(producto)
        
        # Lanzar todas las tareas
        # Los limitadores se aplican automáticamente
        tareas = [client.crear_producto(p) for p in productos]
        resultados = await asyncio.gather(*tareas)
        
        # Ver métricas
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Average wait time: {metrics['average_wait_time']:.3f}s")
        print(f"Max concurrent: {metrics['max_concurrent']}")

asyncio.run(main())
```

## 📁 Estructura de Archivos

```
ACT5 AI/
├── throttle.py                 # 🔧 Implementación principal
│   ├── ConcurrencyLimiter      # Limita peticiones concurrentes
│   ├── RateLimiter             # Limita peticiones por segundo
│   └── ThrottledClient         # Cliente completo con CRUD
│
├── test_throttle_demo.py       # 🧪 Testing y demostración
│   ├── ThrottleMonitor         # Captura métricas en tiempo real
│   ├── plot_metrics()          # Genera gráficas matplotlib
│   └── Comparación tests       # Con/sin throttling
│
├── validadores.py              # ✅ Validación de JSON (de ACT4)
├── url_builder.py              # 🔒 Construcción segura de URLs (de ACT4)
├── README.md                   # 📖 Este archivo
└── diagramas.md                # 📊 Diagramas temporales
```

## 🎨 Gráficas Generadas

El script de testing genera automáticamente gráficas con matplotlib:

### 1. Peticiones en Vuelo vs Tiempo
- Muestra cuántas peticiones están ejecutándose en cada momento
- Línea roja indica el límite configurado
- Área sombreada muestra el uso real
- **Verificación**: Nunca debe exceder la línea roja

### 2. Peticiones por Segundo
- Histograma de peticiones agrupadas por segundo
- Línea roja indica el rate limit
- **Verificación**: Ninguna barra debe exceder la línea roja

### 3. Duración y Tiempo de Espera
- Scatter plot de cada petición
- Naranja: Duración total
- Rojo: Tiempo de espera por rate limit
- Muestra distribución y promedio

## 🧪 Verificación de Límites

El sistema verifica automáticamente:

### ✅ Límite de Concurrencia
```
✅ Concurrencia: 10/10 (RESPETADO)
```
**Criterio**: Nunca más de `max_concurrent` peticiones simultáneas

### ✅ Límite de Rate
```
✅ Rate Limit: 20/20/s (RESPETADO)
```
**Criterio**: Nunca más de `max_per_second` peticiones en 1 segundo

### ❌ Violación Detectada
```
⚠️ LÍMITE EXCEDIDO: 25 > 20
```
Si se detecta violación, se resalta en rojo en las gráficas

## 🎓 Conceptos Clave

### Context Manager Pattern
```python
async with limiter.acquire():
    # El limitador garantiza:
    # 1. Adquisición antes de entrar
    # 2. Liberación al salir (incluso si hay excepciones)
    await hacer_peticion()
```

### Token Bucket Algorithm
```
Bucket: [🪙🪙🪙🪙🪙] (5 tokens)
         ↓
Petición 1: consume 1 token → [🪙🪙🪙🪙_]
Petición 2: consume 1 token → [🪙🪙🪙__]
         ↓
Después de 1 segundo:
Regenera 5 tokens → [🪙🪙🪙🪙🪙] (max 5)
```

### Composición de Limitadores
```python
# Orden de aplicación:
async with rate_limiter.acquire():        # 1. Espera por token
    async with concurrency_limiter.acquire():  # 2. Espera por slot
        await hacer_peticion()             # 3. Ejecuta
```

## 📈 Métricas Capturadas

El `ThrottledClient` registra:

- `total_requests`: Total de peticiones hechas
- `successful_requests`: Peticiones exitosas
- `failed_requests`: Peticiones fallidas
- `in_flight`: Peticiones actualmente en ejecución
- `average_wait_time`: Tiempo promedio de espera por rate limit
- `total_bytes_sent`: Bytes enviados
- `total_bytes_received`: Bytes recibidos

Acceso a métricas:
```python
metrics = client.get_metrics()
print(f"Throughput efectivo: {metrics['successful_requests'] / tiempo_total:.2f}/s")
```

## 🚀 Ventajas de Este Diseño

1. **✅ Reutilizable**: Los limitadores son decoradores/context managers genéricos
2. **✅ Composable**: Se pueden combinar múltiples limitadores
3. **✅ Observable**: Logging detallado y métricas
4. **✅ No-invasivo**: La lógica CRUD no cambia, el throttling es transparente
5. **✅ Configurable**: Límites ajustables en runtime
6. **✅ Resiliente**: Maneja excepciones correctamente

## 🔧 Configuración Recomendada

Para el EcoMarket API:

```python
client = ThrottledClient(
    max_concurrent=10,      # No agotar file descriptors
    max_per_second=20       # Respetar rate limit del API
)
```

Para desarrollo/testing local:

```python
client = ThrottledClient(
    max_concurrent=5,       # Menos concurrencia
    max_per_second=10       # Rate más conservador
)
```

## 📚 Referencias

- **asyncio.Semaphore**: [Documentación Python](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore)
- **Token Bucket Algorithm**: [Wikipedia](https://en.wikipedia.org/wiki/Token_bucket)
- **Context Managers**: [PEP 343](https://www.python.org/dev/peps/pep-0343/)

## 🎯 Conclusión

Este sistema de throttling:
- ✅ Previene sobrecarga del servidor
- ✅ Evita agotamiento de recursos del cliente
- ✅ Respeta rate limits del API
- ✅ Es reutilizable y extensible
- ✅ Incluye visualización de métricas
- ✅ Sigue patrones de diseño profesionales

**Diseñado como un ingeniero de control de tráfico profesional.** 🚦
