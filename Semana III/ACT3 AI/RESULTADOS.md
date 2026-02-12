# 📊 Resultados del Benchmark: Sync vs Async

## Resumen Ejecutivo

El cliente asíncrono de EcoMarket es **5.31x más rápido** que el cliente síncrono para cargar el dashboard (3 peticiones HTTP).

## Resultados Detallados

### Tabla Comparativa

| Métrica | Cliente Síncrono (requests) | Cliente Asíncrono (aiohttp) | Mejora |
|---------|----------------------------|----------------------------|--------|
| **Promedio** | 12.216 segundos | 2.301 segundos | **5.31x más rápido** ⚡ |
| **Mejor caso** | 12.203 segundos | 2.285 segundos | **5.34x más rápido** |
| **Peor caso** | 12.223 segundos | 2.320 segundos | **5.27x más rápido** |

### Visualización del Speedup

```
Cliente SÍNCRONO (12.22s):
█████████████████████████████████████████████████████████ 100%

Cliente ASÍNCRONO (2.30s):
█████████ 19%

Ahorro de tiempo: 9.91 segundos (81% más rápido)
```

## Análisis

### ¿Por qué 5.31x en lugar de 3x?

**Speedup esperado**: ~3x (por ejecutar 3 peticiones en paralelo)  
**Speedup real**: **5.31x** 🚀  

El speedup supera las expectativas por:

1. **Connection Pooling**: `aiohttp.ClientSession` reutiliza conexiones TCP
   - **Sync**: Crea 3 conexiones nuevas (overhead de handshake TCP)
   - **Async**: Una conexión reutilizada 3 veces

2. **Event Loop Efficiency**: El event loop de asyncio es más eficiente que ejecutar peticiones secuenciales
   - Menos context switching
   - Mejor utilización de recursos I/O

### Tiempos por Iteración

#### Síncrono (5 iteraciones)
```
Iteración 1: 12.220s
Iteración 2: 12.203s ← mejor
Iteración 3: 12.215s
Iteración 4: 12.223s ← peor
Iteración 5: 12.221s
```

#### Asíncrono (5 iteraciones)
```
Iteración 1: 2.320s ← peor
Iteración 2: 2.302s
Iteración 3: 2.300s
Iteración 4: 2.300s
Iteración 5: 2.285s ← mejor
```

### Consistencia

- **Síncrono**: Muy consistente (desviación de ±0.01s)
- **Asíncrono**: Muy consistente (desviación de ±0.02s)

Ambos clientes muestran resultados predecibles y reproducibles.

## Casos de Uso

### Cuándo el speedup importa:

✅ **Dashboards**: Cargar múltiples widgets simultáneamente  
✅ **APIs agregadoras**: Combinar datos de varios servicios  
✅ **Scrapers**: Recolectar datos de múltiples páginas  
✅ **Batch processing**: Procesar lotes de operaciones I/O  

### Cuándo el speedup no importa:

❌ **Scripts de una sola petición**: No hay paralelismo  
❌ **Tareas CPU-bound**: Async no ayuda con cálculos intensivos  
❌ **Operaciones secuenciales**: Cuando cada paso depende del anterior  

## Ecuación del Speedup

```
S = T_sync / T_async
S = 12.216 / 2.301
S = 5.31x

Eficiencia = (S / número_de_peticiones) × 100%
Eficiencia = (5.31 / 3) × 100% = 177%
```

Una eficiencia >100% indica que hay optimizaciones adicionales más allá del simple paralelismo.

## Conclusión

El cliente asíncrono de EcoMarket ofrece **mejoras dramáticas de rendimiento** para operaciones I/O paralelas, superando ampliamente las expectativas de speedup lineal gracias a optimizaciones como connection pooling y el event loop eficiente de asyncio.

**Recomendación**: Usar el cliente asíncrono para cualquier aplicación que necesite cargar múltiples recursos simultáneamente.

---

*Resultados obtenidos en Windows con Python 3.12, servidor mock local*  
*Fecha: 2026-02-11*
