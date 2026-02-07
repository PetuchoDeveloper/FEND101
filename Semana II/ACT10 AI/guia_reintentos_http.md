# Guía de Reintentos HTTP: Cuándo es Seguro y Cuándo NO

Esta guía explica las reglas de resiliencia para decidir si una petición HTTP puede reintentarse de forma segura.

---

## Tabla de Decisión Rápida

| Código | Significado | ¿Reintentar? | Razón |
|--------|-------------|--------------|-------|
| **2xx** | Éxito | ❌ No | Ya funcionó |
| **3xx** | Redirección | ❌ No | El cliente debe seguir la redirección |
| **400** | Bad Request | ❌ No | Datos malformados, no cambiará |
| **401** | Unauthorized | ❌ No | Falta autenticación, reintentar no ayuda |
| **403** | Forbidden | ❌ No | Sin permisos, no cambiará |
| **404** | Not Found | ❌ No | El recurso no existe |
| **409** | Conflict | ⚠️ Depende | Si es conflicto de versión, puede reintentarse con datos frescos |
| **422** | Unprocessable | ❌ No | Validación fallida |
| **429** | Rate Limited | ✅ Sí | Esperar y reintentar (respetar `Retry-After`) |
| **500** | Internal Error | ✅ Sí | Error transitorio del servidor |
| **502** | Bad Gateway | ✅ Sí | Problema de red/proxy transitorio |
| **503** | Unavailable | ✅ Sí | Servidor temporalmente sobrecargado |
| **504** | Gateway Timeout | ✅ Sí | Timeout transitorio |

---

## Regla de Oro: Idempotencia

> **Una operación es idempotente si ejecutarla N veces produce el mismo resultado que ejecutarla 1 vez.**

### Métodos HTTP y su Idempotencia

```
┌─────────────────────────────────────────────────────────────┐
│  Método   │ Idempotente │ Seguro reintentar               │
├───────────┼─────────────┼─────────────────────────────────┤
│  GET      │     ✅      │  Siempre                        │
│  HEAD     │     ✅      │  Siempre                        │
│  OPTIONS  │     ✅      │  Siempre                        │
│  PUT      │     ✅      │  Siempre (reemplaza el recurso) │
│  DELETE   │     ✅      │  Siempre (ya está borrado)      │
│  POST     │     ❌      │  ⚠️ Solo con Idempotency-Key    │
│  PATCH    │     ⚠️      │  Depende de la implementación   │
└─────────────────────────────────────────────────────────────┘
```

---

## Errores 4xx: NO Reintentar (Error del Cliente)

Los errores 4xx indican que **TÚ (el cliente) hiciste algo mal**. Reintentar la misma petición producirá el mismo error.

### 400 Bad Request
```
❌ Reintentar NO ayudará
```
- Los datos están malformados
- JSON inválido, campos faltantes, tipos incorrectos
- **Acción**: Corregir los datos antes de reintentar

### 401 Unauthorized
```
❌ Reintentar NO ayudará
```
- Token faltante o expirado
- **Acción**: Obtener nuevo token y reintentar (pero eso es una petición diferente)

### 403 Forbidden
```
❌ Reintentar NO ayudará
```
- El usuario no tiene permisos para este recurso
- **Acción**: Escalar al administrador o cambiar el usuario

### 404 Not Found
```
❌ Reintentar NO ayudará
```
- El recurso no existe
- **Acción**: Verificar el ID/URL

### 422 Unprocessable Entity
```
❌ Reintentar NO ayudará
```
- Los datos son sintácticamente correctos pero semánticamente inválidos
- Ejemplo: edad = -5, email sin @
- **Acción**: Corregir los datos

---

## Errores 5xx: SÍ Reintentar (Error del Servidor)

Los errores 5xx indican que **el servidor tuvo un problema** que probablemente es transitorio.

### 500 Internal Server Error
```
✅ Reintentar con backoff
```
- Bug del servidor, estado corrupto temporal
- Usualmente se recupera en segundos/minutos

### 502 Bad Gateway
```
✅ Reintentar con backoff
```
- El proxy no pudo conectar con el servidor backend
- Común durante deploys

### 503 Service Unavailable
```
✅ Reintentar con backoff + respeta Retry-After
```
- Servidor sobrecargado o en mantenimiento
- Buscar header `Retry-After` para saber cuánto esperar

### 504 Gateway Timeout
```
✅ Reintentar con backoff
```
- El proxy esperó demasiado al backend
- Problema transitorio de latencia

---

## ⚠️ Casos Especiales

### POST sin Idempotency-Key

```
POST /ordenes
{
  "producto": "laptop",
  "cantidad": 1
}
```

**El peligro**:
1. Envías POST → servidor crea orden #123
2. Conexión se corta ANTES de recibir respuesta
3. Tu cliente piensa que falló
4. Reintentas POST → servidor crea orden #124
5. **Resultado**: 2 órdenes duplicadas 💸

**La solución: Idempotency-Key**

```http
POST /ordenes
Idempotency-Key: abc-123-unique-id
{
  "producto": "laptop",
  "cantidad": 1
}
```

El servidor:
1. Recibe petición con `Idempotency-Key: abc-123`
2. Guarda: `{"abc-123": orden #123}` 
3. Si recibe otro POST con el mismo key, retorna orden #123 sin crear nueva

### 429 Too Many Requests

```
⚠️ Reintentar, pero con MUCHO cuidado
```

429 dice: "Estás enviando demasiadas peticiones". Si reintentas inmediatamente, empeorarás el problema.

**Estrategia correcta**:
1. Leer header `Retry-After` (segundos o fecha)
2. Esperar ESE tiempo exacto
3. Reducir frecuencia de peticiones futuras

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

### PATCH (Idempotencia Parcial)

PATCH puede o no ser idempotente, depende de la operación:

```
✅ IDEMPOTENTE (seguro reintentar):
PATCH /usuario/1
{ "email": "nuevo@example.com" }
→ Siempre resulta en el mismo email

❌ NO IDEMPOTENTE (NO reintentar):
PATCH /contador/1
{ "incrementar": 1 }
→ Cada reintento incrementa más
```

---

## Cuándo NUNCA Reintentar (Aunque sea 5xx)

### 1. Circuit Breaker Abierto

Si ya fallaron 50+ peticiones seguidas al mismo servicio:

```
┌──────────────────────────────────────────┐
│         CIRCUIT BREAKER                   │
│                                          │
│  Normal: Closed → permites peticiones    │
│  50 fallos seguidos → Open               │
│  Open: Fallas inmediatamente (no retry)  │
│  Después de 30s → Half-Open              │
│  Half-Open: pruebas 1 petición           │
│  Si funciona → Closed                    │
│  Si falla → Open de nuevo                │
└──────────────────────────────────────────┘
```

### 2. Timeout Muy Largo (> 60s)

Si una petición tardó 60+ segundos antes de fallar:
- El servidor probablemente está muy sobrecargado
- Reintentar solo empeorará las cosas
- Mejor: fallar rápido, alertar al equipo

### 3. Errores de Negocio Disfrazados de 500

Algunos servidores mal diseñados retornan 500 para:
- Validaciones fallidas
- Reglas de negocio no cumplidas
- Datos duplicados

Si ves un patrón de 500 consistente para ciertos datos, probablemente no es transitorio.

### 4. Peticiones que Modifican Estado Crítico

Incluso con idempotencia, algunas operaciones son demasiado riesgosas:

```
❌ NO reintentar automáticamente:
- Transferencias bancarias
- Envío de emails (podrían duplicarse)
- Notificaciones push
- Webhooks a terceros
```

Para estas: usa colas de mensajes con garantía de "exactly-once".

---

## Diagrama de Decisión

```
                    ¿Petición falló?
                          │
                          ▼
                 ┌────────┴────────┐
                 │ ¿Es error 4xx?  │
                 └────────┬────────┘
                    │           │
                   Sí          No
                    │           │
                    ▼           ▼
              ❌ NO reintentar  ┌────────────────┐
                               │ ¿Es error 5xx  │
                               │ o timeout?     │
                               └───────┬────────┘
                                  │          │
                                 Sí         No
                                  │          │
                                  ▼          ▼
                          ┌──────────────┐   ⚠️ Analizar
                          │ ¿El método   │
                          │ es idempotente?│
                          └──────┬───────┘
                            │         │
                           Sí        No
                            │         │
                            ▼         ▼
                    ✅ Reintentar   ┌──────────────┐
                    con backoff    │ ¿Tiene       │
                                   │ Idempotency- │
                                   │ Key?         │
                                   └──────┬───────┘
                                      │       │
                                     Sí      No
                                      │       │
                                      ▼       ▼
                              ✅ Reintentar  ❌ NO reintentar
                                             (riesgo de
                                              duplicación)
```

---

## Resumen de Mejores Prácticas

1. **GET, PUT, DELETE**: Siempre seguro reintentar
2. **POST**: Solo con `Idempotency-Key`
3. **4xx**: Nunca reintentar (corregir datos primero)
4. **5xx**: Reintentar con exponential backoff + jitter
5. **429**: Respetar `Retry-After` exactamente
6. **Operaciones críticas**: Usar colas con exactly-once
7. **Muchos fallos seguidos**: Implementar Circuit Breaker
