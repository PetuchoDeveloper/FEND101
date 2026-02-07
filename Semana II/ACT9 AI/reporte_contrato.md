# Reporte de Auditoría de Contrato API

**Fecha:** 2026-02-05 17:18:44

---

## Resumen

| Estado | Cantidad | Porcentaje |
|--------|----------|------------|
| ✅ Conformidad | 3 | 37.5% |
| ⚠️ Parcial | 5 | 62.5% |
| ❌ Faltante | 0 | 0.0% |
| **Total** | **8** | **100%** |

---

## Detalle por Endpoint

### ⚠️ GET /productos

**operationId:** `listarProductos`
**Estado:** Parcial
**Función:** `listar_productos()` (línea 124)
**Códigos esperados:** 200, 500, 503
**Códigos no manejados:** 200, 500, 503

### ⚠️ GET /productos/{id}

**operationId:** `obtenerProducto`
**Estado:** Parcial
**Función:** `obtener_producto()` (línea 155)
**Códigos esperados:** 200, 401, 404, 500
**Códigos no manejados:** 200, 401, 500

### ⚠️ DELETE /productos/{id}

**operationId:** `eliminarProducto`
**Estado:** Parcial
**Función:** `eliminar_producto()` (línea 342)
**Códigos esperados:** 204, 404, 500

**Problemas:**
- No valida esquema de respuesta

### ⚠️ GET /productos/buscar

**operationId:** `buscarProductos`
**Estado:** Parcial
**Función:** `buscar_productos()` (línea 385)
**Códigos esperados:** 200, 400, 500
**Códigos no manejados:** 200

### ⚠️ GET /productores/{productorId}/productos

**operationId:** `listarProductosProductor`
**Estado:** Parcial
**Función:** `listar_productos_productor()` (línea 461)
**Códigos esperados:** 200, 404, 500
**Códigos no manejados:** 200

### ✅ POST /productos

**operationId:** `crearProducto`
**Estado:** Conformidad
**Función:** `crear_producto()` (línea 193)
**Códigos esperados:** 201, 400, 409, 500

### ✅ PUT /productos/{id}

**operationId:** `actualizarProductoTotal`
**Estado:** Conformidad
**Función:** `actualizar_producto_total()` (línea 242)
**Códigos esperados:** 200, 400, 404, 409, 500

### ✅ PATCH /productos/{id}

**operationId:** `actualizarProductoParcial`
**Estado:** Conformidad
**Función:** `actualizar_producto_parcial()` (línea 292)
**Códigos esperados:** 200, 400, 404, 409, 500

---

## Acciones Requeridas

### Mejoras Requeridas

- [ ] `listar_productos()`: Manejar códigos 200, 500, 503
- [ ] `obtener_producto()`: Manejar códigos 200, 401, 500
- [ ] `eliminar_producto()`: No valida esquema de respuesta
- [ ] `buscar_productos()`: Manejar códigos 200
- [ ] `listar_productos_productor()`: Manejar códigos 200
