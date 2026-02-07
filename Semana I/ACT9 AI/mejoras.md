# Propuestas de Mejora del Cliente

Tras implementar la capa de observabilidad, propongo las siguientes 2 mejoras arquitectónicas para evolucionar el cliente:

## 1. Middleware / Hooks System
**Propuesta:** Implementar un sistema de "hooks" (pre_request, post_response) similar al que usa `requests` pero más estructurado, o un middleware pattern.
**Por qué:**
Actualmente, la lógica de logging está "quemada" dentro del método `_request` o en una clase auxiliar muy acoplada. Si mañana queremos añadir métricas (Prometheus), caché (Redis), o Rate Limiting del lado cliente, seguiremos engordando `_request`.
Un sistema de hooks permitiría inyectar comportamientos limpiamente:
```python
client = EcoMarketClient(plugins=[LoggingPlugin(), MetricsPlugin(), CachePlugin()])
```

## 2. Tipado Fuerte con Pydantic (Response Models)
**Propuesta:** Dejar de retornar `Dict` o `Any` y retornar objetos tipados (Modelos Pydantic).
**Por qué:**
El cliente actual devuelve diccionarios crudos. El consumidor no sabe qué campos esperar sin mirar la documentación o imprimir el JSON.
Al usar Pydantic:
- **Validación automática:** Si la API cambia el contrato, fallamos rápido y claro.
- **Developer Experience:** El IDE puede autocompletar `producto.nombre` en lugar de `producto['nombre']`.
- **Seguridad:** Filtramos campos inesperados o maliciosos extra.

```python
class Producto(BaseModel):
    id: UUID
    nombre: str
    precio: Decimal = Field(ge=0)

def obtener_producto(...) -> Producto:
    ...
```
