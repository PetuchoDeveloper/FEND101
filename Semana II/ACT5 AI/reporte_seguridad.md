# Reporte de Seguridad: URLBuilder para EcoMarket API

## Resumen Ejecutivo

El módulo `url_builder.py` proporciona construcción segura de URLs para el cliente de la API EcoMarket, previniendo varios tipos de ataques de inyección comunes en aplicaciones web.

---

## Ataques Prevenidos por URLBuilder

### 1. Path Traversal (Directory Traversal)

**Descripción:** El atacante intenta acceder a archivos fuera del directorio permitido usando secuencias como `../`.

**Ejemplo de ataque:**
```python
# Sin protección
producto_id = "../../../etc/passwd"
url = f"productos/{producto_id}"
# Resultado: productos/../../../etc/passwd
# El servidor podría exponer /etc/passwd
```

**Cómo URLBuilder protege:**
- Detecta secuencias `..` en paths
- Detecta variantes codificadas (`%2e%2e`, `%2F`)
- Detecta backslashes de Windows (`..\\..\\`)
- Lanza `URLSecurityError` inmediatamente

```python
# Con URLBuilder
url_builder.build_url("productos/{id}", path_params={"id": "../../../etc/passwd"})
# LANZA: URLSecurityError("Path traversal detectado...")
```

---

### 2. Inyección de Query Parameters

**Descripción:** El atacante inyecta parámetros adicionales en la URL para manipular el comportamiento del servidor.

**Ejemplo de ataque:**
```python
# Sin protección
producto_id = "1?admin=true&delete=all"
url = f"productos/{producto_id}"
# Resultado: productos/1?admin=true&delete=all
# El servidor interpreta admin=true como parámetro válido
```

**Cómo URLBuilder protege:**
- Escapa caracteres especiales (`?`, `&`, `=`, `#`)
- Usa `urllib.parse.quote()` con `safe=''`
- Los caracteres inyectados se codifican, no se interpretan

```python
# Con URLBuilder
url = url_builder.build_url("productos/{id}", path_params={"id": "1?admin=true"})
# Resultado: productos/1%3Fadmin%3Dtrue
# El ? se convierte en %3F - no se interpreta como query param
```

---

### 3. Caracteres Unicode/Encoding Peligrosos

#### 3a. Null Byte Injection
**Descripción:** El null byte (`\x00`) puede truncar strings en ciertos lenguajes/sistemas.

**Ejemplo de ataque:**
```python
producto_id = "archivo.txt\x00.jpg"
# Algunos sistemas ven solo "archivo.txt"
```

**Protección:** URLBuilder detecta y bloquea null bytes con `URLSecurityError`.

#### 3b. HTTP Header Injection
**Descripción:** Newlines pueden permitir inyectar headers HTTP adicionales.

**Ejemplo de ataque:**
```python
producto_id = "value\r\nX-Injected: malicious"
```

**Protección:** URLBuilder bloquea `\r` y `\n` en parámetros.

#### 3c. Slash Encoding Bypass
**Descripción:** Slashes codificados (`%2F`) pueden bypassear validaciones que solo revisan `/`.

**Protección:** URLBuilder detecta patrones sospechosos como `..%2F` y los bloquea.

---

### 4. Validación de Tipos de ID

**Problema:** Aceptar cualquier string como ID puede causar comportamiento inesperado.

**Protección de URLBuilder:**
```python
URLBuilder.validate_id(123, "int")     # ✅ "123"
URLBuilder.validate_id(-1, "int")       # ❌ ValueError (ID negativo)
URLBuilder.validate_id("abc", "int")    # ❌ TypeError
URLBuilder.validate_id(True, "int")     # ❌ TypeError (bool no es int)
URLBuilder.validate_id("550e8400-...", "uuid")  # ✅ UUID válido
```

---

## Ataques que Requieren Otras Defensas

| Ataque | Por qué URLBuilder NO protege | Defensa Requerida |
|--------|------------------------------|-------------------|
| **SQL Injection** | Ocurre en el servidor al procesar queries | Prepared statements, ORM |
| **XSS** | Ocurre al renderizar HTML | Escapar output, CSP headers |
| **CSRF** | Ataque a la sesión del usuario | Tokens CSRF, SameSite cookies |
| **Authentication Bypass** | Problema de lógica de autenticación | Validación de tokens server-side |
| **Rate Limiting** | Ataques de fuerza bruta | Rate limiting en servidor/proxy |
| **Insecure Direct Object Reference** | El servidor no valida permisos | Autorización server-side |

---

## Resumen de Implementación

### Archivos Creados

| Archivo | Propósito |
|---------|-----------|
| `url_builder.py` | Clase URLBuilder con sanitización y validación |
| `test_url_builder.py` | Tests demostrativos de protección |
| `reporte_seguridad.md` | Este documento |

### Integración en Cliente

```python
# Antes (inseguro)
url = f"productos/{producto_id}"

# Después (seguro)
url = url_builder.build_url(
    "productos/{id}",
    path_params={"id": producto_id}
)
```

### Dependencias

- **Solo biblioteca estándar:** `urllib.parse` (quote, urlencode, urljoin)
- **Sin dependencias externas**

---

## Recomendaciones Adicionales

1. **Siempre validar en el servidor** - URLBuilder protege el cliente, pero el servidor debe tener su propia validación.

2. **Usar HTTPS** - Para prevenir ataques man-in-the-middle.

3. **Logging de intentos de ataque** - Cuando URLBuilder lanza `URLSecurityError`, considera loggearlo para detección de intrusiones.

4. **Actualizar regularmente** - Nuevos vectores de ataque se descubren constantemente.

---

## Conclusión

URLBuilder proporciona una capa de defensa en profundidad para el cliente de la API EcoMarket, previniendo los ataques más comunes relacionados con la construcción de URLs. Sin embargo, es solo una parte de una estrategia de seguridad completa que debe incluir validación server-side, autenticación robusta y otras medidas de seguridad.
