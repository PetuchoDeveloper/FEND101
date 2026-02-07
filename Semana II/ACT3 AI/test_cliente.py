"""
Script de pruebas para el cliente EcoMarket
Ejecutar DESPUÉS de iniciar servidor_mock.py
"""

from cliente_ecomarket import (
    listar_productos,
    obtener_producto,
    crear_producto,
    actualizar_producto_total,
    actualizar_producto_parcial,
    eliminar_producto,
    ProductoNoEncontrado,
    ProductoDuplicado
)

def separador(titulo):
    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print('='*50)

def main():
    print("\n🧪 PRUEBAS DEL CLIENTE ECOMARKET")
    print("Asegúrate de que servidor_mock.py esté corriendo\n")
    
    # --------------------------------------------------------
    separador("1. LISTAR PRODUCTOS (GET)")
    # --------------------------------------------------------
    productos = listar_productos()
    print(f"✅ Se encontraron {len(productos)} productos:")
    for p in productos:
        print(f"   - [{p['id']}] {p['nombre']} (${p['precio']})")
    
    # --------------------------------------------------------
    separador("2. OBTENER PRODUCTO (GET /{id})")
    # --------------------------------------------------------
    producto = obtener_producto(1)
    print(f"✅ Producto obtenido: {producto['nombre']}")
    print(f"   Categoría: {producto['categoria']}")
    print(f"   Precio: ${producto['precio']}")
    
    # --------------------------------------------------------
    separador("3. CREAR PRODUCTO (POST)")
    # --------------------------------------------------------
    nuevo = crear_producto({
        "nombre": "Jabón Artesanal",
        "precio": 12.50,
        "categoria": "higiene",
        "descripcion": "Jabón hecho a mano con ingredientes naturales",
        "stock": 75
    })
    print(f"✅ Producto creado con ID: {nuevo['id']}")
    print(f"   Nombre: {nuevo['nombre']}")
    
    # --------------------------------------------------------
    separador("4. CREAR PRODUCTO DUPLICADO (POST - 409)")
    # --------------------------------------------------------
    try:
        crear_producto({"nombre": "Jabón Artesanal", "precio": 10.00})
        print("❌ Debió lanzar ProductoDuplicado")
    except ProductoDuplicado as e:
        print(f"✅ Excepción correcta: ProductoDuplicado")
        print(f"   Mensaje: {e}")
    
    # --------------------------------------------------------
    separador("5. ACTUALIZACIÓN TOTAL (PUT)")
    # --------------------------------------------------------
    actualizado = actualizar_producto_total(nuevo['id'], {
        "nombre": "Jabón Artesanal Premium",
        "precio": 18.00,
        "categoria": "higiene",
        "descripcion": "Edición especial con aceites esenciales",
        "stock": 30
    })
    print(f"✅ Producto actualizado (PUT)")
    print(f"   Nombre: {actualizado['nombre']}")
    print(f"   Precio: ${actualizado['precio']} (era $12.50)")
    
    # --------------------------------------------------------
    separador("6. ACTUALIZACIÓN PARCIAL (PATCH)")
    # --------------------------------------------------------
    parcial = actualizar_producto_parcial(nuevo['id'], {
        "precio": 20.00,
        "stock": 25
    })
    print(f"✅ Producto actualizado (PATCH)")
    print(f"   Precio: ${parcial['precio']}")
    print(f"   Stock: {parcial['stock']}")
    print(f"   Nombre sin cambios: {parcial['nombre']}")
    
    # --------------------------------------------------------
    separador("7. ELIMINAR PRODUCTO (DELETE)")
    # --------------------------------------------------------
    eliminado = eliminar_producto(nuevo['id'])
    print(f"✅ Producto eliminado: {eliminado}")
    
    # --------------------------------------------------------
    separador("8. OBTENER PRODUCTO ELIMINADO (GET - 404)")
    # --------------------------------------------------------
    try:
        obtener_producto(nuevo['id'])
        print("❌ Debió lanzar ProductoNoEncontrado")
    except ProductoNoEncontrado as e:
        print(f"✅ Excepción correcta: ProductoNoEncontrado")
        print(f"   Mensaje: {e}")
    
    # --------------------------------------------------------
    separador("9. ELIMINAR PRODUCTO INEXISTENTE (DELETE - 404)")
    # --------------------------------------------------------
    try:
        eliminar_producto(9999)
        print("❌ Debió lanzar ProductoNoEncontrado")
    except ProductoNoEncontrado as e:
        print(f"✅ Excepción correcta: ProductoNoEncontrado")
        print(f"   Mensaje: {e}")
    
    # --------------------------------------------------------
    separador("✅ TODAS LAS PRUEBAS COMPLETADAS")
    # --------------------------------------------------------
    productos_finales = listar_productos()
    print(f"Productos en la base de datos: {len(productos_finales)}")


if __name__ == '__main__':
    main()
