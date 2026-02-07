import datetime

def validar_producto(data):
    """
    Valida un objeto JSON de producto.
    Retorna True si es válido, lanza una excepción ValueError si no.
    """
    
    # 1. Validar campos requeridos
    campos_requeridos = ["id", "nombre", "precio", "categoria", "productor", "creado_en"]
    for campo in campos_requeridos:
        if campo not in data:
            raise ValueError(f"Falta el campo requerido: {campo}")

    # 2. Validar tipos de datos
    if not isinstance(data["id"], int):
        raise ValueError(f"El campo 'id' debe ser int, se recibió: {type(data['id']).__name__}")
    
    if not isinstance(data["precio"], (int, float)):
        raise ValueError(f"El campo 'precio' debe ser float o int, se recibió: {type(data['precio']).__name__}")
        
    if "disponible" in data and not isinstance(data["disponible"], bool):
         raise ValueError(f"El campo 'disponible' debe ser bool, se recibió: {type(data['disponible']).__name__}")

    # 3. Validar reglas de negocio (precio positivo)
    if data["precio"] <= 0:
        raise ValueError("El precio debe ser positivo")

    # 4. Validar categoría (enum)
    categorias_validas = ["frutas", "verduras", "lacteos", "miel", "conservas"]
    if data["categoria"] not in categorias_validas:
        raise ValueError(f"Categoría inválida. Debe ser una de: {categorias_validas}")

    # 5. Validar objetos anidados (productor)
    productor = data["productor"]
    if not isinstance(productor, dict):
         raise ValueError("El campo 'productor' debe ser un objeto JSON")
    
    if "id" not in productor:
        raise ValueError("El campo 'productor.id' es requerido")
    if not isinstance(productor["id"], int):
        raise ValueError("El campo 'productor.id' debe ser int")
        
    if "nombre" not in productor:
        raise ValueError("El campo 'productor.nombre' es requerido")
    if not isinstance(productor["nombre"], str):
        raise ValueError("El campo 'productor.nombre' debe ser str")

    # 6. Validar formato de fecha (ISO 8601)
    try:
        # Intenta parsear la fecha. strptime o fromisoformat (Python 3.7+)
        # Asumiendo formato con Z o offset
        datetime.datetime.fromisoformat(data["creado_en"].replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Formato de fecha inválido, debe ser ISO 8601 (ej. 2024-01-15T10:30:00Z)")

    return True
