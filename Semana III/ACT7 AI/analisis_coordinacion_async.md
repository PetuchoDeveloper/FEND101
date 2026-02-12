# Análisis de Estrategias de Coordinación de Tareas Asíncronas
## EcoMarket Dashboard Loading - Trade-offs Comparison

---

## 📊 Tabla Comparativa de Estrategias

| Estrategia | Latencia Percibida | Robustez | Complejidad | Mantenibilidad | Puntuación Total |
|------------|-------------------|----------|-------------|----------------|------------------|
| **1. asyncio.gather()** | ⭐⭐ (2/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐⭐ (5/5) | **15/20** |
| **2. asyncio.wait(FIRST_COMPLETED)** | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐ (3/5) | ⭐⭐ (2/5) | ⭐⭐ (2/5) | **12/20** |
| **3. asyncio.as_completed()** | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐ (4/5) | **16/20** |
| **4. asyncio.wait(FIRST_EXCEPTION)** | ⭐⭐ (2/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐⭐ (4/5) | **15/20** |

---

## 🔍 Análisis Detallado por Estrategia

### 1️⃣ **asyncio.gather() - Esperar a que TODAS terminen**

#### ¿Cuándo se muestra el primer dato al usuario?
- **Nunca hasta que todas completen**
- Si productos=200ms, categorías=100ms, perfil=500ms, notificaciones=TIMEOUT(10s)
- **Usuario espera 10 segundos** para ver cualquier dato

#### ¿Qué pasa cuando 1 de 4 peticiones falla?
- Por defecto, lanza excepción y cancela el resto
- Con `return_exceptions=True`, retorna la excepción pero espera a todas

#### ¿Qué pasa cuando 1 de 4 peticiones es muy lenta (10s)?
- **Toda la carga espera 10 segundos**
- Experiencia de usuario bloqueada

#### Código extra comparado con secuencial
- **Mínimo**: solo cambiar a `await asyncio.gather()`
- Complejidad: ⭐⭐⭐⭐⭐ (5/5)

#### Facilidad para agregar 5ta petición
- **Muy fácil**: solo agregar a la lista de corutinas
- Mantenibilidad: ⭐⭐⭐⭐⭐ (5/5)

---

### 2️⃣ **asyncio.wait(return_when=FIRST_COMPLETED) - Procesar conforme llegan**

#### ¿Cuándo se muestra el primer dato al usuario?
- **100ms** (categorías llega primero)
- Actualización progresiva del dashboard

#### ¿Qué pasa cuando 1 de 4 peticiones falla?
- Las demás continúan ejecutándose
- Necesitas manejar excepciones individualmente con `.exception()`

#### ¿Qué pasa cuando 1 de 4 peticiones es muy lenta (10s)?
- **No afecta las demás**
- Dashboard muestra 3/4 datos rápidamente

#### Código extra comparado con secuencial
- **Complejo**: bucle while, manejo de pending/done sets
- Complejidad: ⭐⭐ (2/5)

#### Facilidad para agregar 5ta petición
- **Moderado**: agregar a pending set inicial
- Mantenibilidad: ⭐⭐ (2/5) - lógica de loop puede volverse compleja

---

### 3️⃣ **asyncio.as_completed() - Iterar por orden de completación**

#### ¿Cuándo se muestra el primer dato al usuario?
- **100ms** (categorías llega primero)
- Actualización progresiva y natural

#### ¿Qué pasa cuando 1 de 4 peticiones falla?
- El bucle continúa con las demás
- Puedes envolver cada await en try/except

#### ¿Qué pasa cuando 1 de 4 peticiones es muy lenta (10s)?
- **No afecta las demás**
- Dashboard muestra 3/4 datos inmediatamente

#### Código extra comparado con secuencial
- **Moderado**: bucle for async, try/except por iteración
- Complejidad: ⭐⭐⭐ (3/5)

#### Facilidad para agregar 5ta petición
- **Fácil**: agregar a la lista de corutinas
- Mantenibilidad: ⭐⭐⭐⭐ (4/5)

---

### 4️⃣ **asyncio.wait(return_when=FIRST_EXCEPTION) - Abortar ante primer error**

#### ¿Cuándo se muestra el primer dato al usuario?
- **Nunca si hay error temprano**
- Si todo sale bien, espera a que todas terminen (igual que gather)

#### ¿Qué pasa cuando 1 de 4 peticiones falla?
- **Retorna inmediatamente** tras detectar la excepción
- Cancela automáticamente las tareas pendientes

#### ¿Qué pasa cuando 1 de 4 peticiones es muy lenta (10s)?
- Si no hay errores, espera las 10 segundos
- Si hay error antes, termina rápidamente

#### Código extra comparado con secuencial
- **Moderado**: manejo de done/pending, verificación de excepciones
- Complejidad: ⭐⭐⭐⭐ (4/5)

#### Facilidad para agregar 5ta petición
- **Fácil**: agregar a la lista de tareas
- Mantenibilidad: ⭐⭐⭐⭐ (4/5)

---

## 💻 Código Python - Las 4 Estrategias

### Escenario de Prueba
```python
# Simulación de 4 endpoints del dashboard EcoMarket
async def obtener_productos():
    await asyncio.sleep(0.2)  # 200ms
    return {"productos": ["Producto A", "Producto B"]}

async def obtener_categorias():
    await asyncio.sleep(0.1)  # 100ms
    return {"categorias": ["Electrónica", "Hogar"]}

async def obtener_perfil():
    await asyncio.sleep(0.5)  # 500ms
    return {"perfil": {"nombre": "Usuario", "email": "user@eco.com"}}

async def obtener_notificaciones():
    await asyncio.sleep(10)  # TIMEOUT - 10s
    raise asyncio.TimeoutError("Notificaciones no disponibles")
```

### Estrategia 1: asyncio.gather()
```python
async def cargar_dashboard_gather():
    """Espera a que TODAS las peticiones completen."""
    print("🔵 GATHER: Iniciando carga...")
    inicio = time.time()
    
    try:
        # Sin return_exceptions - falla ante primer error
        resultados = await asyncio.gather(
            obtener_productos(),
            obtener_categorias(),
            obtener_perfil(),
            obtener_notificaciones()
        )
        print(f"✅ GATHER: Todas completadas en {time.time() - inicio:.2f}s")
        return resultados
    except Exception as e:
        print(f"❌ GATHER: Falló en {time.time() - inicio:.2f}s - {e}")
        raise

async def cargar_dashboard_gather_tolerante():
    """Espera a TODAS pero tolera errores."""
    print("🔵 GATHER (tolerante): Iniciando carga...")
    inicio = time.time()
    
    resultados = await asyncio.gather(
        obtener_productos(),
        obtener_categorias(),
        obtener_perfil(),
        obtener_notificaciones(),
        return_exceptions=True  # No detiene ante errores
    )
    
    duracion = time.time() - inicio
    print(f"⏱️  GATHER: Completado en {duracion:.2f}s")
    
    # Procesar resultados y errores
    for i, resultado in enumerate(resultados):
        if isinstance(resultado, Exception):
            print(f"  ❌ Petición {i+1} falló: {resultado}")
        else:
            print(f"  ✅ Petición {i+1} exitosa")
    
    return resultados
```

### Estrategia 2: asyncio.wait(FIRST_COMPLETED)
```python
async def cargar_dashboard_first_completed():
    """Procesa resultados conforme van llegando."""
    print("🟢 FIRST_COMPLETED: Iniciando carga...")
    inicio = time.time()
    
    tareas = {
        asyncio.create_task(obtener_productos(), name="productos"),
        asyncio.create_task(obtener_categorias(), name="categorias"),
        asyncio.create_task(obtener_perfil(), name="perfil"),
        asyncio.create_task(obtener_notificaciones(), name="notificaciones"),
    }
    
    resultados = {}
    pending = tareas
    
    while pending:
        # Espera a que al menos 1 tarea complete
        done, pending = await asyncio.wait(
            pending, 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for tarea in done:
            try:
                resultado = tarea.result()
                nombre = tarea.get_name()
                resultados[nombre] = resultado
                
                tiempo_transcurrido = time.time() - inicio
                print(f"  ✅ {nombre} completado en {tiempo_transcurrido:.2f}s")
                print(f"     → UI actualizada con {nombre}")
                
            except Exception as e:
                nombre = tarea.get_name()
                print(f"  ❌ {nombre} falló: {e}")
                resultados[nombre] = None
    
    print(f"🏁 FIRST_COMPLETED: Todo procesado en {time.time() - inicio:.2f}s")
    return resultados
```

### Estrategia 3: asyncio.as_completed()
```python
async def cargar_dashboard_as_completed():
    """Itera por orden de completación."""
    print("🟡 AS_COMPLETED: Iniciando carga...")
    inicio = time.time()
    
    tareas = {
        "productos": obtener_productos(),
        "categorias": obtener_categorias(),
        "perfil": obtener_perfil(),
        "notificaciones": obtener_notificaciones(),
    }
    
    resultados = {}
    
    # Crear lista de corutinas con nombre
    corutinas = [
        (nombre, corutina) 
        for nombre, corutina in tareas.items()
    ]
    
    # as_completed requiere tareas, no corutinas directamente
    tareas_lista = [
        asyncio.create_task(coro, name=nombre)
        for nombre, coro in corutinas
    ]
    
    for tarea_completada in asyncio.as_completed(tareas_lista):
        try:
            resultado = await tarea_completada
            # Recuperar nombre desde la tarea
            nombre = tarea_completada.get_name() if hasattr(tarea_completada, 'get_name') else "unknown"
            
            tiempo_transcurrido = time.time() - inicio
            print(f"  ✅ {nombre} completado en {tiempo_transcurrido:.2f}s")
            print(f"     → UI actualizada progresivamente")
            
            resultados[nombre] = resultado
            
        except Exception as e:
            tiempo_transcurrido = time.time() - inicio
            print(f"  ❌ Petición falló en {tiempo_transcurrido:.2f}s: {e}")
            # Continúa con las demás tareas
    
    print(f"🏁 AS_COMPLETED: Todo procesado en {time.time() - inicio:.2f}s")
    return resultados
```

### Estrategia 4: asyncio.wait(FIRST_EXCEPTION)
```python
async def cargar_dashboard_first_exception():
    """Aborta inmediatamente ante el primer error."""
    print("🔴 FIRST_EXCEPTION: Iniciando carga...")
    inicio = time.time()
    
    tareas = {
        asyncio.create_task(obtener_productos(), name="productos"),
        asyncio.create_task(obtener_categorias(), name="categorias"),
        asyncio.create_task(obtener_perfil(), name="perfil"),
        asyncio.create_task(obtener_notificaciones(), name="notificaciones"),
    }
    
    try:
        done, pending = await asyncio.wait(
            tareas,
            return_when=asyncio.FIRST_EXCEPTION
        )
        
        # Verificar si hay excepciones
        excepciones = []
        resultados = {}
        
        for tarea in done:
            try:
                resultado = tarea.result()
                resultados[tarea.get_name()] = resultado
            except Exception as e:
                excepciones.append((tarea.get_name(), e))
        
        if excepciones:
            # Cancelar tareas pendientes
            for tarea in pending:
                tarea.cancel()
                print(f"  🚫 Cancelando {tarea.get_name()}")
            
            # Esperar a que se cancelen
            await asyncio.gather(*pending, return_exceptions=True)
            
            duracion = time.time() - inicio
            print(f"❌ FIRST_EXCEPTION: Abortado en {duracion:.2f}s")
            print(f"   Error: {excepciones[0][1]}")
            raise excepciones[0][1]
        
        else:
            # No hubo excepciones, esperar el resto
            if pending:
                más_resultados = await asyncio.gather(*pending, return_exceptions=True)
                # Procesar...
            
            print(f"✅ FIRST_EXCEPTION: Completado sin errores en {time.time() - inicio:.2f}s")
            return resultados
            
    except asyncio.CancelledError:
        print("⚠️ FIRST_EXCEPTION: Operación cancelada")
        raise
```

---

## 📈 Diagrama Temporal Comparativo

### Escenario: productos=200ms, categorías=100ms, perfil=500ms, notificaciones=TIMEOUT(10s)

```mermaid
gantt
    title Comparación de Estrategias de Coordinación Async
    dateFormat X
    axisFormat %Ls

    section GATHER (sin tolerancia)
    Productos      :p1, 0, 200
    Categorías     :c1, 0, 100
    Perfil         :pf1, 0, 500
    Notificaciones :n1, 0, 10000
    ❌ Error detectado :milestone, e1, 10000
    🖥️ UI actualiza :crit, milestone, ui1, 10000

    section GATHER (tolerante)
    Productos      :p2, 0, 200
    Categorías     :c2, 0, 100
    Perfil         :pf2, 0, 500
    Notificaciones :n2, 0, 10000
    🖥️ UI actualiza :crit, milestone, ui2, 10000

    section FIRST_COMPLETED
    Productos      :p3, 0, 200
    Categorías     :c3, 0, 100
    Perfil         :pf3, 0, 500
    Notificaciones :n3, 0, 10000
    🖥️ UI #1 (100ms) :crit, milestone, ui3a, 100
    🖥️ UI #2 (200ms) :crit, milestone, ui3b, 200
    🖥️ UI #3 (500ms) :crit, milestone, ui3c, 500
    🖥️ UI #4 (10s) :crit, milestone, ui3d, 10000

    section AS_COMPLETED
    Productos      :p4, 0, 200
    Categorías     :c4, 0, 100
    Perfil         :pf4, 0, 500
    Notificaciones :n4, 0, 10000
    🖥️ UI #1 (100ms) :crit, milestone, ui4a, 100
    🖥️ UI #2 (200ms) :crit, milestone, ui4b, 200
    🖥️ UI #3 (500ms) :crit, milestone, ui4c, 500
    ❌ Error manejado :milestone, ui4d, 10000

    section FIRST_EXCEPTION
    Productos      :p5, 0, 200
    Categorías     :c5, 0, 100
    Perfil         :pf5, 0, 500
    Notificaciones :n5, 0, 10000
    ❌ Error → Abort :crit, milestone, e5, 10000
    🚫 Cancelación :cancel5, 10000, 10100
```

### Interpretación del Diagrama

| Estrategia | Primer Dato Visible | Datos Completos | Comportamiento ante Error |
|------------|---------------------|-----------------|---------------------------|
| **GATHER (sin tolerancia)** | 10s | 10s | ❌ Lanza excepción, no retorna nada |
| **GATHER (tolerante)** | 10s | 10s | ⚠️ Retorna todo (incluyendo excepciones) |
| **FIRST_COMPLETED** | **100ms** ✅ | 10s | ✅ Continúa con las demás |
| **AS_COMPLETED** | **100ms** ✅ | 10s | ✅ Maneja error en el bucle |
| **FIRST_EXCEPTION** | N/A | 10s | ❌ Aborta y cancela pendientes |

---

## 🎯 Recomendación para EcoMarket

### ✅ Estrategia Recomendada: **asyncio.as_completed()**

#### Justificación

1. **Mejor Latencia Percibida** (⭐⭐⭐⭐⭐)
   - Usuario ve el primer dato en **100ms** (categorías)
   - Dashboard se puebla progresivamente
   - Sensación de rapidez y respuesta inmediata

2. **Robustez Adecuada** (⭐⭐⭐⭐)
   - Un endpoint lento/fallido no bloquea los demás
   - Manejo granular de errores por endpoint
   - Degradación elegante del servicio

3. **Complejidad Manejable** (⭐⭐⭐)
   - Código ligeramente más complejo que `gather()`
   - Pero mucho más simple que `wait(FIRST_COMPLETED)`
   - Patrón fácil de entender: "procesar conforme lleguen"

4. **Alta Mantenibilidad** (⭐⭐⭐⭐)
   - Agregar 5ta petición es trivial
   - Código autodocumentado por el flujo de iteración
   - Fácil debuggear orden de llegada

#### Implementación Recomendada para EcoMarket

```python
async def cargar_dashboard_ecomarket():
    """
    Carga progresiva del dashboard con manejo robusto de errores.
    """
    endpoints = {
        "productos": obtener_productos(),
        "categorias": obtener_categorias(),
        "perfil": obtener_perfil(),
        "notificaciones": obtener_notificaciones(),
    }
    
    dashboard_data = {
        "productos": None,
        "categorias": None,
        "perfil": None,
        "notificaciones": None,
        "errores": []
    }
    
    tareas = [
        asyncio.create_task(coro, name=nombre)
        for nombre, coro in endpoints.items()
    ]
    
    for tarea in asyncio.as_completed(tareas):
        try:
            resultado = await tarea
            nombre = tarea.get_name()
            dashboard_data[nombre] = resultado
            
            # 🔥 ACTUALIZACIÓN PROGRESIVA DE UI
            print(f"📊 Dashboard: {nombre} cargado → actualizar UI")
            # En producción: emit_event(f"{nombre}_loaded", resultado)
            
        except asyncio.TimeoutError as e:
            nombre = tarea.get_name()
            dashboard_data["errores"].append({
                "endpoint": nombre,
                "tipo": "timeout",
                "mensaje": str(e)
            })
            print(f"⏱️ Dashboard: {nombre} timeout → usar placeholder")
            
        except Exception as e:
            nombre = tarea.get_name()
            dashboard_data["errores"].append({
                "endpoint": nombre,
                "tipo": type(e).__name__,
                "mensaje": str(e)
            })
            print(f"❌ Dashboard: {nombre} falló → mostrar mensaje de error")
    
    return dashboard_data
```

#### Cuándo NO usar as_completed()

- **Todos los datos son críticos**: Si necesitas los 4 endpoints para mostrar algo, usa `gather(return_exceptions=True)`
- **Necesitas abortar ante primer error**: Si un fallo invalida todo el dashboard, usa `wait(FIRST_EXCEPTION)`

#### Alternativa Secundaria

Si la latencia no es crítica pero quieres código más simple:

```python
# Opción más simple si latencia de 10s es aceptable
resultados = await asyncio.gather(
    obtener_productos(),
    obtener_categorias(),
    obtener_perfil(),
    obtener_notificaciones(),
    return_exceptions=True  # Tolerar errores
)
```

**Trade-off**: Código 50% más simple, pero usuario espera 10x más tiempo.

---

## 📋 Resumen de Trade-offs

| Métrica | Mejor Opción | Peor Opción |
|---------|--------------|-------------|
| **Latencia Percibida** | as_completed() / FIRST_COMPLETED | gather() |
| **Simplicidad de Código** | gather() | FIRST_COMPLETED |
| **Robustez ante Errores** | FIRST_EXCEPTION | gather() (sin return_exceptions) |
| **Experiencia de Usuario** | as_completed() | gather() |
| **Mantenibilidad** | gather() / as_completed() | FIRST_COMPLETED |

---

## 🔬 Próximos Pasos

Ejecutar `comparacion_coordinacion.py` para:
1. Benchmarking real con métricas de tiempo
2. Simulación con diferentes latencias y tasas de error
3. Medición de throughput y uso de recursos
4. Visualización de resultados

---

**Fecha de análisis**: 12 de febrero de 2026  
**Analista**: Antigravity AI  
**Proyecto**: EcoMarket Dashboard Optimization  
**Versión**: 1.0
