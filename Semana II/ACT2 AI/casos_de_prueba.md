# Casos de Prueba JSON Maliciosos o Malformados

Este documento detalla 6 ejemplos de JSON que la función de validación debe rechazar y explica por qué son problemáticos.

## 1. Falta de Campo Requerido
**JSON:**
```json
{
  "nombre": "Miel orgánica",
  "precio": 150.00,
  "categoria": "miel",
  "productor": { "id": 7, "nombre": "Apiarios del Valle" },
  "disponible": true,
  "creado_en": "2024-01-15T10:30:00Z"
}
```
**Razón:** Falta el campo `id`. Sin un identificador único, el sistema no puede rastrear o actualizar el producto correctamente.
**Resultado Esperado:** `ValueError: Falta el campo requerido: id`

## 2. Tipo de Dato Incorrecto
**JSON:**
```json
{
  "id": 42,
  "nombre": "Miel orgánica",
  "precio": "150.00",
  "categoria": "miel",
  "productor": { "id": 7, "nombre": "Apiarios del Valle" },
  "disponible": true,
  "creado_en": "2024-01-15T10:30:00Z"
}
```
**Razón:** El campo `precio` es una cadena (`string`) en lugar de un número (`float` o `int`). Esto causaría errores en cálculos matemáticos (impuestos, totales).
**Resultado Esperado:** `ValueError: El campo 'precio' debe ser float o int...`

## 3. Violación de Regla de Negocio (Precio Negativo)
**JSON:**
```json
{
  "id": 42,
  "nombre": "Miel orgánica",
  "precio": -50.00,
  "categoria": "miel",
  "productor": { "id": 7, "nombre": "Apiarios del Valle" },
  "disponible": true,
  "creado_en": "2024-01-15T10:30:00Z"
}
```
**Razón:** Aunque el tipo de dato es correcto (`float`), el valor es semánticamente inválido. Un precio negativo podría permitir a los usuarios "comprar" dinero.
**Resultado Esperado:** `ValueError: El precio debe ser positivo`

## 4. Categoría Inválida (Enum)
**JSON:**
```json
{
  "id": 42,
  "nombre": "Miel orgánica",
  "precio": 150.00,
  "categoria": "automotriz",
  "productor": { "id": 7, "nombre": "Apiarios del Valle" },
  "disponible": true,
  "creado_en": "2024-01-15T10:30:00Z"
}
```
**Razón:** "automotriz" no está en la lista permitida `[frutas, verduras, lacteos, miel, conservas]`. Esto rompe la consistencia de los datos y filtros de búsqueda.
**Resultado Esperado:** `ValueError: Categoría inválida...`

## 5. Formato de Fecha Inválido
**JSON:**
```json
{
  "id": 42,
  "nombre": "Miel orgánica",
  "precio": 150.00,
  "categoria": "miel",
  "productor": { "id": 7, "nombre": "Apiarios del Valle" },
  "disponible": true,
  "creado_en": "15/01/2024"
}
```
**Razón:** La fecha no sigue el estándar ISO 8601. Esto dificulta el ordenamiento y la interoperabilidad entre sistemas con diferentes configuraciones regionales.
**Resultado Esperado:** `ValueError: Formato de fecha inválido...`

## 6. Objeto Anidado Malformado (Productor sin ID)
**JSON:**
```json
{
  "id": 42,
  "nombre": "Miel orgánica",
  "precio": 150.00,
  "categoria": "miel",
  "productor": { 
    "nombre": "Apiarios Sin ID" 
  },
  "disponible": true,
  "creado_en": "2024-01-15T10:30:00Z"
}
```
**Razón:** El campo `productor` existe, pero le falta el sub-campo requerido `id`. Las validaciones deben ser recursivas y verificar también la integridad de los objetos anidados.
**Resultado Esperado:** `ValueError: El campo 'productor.id' es requerido`

