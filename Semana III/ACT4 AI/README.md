# ACT4 AI: Control de Flujo Asíncrono Avanzado

## 📋 Descripción

Implementación avanzada de control de flujo asíncrono para el cliente EcoMarket. Este proyecto extiende ACT3 AI con tres características fundamentales:

1. **Timeout individual por petición** (configurable por función)
2. **Cancelación granular de tareas en grupo**
3. **Carga con prioridad** usando `asyncio.wait()`

## 🎯 Objetivos Cumplidos

✅ Wrapper `ejecutar_con_timeout()` para timeouts individuales  
✅ Timeouts configurables por función (productos=5s, categorías=3s, perfil=2s)  
✅ Función `cancel_remaining()` para cancelación de tareas  
✅ Cancelación condicional (401 → cancelar todo)  
✅ `cargar_con_prioridad()` con procesamiento incremental  
✅ Dashboard parcial cuando llegan peticiones críticas  
✅ Tests completos con diagramas temporales  
✅ Documentación exhaustiva  

## 📁 Estructura del Proyecto

```
ACT4 AI/
├── coordinador_async.py         # Coordinador asíncrono con control de flujo avanzado
├── validadores.py                 # Validación de respuestas (copiado de ACT3)
├── url_builder.py                # Construcción segura de URLs (copiado de ACT3)
├── test_timeout_individual.py    # Tests de timeout individual
├── test_cancelacion_grupo.py     # Tests de cancelación en grupo
├── test_carga_prioridad.py       # Tests de carga con prioridad
├── diagramas.md                  # Diagramas temporales visuales
└── README.md                     # Este archivo
```

## 🔑 Características Principales

### 1. Timeout Individual por Petición

#### Problema que Resuelve

En ACT3 AI, **todas las peticiones compartían el mismo timeout global** (10s). Esto era inflexible porque:
- Peticiones rápidas (perfil) se beneficiarían de timeouts cortos
- Peticiones lentas (productos) necesitan más tiempo
- Un timeout global es "talla única" que no se ajusta a la realidad

#### Solución: `ejecutar_con_timeout()`

```python
async def ejecutar_con_timeout(
    coroutine, 
    timeout_segundos: float,
    nombre_operacion: str = "operación"
) -> Any:
    """
    Wrapper que envuelve cualquier petición con asyncio.wait_for().
    
    Si una petición excede SU timeout, las demás continúan normalmente.
    """
    try:
        return await asyncio.wait_for(coroutine, timeout=timeout_segundos)
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"La operación '{nombre_operacion}' excedió el timeout de {timeout_segundos}s"
        )
```

#### Ejemplo de Uso

```python
async with aiohttp.ClientSession() as session:
    # Cada petición tiene su propio timeout
    productos = await listar_productos(session, timeout=5.0)      # 5 segundos
    categorias = await obtener_categorias(session, timeout=3.0)   # 3 segundos
    perfil = await obtener_perfil(session, timeout=2.0)           # 2 segundos
```

#### Diagrama Temporal

```
Tiempo →  0s    1s    2s    3s    4s    5s    6s
Perfil (2s):   [██]✅                              
Categorías(3s):[████]✅                            
Productos (5s):[████████]✅                        
                                                   
Si Productos tardara 7s:                           
Productos (5s):[████████████]⏱️ TIMEOUT           
Pero Perfil y Categorías ya completaron ✅         
```

**Clave**: Una petición con timeout NO afecta a las demás.

---

### 2. Cancelación de Tareas en Grupo

#### Problema que Resuelve

En algunos escenarios, **no tiene s**`coordinador_async.py`** (530+ líneas) petición crítica falla. Ejemplos:
- Si `obtener_perfil()` falla con **401 (No Autorizado)**, las demás peticiones fallarán también
- Esperar a que fallen una por una es **desperdicio de recursos**
- Cancelar inmediatamente es más eficiente

#### Solución: `cancel_remaining(tareas)`

```python
def cancel_remaining(tareas: Set[asyncio.Task]) -> int:
    """
    Cancela todas las tareas pendientes del conjunto.
    
    Returns:
        int: Número de tareas canceladas
    """
    canceladas = 0
    for tarea in tareas:
        if not tarea.done():
            tarea.cancel()
            canceladas += 1
    return canceladas
```

#### Función de Alto Nivel: `cargar_dashboard_con_cancelacion()`

Esta función implementa la lógica de cancelación condicional:

```python
async def cargar_dashboard_con_cancelacion() -> dict:
    """
    Si obtener_perfil falla con 401 (no autorizado), 
    cancela las demás peticiones.
    """
    # Crear tareas con timeouts específicos
    tarea_productos = asyncio.create_task(listar_productos(session, timeout=5.0))
    tarea_categorias = asyncio.create_task(obtener_categorias(session, timeout=3.0))
    tarea_perfil = asyncio.create_task(obtener_perfil(session, timeout=2.0))
    
    # Esperar resultados conforme llegan
    while pendientes:
        done, pendientes = await asyncio.wait(pendientes, return_when=asyncio.FIRST_COMPLETED)
        
        for tarea in done:
            try:
                resultado = await tarea
                datos[nombre] = resultado
            
            except NoAutorizado:
                # 🚫 Error 401: Cancelar todas las tareas pendientes
                if pendientes:
                    cancel_remaining(pendientes)
                    break
```

#### Diagrama Temporal

```
Tiempo →       0s    1s    2s    3s    4s    5s
Productos:     [████████████████~~~~~]❌ CANCELADA
Categorías:    [████████~~~~~]❌ CANCELADA        
Perfil:        [██]🚫 401 → DISPARA CANCELACIÓN  
               ↑                                  
               └─ Sin autenticación, cancelar todo

Leyenda:
  ████  = Ejecución activa
  🚫    = Error 401 detectado
  ~~~~~  = Cancelación en progreso
  ❌    = Cancelada por error de autenticación
```

**Clave**: Cancelar rápidamente cuando no tiene sentido continuar.

---

### 3. Carga con Prioridad (asyncio.wait)

#### Problema que Resuelve

En ACT3 AI, `cargar_dashboard()` usaba `asyncio.gather()`:
- **Espera a que TODAS las tareas terminen**
- El usuario debe esperar a la **petición más lenta**
- Aunque productos esté listo en 1s, no se muestra hasta que notificaciones (4s) termine

#### Solución: `cargar_con_prioridad()`

Usa `asyncio.wait(return_when=FIRST_COMPLETED)` para:
1. Lanzar 4 peticiones simultáneas
2. **Procesar resultados conforme llegan** (no esperar a todas)
3. Mostrar **dashboard parcial** cuando llegan las peticiones **CRÍTICAS**
4. Procesar peticiones **SECUNDARIAS** cuando lleguen

```python
async def cargar_con_prioridad() -> dict:
    """
    ESTRATEGIA:
    - CRÍTICAS: productos, perfil (sin esto no hay dashboard)
    - SECUNDARIAS: categorías, notificaciones (mejoran UX pero no son esenciales)
    """
    # Crear tareas con timeouts específicos
    tarea_productos = asyncio.create_task(listar_productos(session, timeout=5.0))
    tarea_categorias = asyncio.create_task(obtener_categorias(session, timeout=3.0))
    tarea_perfil = asyncio.create_task(obtener_perfil(session, timeout=2.0))
    tarea_notificaciones = asyncio.create_task(obtener_notificaciones(session, timeout=4.0))
    
    tareas_criticas = {tarea_productos, tarea_perfil}
    
    while pendientes:
        # Esperar a que al menos una tarea termine
        done, pendientes = await asyncio.wait(pendientes, return_when=asyncio.FIRST_COMPLETED)
        
        for tarea in done:
            resultado = await tarea
            datos[nombre] = resultado
            
            # ¿Ya podemos mostrar dashboard parcial?
            if criticas_completadas == tareas_criticas:
                tiempo_dashboard_parcial = time.time() - inicio
                # 🎉 ¡MOSTRAR DASHBOARD PARCIAL AL USUARIO!
```

#### Diagrama Temporal

```
Tiempo →       0s    1s    2s    3s    4s    5s
Perfil (C):    [██]✅                              
Productos (C): [████]✅                            
               ↑                                   
               └─ 🎉 DASHBOARD PARCIAL LISTO      
                  (usuario ve productos y perfil) 
                                                   
Categorías:    [██████]✅                          
               ↑                                   
               └─ Categorías aparecen después     
                                                   
Notificaciones:[████████]✅                        
               ↑                                   
               └─ Notificaciones aparecen al final

Leyenda:
  (C)   = Petición CRÍTICA
  ████  = Ejecución activa
  ✅    = Completada
  🎉    = Dashboard parcial listo para mostrar
```

#### Comparación: gather() vs wait()

| Aspecto | `asyncio.gather()` | `asyncio.wait(FIRST_COMPLETED)` |
|---------|-------------------|----------------------------------|
| **Filosofía** | Espera a TODAS | Procesa conforme llegan |
| **Orden resultado** | Orden de lanzamiento | Orden de llegada |
| **Dashboard parcial** | ❌ No posible | ✅ Posible |
| **UX percibida** | Usuario espera a la más lenta | Usuario ve resultados incrementales |
| **Tiempo hasta 1er resultado** | ~4-5s (la más lenta) | ~1-2s (la más rápida) |
| **Uso ideal** | Necesitas todos los resultados juntos | Puedes mostrar resultados parciales |

**Ejemplo concreto**:

```python
# gather(): Usuario espera 4s para ver CUALQUIER cosa
productos, categorias, perfil, notificaciones = await asyncio.gather(
    listar_productos(session),      # tarda 2s
    obtener_categorias(session),    # tarda 3s
    obtener_perfil(session),        # tarda 1s
    obtener_notificaciones(session) # tarda 4s  ← TODO espera a esto
)
# ⏱️ Usuario ve el dashboard completo después de 4s

# wait(): Usuario ve dashboard parcial en 2s
resultado = await cargar_con_prioridad()
# ⏱️ Dashboard parcial (productos + perfil) en 2s
# ⏱️ Dashboard completo en 4s
# 📈 Ganancia percibida: 2s más rápido
```

---

## 🧪 Tests

### Ejecutar Tests

```bash
# Ir al directorio
cd "c:\Users\Petucho\Documents\Cosas de la escuela\SEMESTRE VI\FEND101\Semana III\ACT4 AI"

# Test 1: Timeout individual
python test_timeout_individual.py

# Test 2: Cancelación en grupo
python test_cancelacion_grupo.py

# Test 3: Carga con prioridad
python test_carga_prioridad.py
```

### Qué Demuestra Cada Test

#### `test_timeout_individual.py`

- ✅ TEST 1: Timeout individual básico
  - 3 peticiones con diferentes timeouts
  - La que excede timeout falla, las demás continúan
  
- ✅ TEST 2: Timeouts configurables por función
  - Productos: 5s, Categorías: 3s, Perfil: 2s
  - Cada función respeta su timeout específico
  
- ✅ TEST 3: Diagrama temporal visual
  - Muestra visualmente qué pasa cuando una petición tiene timeout

#### `test_cancelacion_grupo.py`

- ✅ TEST 1: Cancelación básica con `cancel_remaining()`
  - Lanzar 3 tareas, cancelar después de 1s
  - Verificar que se cancelan correctamente
  
- ✅ TEST 2: Cancelación en cascada por error 401
  - Perfil falla con 401
  - Las demás peticiones se cancelan automáticamente
  
- ✅ TEST 3: Diagrama temporal de cancelación
- ✅ TEST 4: Prueba real con el cliente

#### `test_carga_prioridad.py`

- ✅ TEST 1: Procesamiento incremental
  - 4 peticiones que tardan 1s, 2s, 3s, 4s
  - Mostrar orden de llegada
  
- ✅ TEST 2: Dashboard parcial con peticiones críticas
  - Mostrar dashboard cuando llegan las críticas
  - Procesar secundarias después
  
- ✅ TEST 3: Diagrama temporal de carga con prioridad
- ✅ TEST 4: Prueba real con el cliente
- ✅ TEST 5: Comparación gather() vs wait()

---

## 📊 Casos de Uso

### Caso 1: E-commerce con Dashboard

**Escenario**: Dashboard de tienda online

**Peticiones**:
- Productos destacados (crítica, tarda 2s)
- Perfil del usuario (crítica, tarda 1s)
- Categorías (secundaria, tarda 3s)
- Ofertas del día (secundaria, tarda 4s)

**Solución**: `cargar_con_prioridad()`
- Dashboard parcial en 2s (productos + perfil)
- Dashboard completo en 4s
- **Ganancia**: Usuario ve contenido 2s antes

### Caso 2: SaaS con Autenticación

**Escenario**: Panel de control de aplicación SaaS

**Peticiones**:
- Verificar token (crítica, tarda 0.5s)
- Cargar datos del usuario (crítica, tarda 1s)
- Cargar estadísticas (secundaria, tarda 3s)

**Problema**: Si token es inválido (401), las demás peticiones fallarán

**Solución**: `cargar_dashboard_con_cancelacion()`
- Si token falla, cancelar inmediatamente
- Redirigir a login sin esperar a que las demás fallen

### Caso 3: API con Rate Limiting

**Escenario**: API externa con límites de tasa

**Peticiones**:
- Endpoint A (límite: 5s)
- Endpoint B (límite: 3s)
- Endpoint C (límite: 10s)

**Solución**: Timeouts individuales
- Cada endpoint tiene su timeout basado en su límite de tasa
- Si uno excede, los demás continúan normalmente

---

## 🔧 Mejores Prácticas

### 1. Configurar Timeouts

```python
# ❌ MAL: Timeout global para todo
GLOBAL_TIMEOUT = 10  # ¿Qué pasa si perfil tarda 0.5s y productos 8s?

# ✅ BIEN: Timeout específico por función
TIMEOUTS = {
    "productos": 5.0,       # Petición lenta, necesita más tiempo
    "categorias": 3.0,      # Petición media
    "perfil": 2.0,          # Petición rápida, timeout corto
    "notificaciones": 4.0   # Petición secundaria
}
```

### 2. Definir Peticiones Críticas

```python
# ✅ BIEN: Definir claramente qué es crítico
CRITICAS = {"productos", "perfil"}        # Sin esto no hay dashboard
SECUNDARIAS = {"categorias", "notificaciones"}  # Mejoran UX pero no son esenciales
```

### 3. Manejar Cancelación

```python
# ✅ BIEN: Logs claros para debugging
try:
    resultado = await tarea
except asyncio.CancelledError:
    logger.info(f"Tarea '{nombre}' fue cancelada (esperado si hubo error 401)")
    raise
except NoAutorizado:
    logger.warning(f"Error 401 en '{nombre}', cancelando tareas pendientes")
    cancel_remaining(pendientes)
```

---

## 📚 Conceptos Técnicos

### asyncio.wait_for()

Espera a que una corutina termine o exceda un timeout:

```python
try:
    resultado = await asyncio.wait_for(coroutine, timeout=5.0)
except asyncio.TimeoutError:
    print("Tardó más de 5 segundos")
```

### asyncio.wait()

Espera a que tareas terminen según una estrategia:

```python
done, pending = await asyncio.wait(
    tareas,
    return_when=asyncio.FIRST_COMPLETED  # O ALL_COMPLETED, FIRST_EXCEPTION
)
```

| Estrategia | Significado |
|------------|-------------|
| `FIRST_COMPLETED` | Retorna cuando al menos una tarea termine |
| `ALL_COMPLETED` | Retorna cuando todas las tareas terminen (por defecto) |
| `FIRST_EXCEPTION` | Retorna cuando una tarea lance una excepción |

### Task.cancel()

Solicita cancelación de una tarea:

```python
tarea = asyncio.create_task(operacion_lenta())
await asyncio.sleep(1.0)
tarea.cancel()  # Solicitar cancelación

try:
    await tarea
except asyncio.CancelledError:
    print("Tarea cancelada")
```

---

## 🔗 Relación con ACT3 AI

| Característica | ACT3 AI | ACT4 AI |
|----------------|---------|---------|
| Timeout | Global (10s para todo) | Individual (configurable por función) |
| Cancelación | No soportada | ✅ Granular con `cancel_remaining()` |
| Procesamiento | `gather()` espera a todas | `wait()` procesa conforme llegan |
| Dashboard | Completo o nada | ✅ Parcial cuando llegan críticas |
| UX percibida | Espera a la más lenta | ✅ Incremental, ve resultados antes |

**ACT4 AI es una evolución** de ACT3 AI que agrega control granular de flujo asíncrono.

---

## 🛠️ Requisitos

- Python 3.7+
- `aiohttp`

```bash
pip install aiohttp
```

---

## 👨‍💻 Autor

Creado como parte de FEND101 - Semana III - ACT4 AI

**Tema**: Control de Flujo Asíncrono Avanzado  
**Enfoque**: Timeout, Cancelación y Priorización
