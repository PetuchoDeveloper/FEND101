# Diagramas Temporales - Control de Flujo Asíncrono

Este documento contiene diagramas temporales detallados para visualizar el funcionamiento de las tres características principales de ACT4 AI.

---

## 📊 Diagrama 1: Timeout Individual por Petición

### Escenario: Timeouts Independientes

**Configuración**:
- Petición A: tarda 1s, timeout 3s
- Petición B: tarda 5s, timeout 2s  
- Petición C: tarda 3s, timeout 4s

### Diagrama Temporal

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Petición A       [████]✅                                                            
(timeout 3s)      ↑                                                                  
                  1s - Completa exitosamente                                         
                                                                                      
Petición B       [████████]⏱️                                                       
(timeout 2s)                ↑                                                        
                            2s - TIMEOUT! Excede su límite de 2s                     
                            Pero A y C continúan normalmente                         
                                                                                      
Petición C       [████████████]✅                                                    
(timeout 4s)                      ↑                                                  
                                  3s - Completa exitosamente                         
                                                                                      
Resultado:                                                                            
  A: ✅ ÉXITO    (completó en 1s < timeout 3s)                                       
  B: ⏱️ TIMEOUT (tardó 5s > timeout 2s)                                             
  C: ✅ ÉXITO    (completó en 3s < timeout 4s)                                       
```

### Leyenda

- `████` = Ejecución activa (petición en progreso)
- `✅` = Completada exitosamente
- `⏱️` = Timeout (excedió su límite individual)
- `↑` = Evento importante

### Conclusión

**Cada petición tiene su propio timeout independiente**. Si una petición excede su timeout, las demás continúan normalmente. Esto es diferente a un timeout global que cancelaría todo.

---

## 📊 Diagrama 2: Cancelación de Tareas por Error 401

### Escenario: Autenticación Fallida

**Configuración**:
- Productos: tarda 5s (timeout 5s)
- Categorías: tarda 3s (timeout 3s)
- Perfil: tarda 2s pero falla con 401 en 1s

### Diagrama Temporal

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Productos        [████████████████~~~~~]❌                                           
                                  ↑     ↑                                            
                                  |     Cancelada en 1s                              
                                  Iba bien hasta aquí                                
                                                                                      
Categorías       [████████~~~~~]❌                                                   
                          ↑     ↑                                                    
                          |     Cancelada en 1s                                      
                          Iba bien hasta aquí                                        
                                                                                      
Perfil           [██]🚫                                                              
                    ↑                                                                 
                    1s - Error 401: No Autorizado                                    
                    DISPARA cancelación de las demás                                 
                                                                                      
Resultado:                                                                            
  Productos:  ❌ CANCELADA (no tiene sentido continuar sin auth)                     
  Categorías: ❌ CANCELADA (no tiene sentido continuar sin auth)                     
  Perfil:     🚫 ERROR 401 (trigger de cancelación)                                  
```

### Leyenda

- `████` = Ejecución activa
- `~~~~~` = Cancelación en progreso
- `🚫` = Error crítico detectado (401 No Autorizado)
- `❌` = Cancelada por error de autenticación

### Secuencia de Eventos

1. **t=0s**: Las 3 peticiones se lanzan en paralelo
2. **t=1s**: Perfil falla con error 401
3. **t=1s**: Se detecta el error 401 → disparador de cancelación
4. **t=1s**: `cancel_remaining()` cancela Productos y Categorías
5. **t=1s+**: Las tareas canceladas reciben `CancelledError` y terminan
6. **Total**: ~1s en lugar de ~5s si esperáramos a que todas fallaran

### Justificación

**¿Por qué cancelar?**

Sin autenticación válida:
- Productos fallaría con 401 también (tardando 5s en fallar)
- Categorías fallaría con 401 también (tardando 3s en fallar)
- **Total desperdiciado**: 5s esperando fallos inevitables

Con cancelación:
- Detectamos el problema en 1s
- Cancelamos inmediatamente
- **Ganancia**: 4s ahorrados + mejor UX

---

## 📊 Diagrama 3: Carga con Prioridad (asyncio.wait)

### Escenario: Dashboard con Peticiones Críticas y Secundarias

**Configuración**:
- **CRÍTICAS** (necesarias para dashboard parcial):
  - Productos: tarda 2s
  - Perfil: tarda 1s
  
- **SECUNDARIAS** (mejoran UX pero no son esenciales):
  - Categorías: tarda 3s
  - Notificaciones: tarda 4s

### Diagrama Temporal

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Perfil (C)       [██]✅                                                              
                    ↑                                                                 
                    1s - Llega primera                                               
                                                                                      
Productos (C)    [████]✅                                                            
                        ↑                                                             
                        2s - Llega segunda                                           
                        🎉 DASHBOARD PARCIAL LISTO                                   
                        Usuario ya puede ver:                                        
                          - Lista de productos                                       
                          - Nombre y datos del perfil                                
                                                                                      
Categorías       [██████]✅                                                          
                              ↑                                                       
                              3s - Llega tercera                                     
                              Se agrega al dashboard sin recargar                    
                                                                                      
Notificaciones   [████████]✅                                                        
                                      ↑                                               
                                      4s - Llega última                               
                                      Dashboard ahora está completo                   
```

### Leyenda

- `(C)` = Petición CRÍTICA (necesaria para dashboard parcial)
- `████` = Ejecución activa
- `✅` = Completada y procesada
- `🎉` = Dashboard parcial listo para mostrar al usuario

### Comparación: gather() vs wait()

#### Con `asyncio.gather()` (ACT3 AI)

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Todas las        [████████████████████████████████]                                  
peticiones                                        ↑                                   
                                                  4s - TODO llega junto              
                                                  Usuario espera a la más lenta      
                                                                                      
⏱️ Usuario ve el dashboard después de 4s (tiempo de notificaciones)                 
```

#### Con `asyncio.wait(FIRST_COMPLETED)` (ACT4 AI)

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Procesamiento    [1]              [2]             [3]              [4]               
incremental       ↓                ↓               ↓                ↓                 
                Perfil         Productos      Categorías      Notificaciones         
                llega          llega          llega           llega                  
                             🎉 PARCIAL                                               
                                                                                      
⏱️ Usuario ve dashboard parcial después de 2s (tiempo de productos)                 
📈 Ganancia percibida: 2 segundos más rápido                                          
```

### Orden de Llegada y Procesamiento

| Tiempo | Evento | Acción |
|--------|--------|--------|
| 1s | Perfil ✅ | Procesado. Falta Productos para dashboard parcial |
| 2s | Productos ✅ | Procesado. **🎉 Dashboard parcial listo** |
| 3s | Categorías ✅ | Procesada. Se agrega al dashboard |
| 4s | Notificaciones ✅ | Procesada. Dashboard completo |

### Métricas de UX

```
                                        gather()    wait()    Mejora
─────────────────────────────────────────────────────────────────────
Tiempo hasta 1er dato visible          4s          1s        ⬇ 75%
Tiempo hasta dashboard parcial         4s          2s        ⬇ 50%
Tiempo hasta dashboard completo        4s          4s        ═ 0%
─────────────────────────────────────────────────────────────────────
```

**Conclusión**: El usuario ve contenido útil **2 segundos antes** con `wait()`.

---

## 📊 Diagrama 4: Combinación de Características

### Escenario Realista: E-commerce bajo Carga

**Configuración**:
- Productos: timeout 5s, tarda 2s
- Perfil: timeout 2s, tarda 1s, **puede fallar con 401**
- Categorías: timeout 3s, tarda 3s
- Ofertas: timeout 4s, tarda 4s

### Caso A: Todo Funciona Correctamente

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Perfil (C)       [██]✅                                                              
Productos (C)    [████]✅                                                            
                        ↑                                                             
                        🎉 Dashboard parcial @ 2s                                    
Categorías       [██████]✅                                                          
Ofertas          [████████]✅                                                        
                                      ↑                                               
                                      Dashboard completo @ 4s                        
```

**Resultado**: Dashboard parcial en 2s, completo en 4s

### Caso B: Perfil Falla con 401

```
Tiempo (segundos) →
0                1                2                3                4                5
|----------------|----------------|----------------|----------------|----------------|
                                                                                      
Perfil           [██]🚫                                                              
                    ↑                                                                 
                    Error 401 @ 1s → Cancelar todo                                   
                                                                                      
Productos        [████~~~~~]❌                                                       
Categorías       [████~~~~~]❌                                                       
Ofertas          [████~~~~~]❌                                                       
                    ↑                                                                 
                    Canceladas @ 1s                                                   
```

**Resultado**: Error detectado en 1s, todo cancelado, redirigir a login

### Caso C: Productos Tiene Timeout

```
Tiempo (segundos) →
0                1                2                3                4                5        6
|----------------|----------------|----------------|----------------|----------------|--------|
                                                                                              
Perfil (C)       [██]✅                                                                      
Productos (C)    [██████████]⏱️                                                              
                                ↑                                                             
                                Timeout @ 5s (tardó más de lo esperado)                      
                                ⚠️ Dashboard parcial NO disponible                           
Categorías       [██████]✅                                                                  
Ofertas          [████████]✅                                                                
```

**Resultado**: Dashboard parcial NO disponible (falta productos), mostrar error

---

## 🎯 Casos de Uso y Decisiones

### ¿Cuándo Usar Timeout Individual?

```python
# ✅ USAR cuando:
# - Diferentes endpoints tienen diferentes SLAs
# - Algunos endpoints son naturalmente más lentos
# - Quieres fallar rápido en endpoints críticos

# Ejemplo:
listar_productos(session, timeout=5.0)   # API lenta, necesita tiempo
obtener_perfil(session, timeout=1.0)     # Debe ser rápido o fallar
```

### ¿Cuándo Usar Cancelación de Grupo?

```python
# ✅ USAR cuando:
# - Un fallo implica que las demás peticiones también fallarán
# - No tiene sentido continuar sin datos críticos
# - Quieres ahorrar recursos del servidor

# Ejemplo:
if error_401_en_perfil:
    cancel_remaining(pendientes)  # Sin auth, nada funcionará
    redirect_to_login()
```

### ¿Cuándo Usar Carga con Prioridad?

```python
# ✅ USAR cuando:
# - Puedes mostrar UI parcial útil
# - Algunos datos son más importantes que otros
# - Quieres mejorar la UX percibida

# Ejemplo:
resultado = await cargar_con_prioridad()
if resultado["criticas_completas"]:
    mostrar_dashboard_parcial()  # Usuario ve algo ANTES
    # Secundarias se irán agregando conforme lleguen
```

---

## 📈 Métricas de Rendimiento

### Comparación de Estrategias

```
Escenario: 4 peticiones (1s, 2s, 3s, 4s)
2 críticas (1s, 2s), 2 secundarias (3s, 4s)

┌─────────────────────────┬──────────┬─────────┬──────────┐
│ Estrategia              │ 1er dato │ Parcial │ Completo │
├─────────────────────────┼──────────┼─────────┼──────────┤
│ gather()                │   4s     │   N/A   │    4s    │
│ wait(ALL_COMPLETED)     │   4s     │   N/A   │    4s    │
│ wait(FIRST_COMPLETED)   │   1s     │   2s    │    4s    │
│ + timeout individual    │   1s     │   2s    │    4s    │
│ + cancelación (si 401)  │   1s     │  -1s-   │   -1s-   │
└─────────────────────────┴──────────┴─────────┴──────────┘

Nota: Con cancelación por 401, todo termina en ~1s
```

---

## 🔍 Debugging Visual

### Cómo Leer los Diagramas

```
Tiempo → 0s    1s    2s    3s
Tarea A  [████]✅              ← Completa en 1s
Tarea B  [████████]⏱️          ← Timeout en 2s
Tarea C  [██]🚫                ← Error en 1s, dispara cancelación
Tarea D  [████~~~~~]❌         ← Cancelada externamente
         ↑    ↑    ↑
         |    |    └─ Eventos importantes
         |    └────── Estados finales
         └─────────── Progreso de ejecución
```

### Estados Posibles

- `████` = Ejecución activa
- `~~~~~` = Cancelación en progreso
- `✅` = Completada exitosamente
- `⏱️` = Timeout (excedió su límite)
- `🚫` = Error crítico (401, 500, etc.)
- `❌` = Cancelada externamente
- `⚠️` = Advertencia o problema no crítico
- `🎉` = Evento positivo (dashboard parcial listo)

---

## 📚 Referencias

- [asyncio — Asynchronous I/O](https://docs.python.org/3/library/asyncio.html)
- [asyncio.wait()](https://docs.python.org/3/library/asyncio-task.html#asyncio.wait)
- [asyncio.wait_for()](https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for)
- [Task Cancellation](https://docs.python.org/3/library/asyncio-task.html#task-cancellation)
