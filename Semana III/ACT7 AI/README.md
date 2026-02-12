# ACT7 AI - Análisis de Estrategias de Coordinación Asíncrona

## 📖 Descripción del Proyecto

Este proyecto analiza y compara **4 estrategias diferentes de coordinación de tareas asíncronas** para el caso de uso del dashboard de EcoMarket, que necesita cargar datos desde 4 endpoints independientes.

## 📁 Estructura del Proyecto

```
ACT7 AI/
├── README.md                           # Este archivo
├── analisis_coordinacion_async.md     # Análisis completo con tablas y diagramas
├── RECOMENDACION_ECOMARKET.md          # Recomendación detallada con scoring
├── comparacion_coordinacion.py         # Script de benchmarking
├── throttle.py                         # Cliente HTTP con throttling (de ACT5)
├── mock_server.py                      # Servidor mock (de ACT5)
├── validadores.py                      # Validadores (de ACT5)
└── benchmark_*.json                    # Resultados de benchmarking
```

## 🎯 Estrategias Analizadas

### 1. `asyncio.gather()`
**Concepto**: Esperar a que TODAS las peticiones completen antes de retornar resultados.

**Pros**:
- ✅ Código más simple (5/5 complejidad)
- ✅ Fácil mantenibilidad (5/5)

**Contras**:
- ❌ Usuario espera al endpoint más lento (latencia percibida: 2/5)
- ❌ Todo o nada (robustez: 3/5)

**Puntuación total**: 15/20

---

### 2. `asyncio.wait(return_when=FIRST_COMPLETED)`
**Concepto**: Procesar resultados conforme van llegando usando bucle `while` y sets.

**Pros**:
- ✅ Actualización progresiva de UI (latencia percibida: 5/5)
- ✅ Tolerante a fallos (robustez: 3/5)

**Contras**:
- ❌ Código complejo con manejo manual de sets (complejidad: 2/5)
- ❌ Difícil de mantener (mantenibilidad: 2/5)

**Puntuación total**: 12/20

---

### 3. `asyncio.as_completed()` ⭐ **RECOMENDADO**
**Concepto**: Iterar sobre tareas en orden de completación con bucle `async for`.

**Pros**:
- ✅ Actualización progresiva de UI (latencia percibida: 5/5)
- ✅ Robusto con manejo granular de errores (robustez: 4/5)
- ✅ Código idiomático en Python (complejidad: 3/5)
- ✅ Fácil de extender (mantenibilidad: 4/5)

**Contras**:
- ⚠️ Levemente más complejo que `gather()`

**Puntuación total**: **16/20**

---

### 4. `asyncio.wait(return_when=FIRST_EXCEPTION)`
**Concepto**: Abortar inmediatamente ante el primer error detectado.

**Pros**:
- ✅ Cancela rápido ante errores críticos (robustez: 5/5)
- ✅ Control fino de excepciones (complejidad: 4/5)

**Contras**:
- ❌ Comportamiento "todo o nada" demasiado estricto
- ❌ Puede desperdiciar trabajo ya iniciado

**Puntuación total**: 15/20

---

## 🏆 Recomendación Final

### **Usar `asyncio.as_completed()` para EcoMarket Dashboard**

**Razones**:

1. **Mejor Experiencia de Usuario** (⭐⭐⭐⭐⭐)
   - Usuario ve el primer dato en **100ms** (categorías)
   - Dashboard se actualiza progresivamente, no bloqueado
   
2. **Robustez Adecuada** (⭐⭐⭐⭐)
   - Un endpoint lento/fallido no bloquea los demás
   - Degradación graceful del servicio
   
3. **Código Mantenible** (⭐⭐⭐⭐)
   - Agregar 5to endpoint = 1 línea de código
   - Patrón idiomático en Python
   - Fácil de debuggear

### Ejemplo de Implementación

```python
async def cargar_dashboard_ecomarket():
    endpoints = {
        "productos": obtener_productos(),
        "categorias": obtener_categorias(),
        "perfil": obtener_perfil(),
        "notificaciones": obtener_notificaciones(),
    }
    
    dashboard_data = {endpoint: None for endpoint in endpoints}
    dashboard_data["errores"] = []
    
    tareas = [
        asyncio.create_task(coro, name=nombre)
        for nombre, coro in endpoints.items()
    ]
    
    for tarea in asyncio.as_completed(tareas):
        try:
            resultado = await tarea
            nombre = tarea.get_name()
            dashboard_data[nombre] = resultado
            
            # 🔥 Actualizar UI progresivamente
            print(f"✅ {nombre} cargado → actualizar UI")
            
        except Exception as e:
            nombre = tarea.get_name()
            dashboard_data["errores"].append({
                "endpoint": nombre,
                "error": str(e)
            })
            print(f"❌ {nombre} falló → mostrar placeholder")
    
    return dashboard_data
```

---

## 🔬 Ejecutar Benchmarking

### Prerequisitos

- Python 3.7+
- `asyncio` (incluido en stdlib)

### Ejecutar

```bash
cd "Semana III/ACT7 AI"
python comparacion_coordinacion.py
```

### Escenarios de Prueba

El benchmark ejecuta 4 escenarios:

1. **normal**: Todos los endpoints responden exitosamente
   - productos: 200ms
   - categorias: 100ms
   - perfil: 500ms
   - notificaciones: 300ms

2. **timeout**: Un endpoint tiene timeout de 10s
   - productos: 200ms
   - categorias: 100ms
   - perfil: 500ms
   - notificaciones: **10,000ms** ⏱️

3. **error_rapido**: Error inmediato en un endpoint
   - productos: 200ms
   - categorias: **ERROR 500** ❌
   - perfil: 500ms
   - notificaciones: 300ms

4. **mixto**: Múltiples endpoints con errores variables
   - productos: 150ms (20% error de conexión)
   - categorias: 80ms (10% timeout)
   - perfil: 400ms
   - notificaciones: 250ms (30% error de servidor)

### Resultados Esperados

El benchmark genera:

1. **Salida en consola** con:
   - Tiempo total promedio ± desviación estándar
   - Tiempo hasta primer dato ± desviación estándar
   - Tasa de éxito (%)
   - Orden de completación de cada endpoint

2. **Archivos JSON** con datos detallados:
   - `benchmark_normal_<timestamp>.json`
   - `benchmark_timeout_<timestamp>.json`
   - `benchmark_error_rapido_<timestamp>.json`
   - `benchmark_mixto_<timestamp>.json`

---

## 📊 Comparación Visual

### Escenario Timeout (productos=200ms, categorías=100ms, perfil=500ms, notificaciones=10s)

| Estrategia | Tiempo Total | Primer Dato | Datos OK | UX |
|------------|--------------|-------------|----------|-----|
| **gather (tolerante)** | 10,000ms | 10,000ms | 3/4 | 😴 |
| **gather (estricto)** | 10,000ms | ❌ ERROR | 0/4 | 😡 |
| **first_completed** | 10,000ms | **100ms** ✅ | 3/4 | 😊 |
| **as_completed** | 10,000ms | **100ms** ✅ | 3/4 | 😊 |
| **first_exception** | 10,000ms | ❌ ERROR | 0/4 | 😡 |

**Ganador**: `as_completed()` por simplicidad de código vs `first_completed()`

---

## 📚 Documentos Adicionales

### 1. [`analisis_coordinacion_async.md`](./analisis_coordinacion_async.md)
Contiene:
- Tabla comparativa completa con puntuaciones
- Análisis detallado de cada estrategia
- Código Python completo para las 4 estrategias
- Diagramas temporales con Mermaid
- Interpretación de resultados

### 2. [`RECOMENDACION_ECOMARKET.md`](./RECOMENDACION_ECOMARKET.md)
Contiene:
- Justificación detallada de la recomendación
- Scoring con pesos (Latencia 35%, Robustez 25%, etc.)
- Código de producción listo para usar
- Plan de migración paso a paso
- Recomendaciones adicionales (cacheo, retry, priorización)

### 3. [`comparacion_coordinacion.py`](./comparacion_coordinacion.py)
Script ejecutable que:
- Simula 4 endpoints con latencias configurables
- Implementa las 4 estrategias de coordinación
- Ejecuta benchmarks con 4 escenarios
- Genera estadísticas (promedio, desviación estándar)
- Exporta resultados a JSON

---

## 💡 Conclusiones Clave

1. **Para dashboards interactivos**: Usar `as_completed()` para actualización progresiva

2. **Para datos críticos (todos importantes)**: Usar `gather(return_exceptions=True)`

3. **Para transacciones**: Usar `wait(FIRST_EXCEPTION)` para abortar ante fallos

4. **Evitar**: `wait(FIRST_COMPLETED)` a menos que necesites lógica muy avanzada

---

## 🚀 Impacto Esperado en EcoMarket

Al migrar de secuencial a `as_completed()`:

- 📈 **Latencia percibida**: -90% (de 1,100ms a 100ms para primer dato)
- 😊 **Satisfacción de usuario**: Significativamente mejorada
- 🛡️ **Resiliencia**: Dashboard funcional incluso con endpoints caídos
- 🔧 **Mantenibilidad**: Fácil agregar nuevos endpoints

---

**Autor**: Antigravity AI  
**Fecha**: 12 de febrero de 2026  
**Proyecto**: EcoMarket - Semana III/ACT7 AI  
**Versión**: 1.0
