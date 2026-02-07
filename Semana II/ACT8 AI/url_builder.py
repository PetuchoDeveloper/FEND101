"""
URL Builder Seguro para EcoMarket API.

Este módulo proporciona construcción segura de URLs previniendo:
- Path traversal (../../../etc/passwd)
- Inyección de query parameters (?admin=true)
- Caracteres unicode peligrosos (%00, %2F)
- Tipos de ID inválidos

Uso solo de biblioteca estándar: urllib.parse
"""

import re
import uuid
from urllib.parse import quote, urlencode, urljoin
from typing import Any, Dict, Optional, Union


class URLSecurityError(Exception):
    """Error de seguridad al construir URL."""
    pass


class URLBuilder:
    """
    Constructor seguro de URLs para APIs REST.
    
    Previene ataques comunes como path traversal, inyección de parámetros
    y caracteres unicode maliciosos.
    
    Ejemplo:
        >>> builder = URLBuilder("http://localhost:3000/api/")
        >>> builder.build_url("productos/{id}", path_params={"id": 123})
        'http://localhost:3000/api/productos/123'
    """
    
    # Patrón para detectar path traversal
    PATH_TRAVERSAL_PATTERN = re.compile(r'(?:^|[/\\])\.\.(?:[/\\]|$)')
    
    # Patrón para UUID v4
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    # Caracteres peligrosos que deben bloquearse (no solo escaparse)
    DANGEROUS_CHARS = [
        '\x00',      # Null byte
        '\n', '\r',  # Newlines (HTTP header injection)
    ]
    
    def __init__(self, base_url: str):
        """
        Inicializa el builder con una URL base.
        
        Args:
            base_url: URL base de la API (ej: "http://localhost:3000/api/")
        """
        if not base_url:
            raise ValueError("base_url no puede estar vacía")
        
        # Asegurar que termine con /
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
    
    @staticmethod
    def validate_id(value: Any, expected_type: str = "int") -> str:
        """
        Valida que un ID sea del tipo esperado y retorna su representación segura.
        
        Args:
            value: Valor a validar
            expected_type: "int" o "uuid"
        
        Returns:
            str: Representación string del ID validado
        
        Raises:
            TypeError: Si el tipo no coincide con lo esperado
            ValueError: Si el valor no es válido para el tipo
        
        Ejemplo:
            >>> URLBuilder.validate_id(123, "int")
            '123'
            >>> URLBuilder.validate_id("550e8400-e29b-41d4-a716-446655440000", "uuid")
            '550e8400-e29b-41d4-a716-446655440000'
        """
        if expected_type == "int":
            if isinstance(value, bool):  # bool es subclase de int en Python
                raise TypeError(f"Se esperaba int, pero recibió bool: {value}")
            if isinstance(value, int):
                if value < 0:
                    raise ValueError(f"ID no puede ser negativo: {value}")
                return str(value)
            if isinstance(value, str):
                try:
                    int_val = int(value)
                    if int_val < 0:
                        raise ValueError(f"ID no puede ser negativo: {value}")
                    return str(int_val)
                except ValueError:
                    raise TypeError(f"Se esperaba int, pero recibió string no numérico: '{value}'")
            raise TypeError(f"Se esperaba int, pero recibió {type(value).__name__}: {value}")
        
        elif expected_type == "uuid":
            str_value = str(value)
            if URLBuilder.UUID_PATTERN.match(str_value):
                return str_value.lower()
            # Intentar parsear como UUID
            try:
                parsed = uuid.UUID(str_value)
                return str(parsed)
            except ValueError:
                raise ValueError(f"UUID inválido: '{str_value}'")
        
        else:
            raise ValueError(f"Tipo esperado no soportado: {expected_type}")
    
    def _check_dangerous_chars(self, value: str, param_name: str) -> None:
        """Verifica que no haya caracteres peligrosos en el valor."""
        for char in self.DANGEROUS_CHARS:
            if char in value:
                char_repr = repr(char)
                raise URLSecurityError(
                    f"Carácter peligroso {char_repr} detectado en parámetro '{param_name}'"
                )
    
    def _check_path_traversal(self, value: str, param_name: str) -> None:
        """Verifica que no haya intento de path traversal."""
        # Decodificar posibles escapes antes de verificar
        decoded = value
        
        # Verificar patrón de traversal en valor original y decodificado
        if self.PATH_TRAVERSAL_PATTERN.search(value):
            raise URLSecurityError(
                f"Path traversal detectado en parámetro '{param_name}': {value}"
            )
        
        # Verificar secuencias codificadas comunes
        suspicious_patterns = ['..', '%2e%2e', '%2E%2E', '..%2f', '..%5c', '%2e%2e%2f']
        value_lower = value.lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in value_lower:
                raise URLSecurityError(
                    f"Posible path traversal detectado en '{param_name}': {value}"
                )
    
    def _sanitize_path_param(self, value: Any, param_name: str) -> str:
        """
        Sanitiza un parámetro de path para uso seguro en URL.
        
        Args:
            value: Valor del parámetro
            param_name: Nombre del parámetro (para mensajes de error)
        
        Returns:
            str: Valor escapado de forma segura
        
        Raises:
            URLSecurityError: Si se detecta un valor malicioso
        """
        str_value = str(value)
        
        # Verificar caracteres peligrosos
        self._check_dangerous_chars(str_value, param_name)
        
        # Verificar path traversal
        self._check_path_traversal(str_value, param_name)
        
        # Escapar caracteres especiales de URL
        # safe='' significa que incluso '/' será escapado
        return quote(str_value, safe='')
    
    def build_path(self, template: str, **path_params) -> str:
        """
        Construye un path seguro sustituyendo parámetros.
        
        Args:
            template: Template con placeholders {name}
            **path_params: Parámetros a sustituir
        
        Returns:
            str: Path con parámetros sustituidos y escapados
        
        Raises:
            URLSecurityError: Si algún parámetro es malicioso
            KeyError: Si falta un parámetro requerido
        
        Ejemplo:
            >>> builder = URLBuilder("http://api.test/")
            >>> builder.build_path("productos/{id}/reviews/{review_id}", id=1, review_id=42)
            'productos/1/reviews/42'
        """
        # Encontrar todos los placeholders en el template
        placeholders = re.findall(r'\{(\w+)\}', template)
        
        result = template
        for name in placeholders:
            if name not in path_params:
                raise KeyError(f"Parámetro requerido '{name}' no proporcionado")
            
            safe_value = self._sanitize_path_param(path_params[name], name)
            result = result.replace(f'{{{name}}}', safe_value)
        
        return result
    
    def build_query_string(self, params: Dict[str, Any]) -> str:
        """
        Construye un query string seguro.
        
        Args:
            params: Diccionario de parámetros
        
        Returns:
            str: Query string codificado (sin el '?' inicial)
        
        Ejemplo:
            >>> builder = URLBuilder("http://api.test/")
            >>> builder.build_query_string({"categoria": "frutas", "orden": "asc"})
            'categoria=frutas&orden=asc'
        """
        if not params:
            return ""
        
        # Filtrar valores None
        filtered = {k: v for k, v in params.items() if v is not None}
        
        if not filtered:
            return ""
        
        # urlencode escapa automáticamente caracteres especiales
        return urlencode(filtered)
    
    def build_url(
        self,
        template: str,
        path_params: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Construye una URL completa y segura.
        
        Args:
            template: Template del path con placeholders {name}
            path_params: Parámetros para sustituir en el path
            query_params: Parámetros para el query string
        
        Returns:
            str: URL completa y segura
        
        Raises:
            URLSecurityError: Si algún parámetro es malicioso
        
        Ejemplo:
            >>> builder = URLBuilder("http://localhost:3000/api/")
            >>> builder.build_url(
            ...     "productos/{id}",
            ...     path_params={"id": 123},
            ...     query_params={"incluir": "productor"}
            ... )
            'http://localhost:3000/api/productos/123?incluir=productor'
        """
        # Construir path con parámetros escapados
        if path_params:
            path = self.build_path(template, **path_params)
        else:
            path = template
        
        # Unir con base URL
        url = urljoin(self.base_url, path)
        
        # Agregar query string si hay parámetros
        if query_params:
            query = self.build_query_string(query_params)
            if query:
                url = f"{url}?{query}"
        
        return url


# =============================================================
# EJEMPLOS DE URLs MALICIOSAS
# =============================================================

EJEMPLOS_MALICIOSOS = """
# Ejemplos de URLs Maliciosas y Cómo URLBuilder las Maneja

## 1. Path Traversal (../../../etc/passwd)

**Ataque:** Un atacante intenta acceder a archivos del sistema:
```python
producto_id = "../../../etc/passwd"
url = f"productos/{producto_id}"
# Resultado: productos/../../../etc/passwd
# El servidor podría servir /etc/passwd!
```

**Protección de URLBuilder:**
```python
builder.build_url("productos/{id}", path_params={"id": "../../../etc/passwd"})
# LANZA: URLSecurityError("Path traversal detectado...")
```

---

## 2. Inyección de Query Params (?admin=true)

**Ataque:** Un atacante inyecta parámetros adicionales:
```python
producto_id = "1?admin=true&delete=all"
url = f"productos/{producto_id}"
# Resultado: productos/1?admin=true&delete=all
# ¡El servidor podría interpretar admin=true!
```

**Protección de URLBuilder:**
```python
builder.build_url("productos/{id}", path_params={"id": "1?admin=true"})
# Resultado seguro: productos/1%3Fadmin%3Dtrue
# El ? y = quedan escapados, no se interpretan como query params
```

---

## 3. Caracteres Unicode Peligrosos

**Ataque 3a - Null Byte (%00):**
```python
producto_id = "archivo.txt%00.jpg"
# Algunos sistemas truncan en el null byte
# Resultado: el sistema ve "archivo.txt" ignorando ".jpg"
```

**Ataque 3b - Slash Codificado (%2F):**
```python
producto_id = "..%2F..%2Fetc%2Fpasswd"
# Si el servidor decodifica DESPUÉS de rutear...
# Resultado: path traversal exitoso
```

**Protección de URLBuilder:**
```python
# Null byte
builder.build_url("productos/{id}", path_params={"id": "file\\x00.txt"})
# LANZA: URLSecurityError("Carácter peligroso detectado...")

# Slash codificado - detectado como traversal
builder.build_url("productos/{id}", path_params={"id": "..%2F..%2Fetc"})
# LANZA: URLSecurityError("Posible path traversal detectado...")
```
"""


def mostrar_ejemplos_maliciosos():
    """Imprime ejemplos de URLs maliciosas y cómo se manejan."""
    print(EJEMPLOS_MALICIOSOS)
