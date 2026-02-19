# Benchmark: Sync vs Async HTTP Clients - ACT9 AI

Este directorio contiene un benchmark riguroso para comparar el rendimiento de clientes HTTP síncronos y asíncronos para la API de EcoMarket.

## Archivos

- **`benchmark_sync_vs_async.py`**: Script principal del benchmark
- **`benchmark_mock_server.py`**: Servidor mock con latencia configurable
- **`requirements.txt`**: Dependencias de Python
- **`benchmark_results.png`**: Gráficos comparativos (generado automáticamente)
- **`recomendaciones.md`**: Análisis y recomendaciones (generado automáticamente)

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### 1. Iniciar el servidor mock (terminal 1)

```bash
python benchmark_mock_server.py
```

Deberías ver:
```
✅ Benchmark Mock Server corriendo en http://127.0.0.1:8888
```

### 2. Ejecutar el benchmark (terminal 2)

**Modo completo** (10 iteraciones, 3 latencias, ~10-15 min):
```bash
python benchmark_sync_vs_async.py
```

**Modo rápido** (2 iteraciones, 2 latencias, ~2 min):
```bash
python benchmark_sync_vs_async.py --quick-mode
```

## Escenarios de Prueba

1. **Dashboard**: 4 peticiones GET simultáneas (simula cargar un dashboard)
2. **Creación Masiva**: 20 productos POST (simula importación masiva)
3. **Operaciones Mixtas**: 10 GET + 5 POST + 3 PATCH (simula carga real)

Cada escenario se ejecuta con 3 niveles de latencia:
- **0ms**: Sin latencia (red local rápida)
- **100ms**: Latencia media (API externa)
- **500ms**: Alta latencia (servidor lento o red degradada)

## Métricas Recolectadas

- ⏱️ **Tiempo total de ejecución**
- 📈 **Throughput** (requests por segundo)
- 🧠 **Memoria pico** (MB via tracemalloc)
- 📊 **Estadísticas**: media, mediana, desviación estándar

## Resultados

El benchmark genera automáticamente:

1. **Tabla comparativa en consola**:
   - Speedup por escenario
   - Comparación de throughput
   - Overhead de memoria

2. **Gráfico PNG** (`benchmark_results.png`):
   - Panel 1: Tiempo total por escenario
   - Panel 2: Speedup vs número de requests
   - Panel 3: Throughput comparativo
   - Panel 4: Uso de memoria

3. **Documento de recomendaciones** (`recomendaciones.md`):
   - Análisis ejecutivo
   - Punto de cruce (cuándo migrar a async)
   - Justificación basada en datos

## Ejemplo de Salida

```
┌─────────────────────────────────────────────────────────────────┐
│ Escenario 1: Dashboard (4 GET requests)                         │
├─────────────┬──────────┬──────────┬───────────┬─────────────────┤
│ Latency     │ Client   │ Time (s) │ RPS       │ Memory (MB)     │
├─────────────┼──────────┼──────────┼───────────┼─────────────────┤
│ 0ms         │ Sync     │ 0.45     │ 8.9       │ 12.3            │
│             │ Async    │ 0.12     │ 33.3      │ 14.1            │
│             │ Speedup  │ 3.75x    │ 3.75x     │ -14.6%          │
└─────────────┴──────────┴──────────┴───────────┴─────────────────┘
```

## Troubleshooting

**Error: "Servidor mock no detectado"**
- Asegúrate de ejecutar `python benchmark_mock_server.py` en otra terminal primero

**Error: ModuleNotFoundError**
- Instala las dependencias: `pip install -r requirements.txt`

**Error: "No module named 'cliente_ecomarket'"**
- El script busca automáticamente los clientes en `Semana II/ACT7 AI` y `Semana III/ACT8 AI`
- Verifica que esos directorios existan con los archivos correctos

## Configuración del Servidor Mock

Puedes cambiar la latencia dinámicamente:

```bash
curl -X POST http://127.0.0.1:8888/config -d '{"latency_ms": 200}'
```

Ver configuración actual:
```bash
curl http://127.0.0.1:8888/config
```

## Notas Técnicas

- El benchmark usa `tracemalloc` para medir memoria exacta de Python
- Cada escenario se ejecuta 10 veces para obtener estadísticas confiables
- El servidor mock simula delays realistas sin variabilidad de red externa
- Los clientes se importan directamente (no se copian) para probar las implementaciones reales
