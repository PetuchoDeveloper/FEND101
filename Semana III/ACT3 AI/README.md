# ACT3 AI: Cliente Asíncrono de EcoMarket

## 📋 Descripción

Migración del cliente HTTP de EcoMarket de síncrono (usando `requests`) a asíncrono (usando `aiohttp`). Este proyecto demuestra las ventajas del código asíncrono para operaciones I/O paralelas.

## 🎯 Objetivos Cumplidos

✅ Convertir todas las funciones CRUD a versiones asíncronas  
✅ Implementar `cargar_dashboard()` con ejecución paralela  
✅ Implementar `crear_multiples_productos()` con límite de concurrencia  
✅ Crear benchmarks comparativos sync vs async  
✅ Mantener toda la validación de datos sin cambios  

## 📁 Estructura del Proyecto

```
ACT3 AI/
├── cliente_ecomarket_async.py   # Cliente asíncrono principal
├── validadores.py                # Validación de respuestas (sin cambios)
├── url_builder.py                # Construcción segura de URLs (sin cambios)
├── benchmark_sync.py             # Benchmark del cliente síncrono
├── benchmark_async.py            # Benchmark del cliente asíncrono
├── benchmark.md                  # Reporte comparativo de rendimiento
└── README.md                     # Este archivo
```

## 🚀 Uso del Cliente Asíncrono

### Operaciones Básicas

```python
import asyncio
import aiohttp
import cliente_ecomarket_async as client

async def ejemplo_basico():
    # Crear una sesión para reutilizar conexiones
    async with aiohttp.ClientSession() as session:
        # Listar productos
        productos = await client.listar_productos(session)
        print(f"Total productos: {len(productos)}")
        
        # Obtener un producto específico
        producto = await client.obtener_producto(session, producto_id=1)
        print(f"Producto: {producto['nombre']}")
        
        # Crear un producto
        nuevo = await client.crear_producto(session, {
            "nombre": "Manzanas Orgánicas",
            "precio": 25.50,
            "categoria": "frutas"
        })
        print(f"Creado con ID: {nuevo['id']}")

# Ejecutar
asyncio.run(ejemplo_basico())
```

### Carga Paralela del Dashboard

```python
async def ejemplo_dashboard():
    # Carga 3 endpoints en paralelo (3x más rápido que secuencial)
    resultado = await client.cargar_dashboard()
    
    if resultado["errores"]:
        print(f"⚠️ Algunos endpoints fallaron:")
        for error in resultado["errores"]:
            print(f"  - {error['endpoint']}: {error['error']}")
    
    datos = resultado["datos"]
    if datos["productos"]:
        print(f"✅ Productos: {len(datos['productos'])}")
    if datos["categorias"]:
        print(f"✅ Categorías: {len(datos['categorias'])}")
    if datos["perfil"]:
        print(f"✅ Perfil: {datos['perfil'].get('nombre', 'N/A')}")

asyncio.run(ejemplo_dashboard())
```

### Creación Masiva de Productos

```python
async def ejemplo_creacion_masiva():
    productos_a_crear = [
        {"nombre": "Manzanas", "precio": 25.0, "categoria": "frutas"},
        {"nombre": "Leche", "precio": 30.0, "categoria": "lacteos"},
        {"nombre": "Miel", "precio": 80.0, "categoria": "miel"},
        # ... hasta 100 productos
    ]
    
    # Crea todos en paralelo, máximo 5 peticiones simultáneas
    creados, fallidos = await client.crear_multiples_productos(
        productos_a_crear,
        max_concurrencia=5
    )
    
    print(f"✅ Creados: {len(creados)}")
    print(f"❌ Fallidos: {len(fallidos)}")
    
    if fallidos:
        for fallo in fallidos:
            print(f"  - {fallo['datos']['nombre']}: {fallo['error']}")

asyncio.run(ejemplo_creacion_masiva())
```

## 📊 Benchmarking

### Ejecutar Benchmarks

**Requisito**: El servidor mock de EcoMarket debe estar corriendo.

```bash
# Terminal 1: Iniciar el servidor mock
cd "c:\Users\Petucho\Documents\Cosas de la escuela\SEMESTRE VI\FEND101"
python servidor_mock.py

# Terminal 2: Ejecutar benchmarks
cd "Semana III\ACT3 AI"

# Benchmark síncrono (secuencial)
python benchmark_sync.py

# Benchmark asíncrono (paralelo)
python benchmark_async.py
```

### Resultados Esperados

El cliente asíncrono debería ser **~3x más rápido** que el síncrono para la carga del dashboard (3 peticiones paralelas).

Ver [`benchmark.md`](./benchmark.md) para análisis detallado.

## 🔑 Características Clave

### 1. Funciones Asíncronas Convertidas

Todas las funciones CRUD del cliente síncrono fueron migradas:

| Función Original | Versión Asíncrona | Cambios Clave |
|-----------------|-------------------|--------------|
| `listar_productos()` | `listar_productos(session, ...)` | Recibe `session`, usa `async with` |
| `obtener_producto()` | `obtener_producto(session, id)` | Usa `await response.json()` |
| `crear_producto()` | `crear_producto(session, datos)` | Usa `session.post()` |
| `actualizar_producto_total()` | `actualizar_producto_total(session, id, datos)` | Usa `session.put()` |
| `actualizar_producto_parcial()` | `actualizar_producto_parcial(session, id, campos)` | Usa `session.patch()` |
| `eliminar_producto()` | `eliminar_producto(session, id)` | Usa `session.delete()` |

### 2. Nuevas Funciones Paralelas

#### `cargar_dashboard()`

- Ejecuta 3 peticiones **simultáneamente**
- Usa `asyncio.gather(..., return_exceptions=True)`
- Errores individuales no detienen otras peticiones
- Retorna dict con datos y errores separados

#### `crear_multiples_productos(lista, max_concurrencia=5)`

- Crea múltiples productos **en paralelo**
- Limita concurrencia con `asyncio.Semaphore`
- Retorna tupla: `(creados, fallidos)`
- Permite operaciones masivas eficientes

### 3. Manejo de Excepciones

Nuevas excepciones específicas de aiohttp:

```python
try:
    resultado = await client.listar_productos(session)
except client.TimeoutError:
    print("La petición tardó demasiado")
except client.ConexionError:
    print("No se pudo conectar con el servidor")
except asyncio.CancelledError:
    print("La tarea fue cancelada")
```

### 4. Validación Sin Cambios

Los módulos `validadores.py` y `url_builder.py` se copian sin modificaciones:
- Las funciones de validación son síncronas y compatibles con código async
- La construcción segura de URLs funciona igual

## 🆚 Sync vs Async: ¿Cuándo usar cada uno?

### Usa el Cliente Síncrono (requests) cuando:

- ✅ Necesitas simplicidad y código fácil de depurar
- ✅ Haces operaciones secuenciales por diseño
- ✅ Scripts de una sola tarea
- ✅ Testing unitario simple

### Usa el Cliente Asíncrono (aiohttp) cuando:

- ✅ Necesitas cargar múltiples recursos simultáneamente
- ✅ Operaciones masivas (bulk operations)
- ✅ Aplicaciones web con alta concurrencia
- ✅ El tiempo de respuesta es crítico
- ✅ Dashboards en tiempo real

## 📚 Conceptos Clave de Async/Await

### Event Loop

El event loop permite ejecutar múltiples operaciones I/O sin bloquear:

```
Síncrono (bloqueante):
  Petición 1 [█████ esperando █████] → 100ms
  Petición 2 [█████ esperando █████] → 100ms
  Petición 3 [█████ esperando █████] → 100ms
  Total: 300ms

Asíncrono (no bloqueante):
  Petición 1 [█ enviar ··waiting··] ──┐
  Petición 2 [█ enviar ··waiting··] ──┼─→ En paralelo
  Petición 3 [█ enviar ··waiting··] ──┘
  Total: ~100ms (tiempo de la más lenta)
```

### Connection Pooling

`ClientSession` reutiliza conexiones TCP:

```python
# ❌ Ineficiente (nueva conexión por petición)
requests.get(url1)
requests.get(url2)
requests.get(url3)

# ✅ Eficiente (reutiliza conexiones)
async with aiohttp.ClientSession() as session:
    await session.get(url1)  # Conexión inicial
    await session.get(url2)  # Reutiliza
    await session.get(url3)  # Reutiliza
```

## 🛠️ Requisitos

- Python 3.7+
- `aiohttp` (para cliente asíncrono)
- `requests` (para cliente síncrono y benchmarks)

Instalar dependencias:

```bash
pip install aiohttp requests
```

## 🔗 Referencias

- [Documentación de aiohttp](https://docs.aiohttp.org/)
- [asyncio — Asynchronous I/O](https://docs.python.org/3/library/asyncio.html)
- [Real Python: Async IO in Python](https://realpython.com/async-io-python/)
- Cliente síncrono original: `/Semana II/ACT9 AI/cliente_ecomarket.py`

## 👨‍💻 Autor

Creado como parte de FEND101 - Semana III - ACT3 AI
