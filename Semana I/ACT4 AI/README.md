# ACT4: Cliente HTTP para EcoMarket API

## 📚 Descripción del Proyecto

Este proyecto implementa un cliente HTTP para consumir la API de EcoMarket, diseñado como ejercicio de aprendizaje para entender cómo funcionan las peticiones HTTP en aplicaciones frontend.

## 🗂️ Archivos

| Archivo | Descripción |
|---------|-------------|
| `ecomarket_client.py` | Cliente HTTP en Python usando la biblioteca `requests` |
| `ecomarket_client.ts` | Cliente HTTP en TypeScript usando la API nativa `fetch` |

## 🚀 ¿Cómo ejecutar?

### Python

```bash
# Instalar dependencia
pip install requests

# Ejecutar
python ecomarket_client.py
```

### TypeScript

```bash
# Opción 1: Usar ts-node (más rápido para desarrollo)
npx ts-node ecomarket_client.ts

# Opción 2: Compilar y ejecutar
tsc ecomarket_client.ts
node ecomarket_client.js
```

## 📡 Endpoints Implementados

### 1. GET /productos - Listar productos
- Obtiene todos los productos disponibles
- Soporta filtros opcionales: `categoria`, `productor_id`
- Maneja errores de red (timeout, servidor no disponible)

### 2. GET /productos/{id} - Obtener producto
- Obtiene detalles de un producto específico
- Maneja el caso 404 con mensaje amigable

### 3. POST /productos - Crear producto
- Envía JSON en el body con los datos del producto
- Incluye headers `Content-Type` y `Authorization`
- Maneja respuestas 201 (éxito), 400 (validación), 401 (auth), 403 (permisos)

## 🔧 Comparación de Bibliotecas

| Aspecto | Python `requests` | TypeScript `fetch` |
|---------|-------------------|-------------------|
| **Instalación** | Requiere `pip install` | Nativo (Node.js 18+) |
| **Sintaxis** | Muy intuitiva | Moderna con async/await |
| **JSON** | `.json()` automático | `.json()` devuelve Promise |
| **Timeout** | Parámetro directo | Requiere AbortController |
| **Manejo de errores** | Excepciones explícitas | Verificar `response.ok` |

## 📖 Conceptos Clave

### Headers HTTP
- **Content-Type**: Indica el formato del body (`application/json`)
- **Authorization**: Token de autenticación (`Bearer <token>`)

### Códigos de Estado
| Código | Significado |
|--------|-------------|
| 200 | OK - Petición exitosa |
| 201 | Created - Recurso creado |
| 400 | Bad Request - Error de validación |
| 401 | Unauthorized - Sin autenticación |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no existe |
| 500 | Internal Server Error - Error del servidor |

### Manejo de Errores
1. **Timeout**: El servidor no responde a tiempo
2. **Connection Error**: No hay conexión de red
3. **HTTP Error**: El servidor devuelve un código de error

## ✨ Buenas Prácticas Implementadas

1. **Funciones reutilizables**: Cada operación es una función independiente
2. **Tipado**: TypeScript usa interfaces para definir estructuras
3. **Comentarios**: Cada sección explica el propósito del código
4. **Mensajes amigables**: Los errores se muestran de forma comprensible
5. **Configuración centralizada**: URL base y timeout en constantes
