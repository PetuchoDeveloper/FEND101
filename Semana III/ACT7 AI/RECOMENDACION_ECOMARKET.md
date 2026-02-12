# Recomendación de Estrategia de Coordinación Asíncrona para EcoMarket

## 🎯 Resumen Ejecutivo

**Estrategia Recomendada**: `asyncio.as_completed()`

**Puntuación General**: ⭐⭐⭐⭐ (16/20)

**Justificación en una línea**: Ofrece el mejor balance entre experiencia de usuario (latencia percibida baja), robustez ante fallos, y mantenibilidad del código.

---

## 📋 Contexto del Problema

### Requisitos del Dashboard EcoMarket

El dashboard de EcoMarket necesita cargar datos desde **4 endpoints independientes**:

1. **Productos** (~200ms)
2. **Categorías** (~100ms)
3. **Perfil de usuario** (~500ms)
4. **Notificaciones** (variable, puede llegar a timeout)

### Criterios de Evaluación

| Criterio | Peso | Descripción |
|----------|------|-------------|
| **Latencia Percibida** | 35% | ¿Cuánto espera el usuario para ver el primer dato? |
| **Robustez** | 25% | ¿Cómo maneja fallos en endpoints individuales? |
| **Complejidad** | 20% | ¿Qué tan difícil es escribir y debuggear el código? |
| **Mantenibilidad** | 20% | ¿Qué tan fácil es agregar/modificar endpoints? |

---

## ✅ Estrategia Recomendada: `asyncio.as_completed()`

### Puntuación Detallada

- **Latencia Percibida**: ⭐⭐⭐⭐⭐ (5/5)
  - Usuario ve el primer dato en **100ms** (categorías)
  - Dashboard se actualiza progresivamente, no en bloque
  
- **Robustez**: ⭐⭐⭐⭐ (4/5)
  - Un endpoint lento/fallido no bloquea los demás
  - Manejo individual de errores con try/except
  - Degradación graceful del servicio

- **Complejidad**: ⭐⭐⭐ (3/5)
  - Bucle `async for` es idiomático en Python
  - Ligeramente más code que `gather()` pero mucho más simple que `wait()`
  - Patrón fácil de entender: "procesar conforme lleguen"

- **Mantenibilidad**: ⭐⭐⭐⭐ (4/5)
  - Agregar un 5to endpoint: añadir 1 línea de código
  - Código autodocumentado
  - Fácil de debuggear (logs muestran orden real de llegada)

**Total**: 16/20 (80%)

---

## 💻 Implementación Recomendada

### Código de Producción para EcoMarket

```python
import asyncio
from typing import Dict, Any, Optional


async def cargar_dashboard_ecomarket() -> Dict[str, Any]:
    """
    Carga progresiva del dashboard EcoMarket con manejo robusto de errores.
    
    Returns:
        Dict con datos del dashboard y lista de errores (si los hubo)
    """
    # Definir endpoints a cargar
    endpoints = {
        "productos": obtener_productos(),
        "categorias": obtener_categorias(),
        "perfil": obtener_perfil(),
        "notificaciones": obtener_notificaciones(),
    }
    
    # Inicializar estructura de respuesta
    dashboard_data = {
        "productos": None,
        "categorias": None,
        "perfil": None,
        "notificaciones": None,
        "errores": [],
        "timestamp_carga": None
    }
    
    # Crear tareas con nombres identificables
    tareas = [
        asyncio.create_task(coro, name=nombre)
        for nombre, coro in endpoints.items()
    ]
    
    # Procesar conforme van completando
    for tarea in asyncio.as_completed(tareas):
        try:
            resultado = await tarea
            nombre = tarea.get_name()
            dashboard_data[nombre] = resultado
            
            # 🔥 PUNTO DE INTEGRACIÓN: Actualizar UI progresivamente
            print(f"✅ Dashboard: {nombre} cargado → actualizar UI")
            # En producción:
            # await websocket.send_json({"tipo": "update", "seccion": nombre, "datos": resultado})
            # O: event_bus.emit(f"{nombre}_loaded", resultado)
            
        except asyncio.TimeoutError as e:
            nombre = tarea.get_name()
            dashboard_data["errores"].append({
                "endpoint": nombre,
                "tipo": "timeout",
                "mensaje": f"Timeout en {nombre}"
            })
            print(f"⏱️ Dashboard: {nombre} timeout → mostrar placeholder")
            
        except ConnectionError as e:
            nombre = tarea.get_name()
            dashboard_data["errores"].append({
                "endpoint": nombre,
                "tipo": "connection",
                "mensaje": str(e)
            })
            print(f"🔌 Dashboard: {nombre} sin conexión → mostrar mensaje offline")
            
        except Exception as e:
            nombre = tarea.get_name()
            dashboard_data["errores"].append({
                "endpoint": nombre,
                "tipo": type(e).__name__,
                "mensaje": str(e)
            })
            print(f"❌ Dashboard: {nombre} error → mostrar mensaje de error")
    
    dashboard_data["timestamp_carga"] = asyncio.get_event_loop().time()
    return dashboard_data


# Funciones auxiliares (simulación)
async def obtener_productos():
    await asyncio.sleep(0.2)
    return {"productos": [...]}

async def obtener_categorias():
    await asyncio.sleep(0.1)
    return {"categorias": [...]}

async def obtener_perfil():
    await asyncio.sleep(0.5)
    return {"perfil": {...}}

async def obtener_notificaciones():
    await asyncio.sleep(0.3)
    return {"notificaciones": [...]}
```

### Ventajas en Producción

1. **UX Superior**: Dashboard "cobra vida" progresivamente
2. **Tolerancia a Fallos**: Un servicio caído no afecta a los demás
3. **Debugging Fácil**: Logs muestran el orden real de eventos
4. **Extensible**: Agregar un endpoint = 1 línea de código

---

## ⚖️ Comparación con Alternativas

### ❌ ¿Por qué NO `asyncio.gather()`?

```python
# Código más simple...
resultados = await asyncio.gather(
    obtener_productos(),
    obtener_categorias(),
    obtener_perfil(),
    obtener_notificaciones(),
    return_exceptions=True
)
```

**Problema**: Usuario espera **10 segundos** (el endpoint más lento) para ver **cualquier** dato.

- ⏱️ Latencia percibida: **10,000ms**
- 😴 UX: Usuario piensa que la app está congelada
- 📊 Puntuación: 15/20

**Cuándo usarlo**: Si TODOS los datos son igualmente críticos y no puedes mostrar nada hasta tenerlos todos.

---

### ❌ ¿Por qué NO `asyncio.wait(FIRST_COMPLETED)`?

```python
# Código más complejo...
pending = {asyncio.create_task(...) for ...}
while pending:
    done, pending = await asyncio.wait(pending, return_when=FIRST_COMPLETED)
    for tarea in done:
        # Procesar...
```

**Problema**: Código verbose y propenso a errores (manejo manual de sets).

- 🧩 Complejidad: ⭐⭐ (2/5)
- 🔧 Mantenibilidad: ⭐⭐ (2/5)
- 📊 Puntuación: 12/20

**Cuándo usarlo**: Cuando necesitas lógica avanzada como timeouts dinámicos o cancelación condicional.

---

### ⚠️ ¿Por qué NO `asyncio.wait(FIRST_EXCEPTION)`?

```python
done, pending = await asyncio.wait(tareas, return_when=FIRST_EXCEPTION)
# Si hay error, cancelar todo...
```

**Problema**: Comportamiento "todo o nada" es demasiado estricto para un dashboard.

- ❌ Si notificaciones fallan (no crítico), cancela carga de productos (crítico)
- 📊 Puntuación: 15/20

**Cuándo usarlo**: Cuando un fallo en cualquier endpoint invalida toda la operación (ej: transacción bancaria).

---

## 🔬 Resultados del Benchmark

### Escenario: productos=200ms, categorías=100ms, perfil=500ms, notificaciones=TIMEOUT(10s)

| Estrategia | Tiempo Total | Primer Dato | Datos Exitosos | Tasa Éxito |
|------------|--------------|-------------|----------------|------------|
| **gather (tolerante)** | 10,000ms | 10,000ms | 3/4 | 75% |
| **gather (estricto)** | 10,000ms | ❌ ERROR | 0/4 | 0% |
| **first_completed** | 10,000ms | **100ms** ✅ | 3/4 | 75% |
| **as_completed** | 10,000ms | **100ms** ✅ | 3/4 | 75% |
| **first_exception** | 10,000ms | ❌ ERROR | 0/4 | 0% |

### Interpretación

- `as_completed()` y `first_completed()` empatan en rendimiento
- `as_completed()` gana por **simplicidad del código** (3/5 vs 2/5)

---

## 📦 Plan de Migración

### Paso 1: Refactorizar Código Actual (Día 1)

```python
# ANTES (secuencial - 1,100ms total)
productos = await obtener_productos()      # 200ms
categorias = await obtener_categorias()    # 100ms
perfil = await obtener_perfil()            # 500ms
notificaciones = await obtener_notificaciones()  # 300ms

# DESPUÉS (paralelo con as_completed - primer dato en 100ms)
async for resultado in cargar_dashboard_ecomarket():
    actualizar_ui(resultado)
```

### Paso 2: Agregar Timeouts (Día 2)

```python
async def obtener_notificaciones_con_timeout():
    try:
        return await asyncio.wait_for(
            obtener_notificaciones(),
            timeout=2.0  # 2 segundos máximo
        )
    except asyncio.TimeoutError:
        return {"notificaciones": [], "timeout": True}
```

### Paso 3: Monitorear Métricas (Día 3-7)

- **Métrica clave**: Percentil 95 de "tiempo hasta primer dato"
- **Meta**: < 500ms
- **Tools**: Logging de `orden_completacion` del benchmark

---

## 🚀 Recomendaciones Adicionales

### 1. Cacheo Inteligente

```python
# Cachear categorías (cambian rara vez)
@cache(ttl=3600)  # 1 hora
async def obtener_categorias():
    ...
```

### 2. Priorización de Endpoints

```python
# Cargar productos ANTES que notificaciones
endpoints_criticos = ["productos", "categorias"]
endpoints_opcionales = ["perfil", "notificaciones"]
```

### 3. Retry con Backoff Exponencial

```python
@retry(max_attempts=3, backoff_factor=2)
async def obtener_productos():
    ...
```

---

## 🎓 Conclusión

Para el dashboard de EcoMarket:

✅ **USAR**: `asyncio.as_completed()`  
❌ **EVITAR**: `asyncio.gather()` sin timeouts  
⚠️ **CONSIDERAR**: `gather()` solo si todos los datos son igualmente críticos

**Impacto esperado**:
- 🚀 Latencia percibida reducida en **90%** (10s → 100ms para primer dato)
- 😊 Satisfacción de usuario: **significativamente mejorada**
- 🛡️ Resiliencia: Dashboard funcional incluso con endpoints caídos

---

**Autor**: Antigravity AI  
**Fecha**: 12 de febrero de 2026  
**Versión**: 1.0  
**Próxima revisión**: Después de ejecutar benchmark en producción
