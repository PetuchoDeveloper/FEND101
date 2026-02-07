"""
Test de integración: Cliente vs Servidor con datos inválidos
Ejecutar DESPUÉS de iniciar servidor_mock.py en ACT4 AI
"""

import requests
from cliente_ecomarket import (
    obtener_producto,
    listar_productos,
    crear_producto,
    ResponseValidationError,
    ProductoNoEncontrado
)
from validadores import ValidationError


def separador(titulo):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print('='*60)


def test_precio_negativo_desde_servidor():
    """
    Prueba que el cliente detecta cuando el servidor devuelve un precio negativo.
    Endpoint: GET /api/productos/invalido
    """
    print("\n🧪 Probando detección de precio negativo...")
    
    # Hacer petición directa al endpoint de prueba
    url = "http://localhost:3000/api/productos/invalido"
    response = requests.get(url)
    
    print(f"   📥 Respuesta del servidor: {response.json()}")
    print(f"   📊 Status: {response.status_code}")
    
    # Verificar que el servidor devolvió precio negativo
    data = response.json()
    assert data['precio'] < 0, "El servidor debería devolver precio negativo"
    print(f"   ⚠️  Precio recibido: ${data['precio']} (NEGATIVO)")
    
    # Ahora probar la validación manualmente
    from validadores import validar_producto, ValidationError
    
    try:
        validar_producto(data)
        print("   ❌ FALLÓ: No se detectó el precio negativo")
        return False
    except ValidationError as e:
        print(f"   ✅ DETECTADO: {e}")
        return True


def test_categoria_invalida_desde_servidor():
    """
    Prueba que el cliente detecta cuando el servidor devuelve categoría no permitida.
    Endpoint: GET /api/productos/categoria-invalida
    """
    print("\n🧪 Probando detección de categoría inválida...")
    
    url = "http://localhost:3000/api/productos/categoria-invalida"
    response = requests.get(url)
    
    data = response.json()
    print(f"   📥 Respuesta del servidor: {data}")
    print(f"   ⚠️  Categoría recibida: '{data['categoria']}' (NO VÁLIDA)")
    
    from validadores import validar_producto, ValidationError
    
    try:
        validar_producto(data)
        print("   ❌ FALLÓ: No se detectó la categoría inválida")
        return False
    except ValidationError as e:
        print(f"   ✅ DETECTADO: {e}")
        return True


def test_productos_validos():
    """
    Prueba que los productos válidos pasan la validación.
    Endpoint: GET /api/productos
    """
    print("\n🧪 Probando productos válidos del servidor...")
    
    try:
        productos = listar_productos()
        print(f"   ✅ Se obtuvieron y validaron {len(productos)} productos")
        for p in productos:
            print(f"      - [{p['id']}] {p['nombre']} (${p['precio']}) - {p['categoria']}")
        return True
    except ResponseValidationError as e:
        print(f"   ❌ Error de validación inesperado: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_obtener_producto_valido():
    """
    Prueba que obtener un producto válido funciona.
    """
    print("\n🧪 Probando obtener producto válido (ID=1)...")
    
    try:
        producto = obtener_producto(1)
        print(f"   ✅ Producto validado: {producto['nombre']}")
        print(f"      Precio: ${producto['precio']}")
        print(f"      Categoría: {producto['categoria']}")
        return True
    except ResponseValidationError as e:
        print(f"   ❌ Error de validación: {e}")
        return False


def test_crear_producto_valido():
    """
    Prueba crear un producto y validar la respuesta.
    """
    print("\n🧪 Probando crear producto nuevo...")
    
    try:
        nuevo = crear_producto({
            "nombre": "Conserva de Tomate Test",
            "precio": 35.00,
            "categoria": "conservas",
            "descripcion": "Salsa de tomate casera"
        })
        print(f"   ✅ Producto creado y validado: {nuevo['nombre']}")
        print(f"      ID asignado: {nuevo['id']}")
        return True
    except ResponseValidationError as e:
        print(f"   ❌ Error de validación: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  TEST DE INTEGRACIÓN: CLIENTE + SERVIDOR")
    print("  Verificando detección de respuestas inválidas")
    print("="*60)
    
    resultados = []
    
    separador("PRUEBAS DE DETECCIÓN DE ERRORES")
    resultados.append(("Precio negativo", test_precio_negativo_desde_servidor()))
    resultados.append(("Categoría inválida", test_categoria_invalida_desde_servidor()))
    
    separador("PRUEBAS DE OPERACIÓN NORMAL")
    resultados.append(("Listar productos", test_productos_validos()))
    resultados.append(("Obtener producto", test_obtener_producto_valido()))
    resultados.append(("Crear producto", test_crear_producto_valido()))
    
    separador("RESUMEN DE RESULTADOS")
    
    exitosos = sum(1 for _, r in resultados if r)
    fallidos = len(resultados) - exitosos
    
    for nombre, resultado in resultados:
        emoji = "✅" if resultado else "❌"
        print(f"   {emoji} {nombre}")
    
    print(f"\n   Total: {exitosos}/{len(resultados)} pruebas exitosas")
    
    if fallidos == 0:
        print("\n   🎉 ¡TODAS LAS PRUEBAS PASARON!")
    else:
        print(f"\n   ⚠️  {fallidos} prueba(s) fallaron")


if __name__ == '__main__':
    main()
