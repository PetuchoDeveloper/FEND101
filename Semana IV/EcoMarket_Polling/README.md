# Semana 4: Monitor de Inventario EcoMarket

**Entregable:** Sistema de Polling Adaptativo con Patrón Observer

---

## Reto 1: Traza del Ciclo de Polling con ETag

### Descripción del Escenario

EcoMarket necesita detectar cambios en el inventario sin bombardear al servidor. Usamos **ETag** para identificar versiones de los datos.

### Flujo de 4 Consultas con ETag

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CICLO DE POLLING CON ETag                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CONSULTA #1 (Inicial)                                                      │
│  ┌──────────────┐                    ┌──────────────┐                       │
│  │   CLIENTE    │ ── GET /api/productos ──▶ │   SERVIDOR   │                       │
│  │              │                    │              │                       │
│  │              │ ◀─ 200 OK + datos ──── │              │                       │
│  │              │     ETag: "abc123"   │              │                       │
│  └──────────────┘                    └──────────────┘                       │
│                                                                             │
│  Headers enviados:    (ninguno especial)                                    │
│  Status recibido:     200 OK                                                │
│  Datos transferidos:  ~2KB (lista completa de productos)                    │
│  Acción del cliente:  Guardar ETag="abc123", notificar observadores         │
│  Intervalo:           Reset a 5s (hay actividad)                            │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  CONSULTA #2 (Sin cambios)                                                  │
│  ┌──────────────┐                    ┌──────────────┐                       │
│  │   CLIENTE    │ ── GET /api/productos ──▶ │   SERVIDOR   │                       │
│  │   If-None-   │     If-None-Match: "abc123"              │                       │
│  │   Match:     │                    │  (datos sin cambio)│                       │
│  │  "abc123"    │ ◀─ 304 Not Modified ──── │              │                       │
│  │              │     (sin body)       │              │                       │
│  └──────────────┘                    └──────────────┘                       │
│                                                                             │
│  Headers enviados:    If-None-Match: "abc123"                               │
│  Status recibido:     304 Not Modified                                      │
│  Datos transferidos:  ~0 bytes (solo headers)                               │
│  Acción del cliente:  No notificar (sin cambios)                            │
│  Intervalo:           Crece a 7.5s (backoff ×1.5)                           │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  CONSULTA #3 (Sin cambios - de nuevo)                                       │
│  ┌──────────────┐                    ┌──────────────┐                       │
│  │   CLIENTE    │ ── GET /api/productos ──▶ │   SERVIDOR   │                       │
│  │   If-None-   │     If-None-Match: "abc123"              │                       │
│  │   Match:     │                    │  (datos sin cambio)│                       │
│  │  "abc123"    │ ◀─ 304 Not Modified ──── │              │                       │
│  └──────────────┘                    └──────────────┘                       │
│                                                                             │
│  Headers enviados:    If-None-Match: "abc123"                               │
│  Status recibido:     304 Not Modified                                      │
│  Datos transferidos:  ~0 bytes                                              │
│  Acción del cliente:  No notificar                                          │
│  Intervalo:           Crece a 11.25s (backoff ×1.5)                         │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  CONSULTA #4 (¡Hay cambios!)                                                │
│  ┌──────────────┐                    ┌──────────────┐                       │
│  │   CLIENTE    │ ── GET /api/productos ──▶ │   SERVIDOR   │                       │
│  │   If-None-   │     If-None-Match: "abc123"              │                       │
│  │   Match:     │                    │ (alguien actualizó)│                       │
│  │  "abc123"    │ ◀─ 200 OK + datos ──── │  un precio!      │                       │
│  │              │     ETag: "def456"   │              │                       │
│  └──────────────┘                    └──────────────┘                       │
│                                                                             │
│  Headers enviados:    If-None-Match: "abc123"                               │
│  Status recibido:     200 OK                                                │
│  Datos transferidos:  ~2KB (lista actualizada)                              │
│  Acción del cliente:  Guardar ETag="def456", notificar observadores         │
│  Intervalo:           Reset a 5s (hay actividad)                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ¿Por qué ETag es más eficiente?

| Método | Sin cambios | Con cambios | Ancho de banda |
|--------|-------------|-------------|----------------|
| **Comparar datos completos** | Descargar JSON + comparar | Descargar JSON + comparar | Alto |
| **ETag (304)** | Solo headers (~200 bytes) | JSON completo | Bajo |

**Ventaja:** Cuando no hay cambios (el caso común), solo se transfieren headers HTTP, no el cuerpo completo. Con 500 clientes haciendo polling, esto representa un ahorro enorme.

---

## Estructura del Proyecto

```
ACT4_EcoMarket_Polling/
├── monitor.py          # Código principal (Observable + ServicioPolling)
├── validacion.log      # Salida de pruebas (Reto 4)
└── README.md          # Este archivo
```

---

## Cómo Ejecutar

### Requisitos

```bash
pip install aiohttp
```

### Iniciar el servidor mock (desde Semana IV)

```bash
python servidor_mock.py
```

### Ejecutar el monitor

```bash
python monitor.py
```

El monitor correrá por 30 segundos o hasta que presiones Ctrl+C.

---

## Componentes del Sistema

### Observable (Patrón Observer)

La clase `Observable` implementa el patrón Observer que desacopla:
- **Productores de eventos**: El polling detecta cambios
- **Consumidores de eventos**: La UI, alertas, logs

Métodos principales:
- `suscribir(evento, callback)`: Agregar observador
- `desuscribir(evento, callback)`: Remover observador
- `notificar(evento, datos)`: Notificar a todos los observadores

### ServicioPolling

Extiende `Observable` e implementa:
- Polling adaptativo con ETag
- Backoff progresivo (304 y errores)
- Detención limpia
- Manejo de timeouts

### Observadores

1. **observador_ui**: Actualiza la interfaz de usuario
2. **observador_alertas**: Detecta productos agotados (stock=0)
3. **observador_logs**: Registra eventos
4. **observador_errores**: Maneja errores del servidor

---

## Decisiones de Diseño (Reto 3)

### Intervalo Base (5s)
- **Trade-off**: Balance entre frescura de datos y carga
- **Justificación**: Para un dashboard de inventario, 5s es suficientemente rápido sin saturar el servidor

### Intervalo Máximo (60s)
- **Trade-off**: Cliente descansa vs datos desactualizados
- **Justificación**: 60s es el máximo tolerable para inventario. En tiempo real sería menor.

### Backoff Multiplicador (1.5)
- **Trade-off**: Crecimiento suave vs recuperación rápida
- **Justificación**: No queremos que suba demasiado rápido (ahorro de ancho de banda) ni que tarde mucho en bajar cuando hay actividad

### Callbacks Síncronos
- **Trade-off**: Simplicidad vs no bloquear
- **Justificación**: Para este caso de uso, los callbacks son rápidos. Si fueran lentos (escritura a disco), usaríamos `asyncio.create_task()`.

---

## Pruebas Realizadas (Reto 4)

Ver archivo `validacion.log` para los resultados de:

1. ✅ Happy path - Servidor responde 200 con datos nuevos
2. ✅ Sin cambios - Servidor responde 304, intervalo crece
3. ✅ Servidor caído - Timeout, backoff aplicado
4. ✅ Error 500 - Backoff y notificación de error
5. ✅ Observador falla - Otros observadores siguen funcionando
6. ✅ Detención limpia - Sin tareas huérfanas

---

## Migración a WebSocket (Reto 5 - Opcional)

Para migrar a WebSocket sin cambiar los observadores:

```python
class ServicioWebSocket(Observable):
    # Mismos métodos: suscribir, desuscribir, notificar
    # Diferente implementación:
    # - iniciar(): Conecta WebSocket
    # - _recibir_mensaje(): Parsea y notifica
    # - detener(): Cierra conexión limpiamente

    # Los observadores (UI, alertas, logs) NO cambian
    # Solo cambia la fuente de eventos: polling → WebSocket
```

**Lo que cambia:**
- Lógica de conexión (HTTP polling → WebSocket persistente)
- Manejo de estado de conexión (Conectado/Reconectando)

**Lo que NO cambia:**
- Los 4 observadores
- La interfaz Observable (suscribir/notificar)
- La reacción a eventos

---

## Autor

- **Nombre:** Kevin Varick Gongora Silva
- **Fecha:** 2026-03-12
- **Asignatura:** Programación Distribuida del Lado del Cliente
- **Semana:** 4 - Patrones de Comunicación (Polling y Observer)
