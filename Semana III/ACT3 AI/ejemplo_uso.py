"""
Ejemplo de uso del cliente asíncrono de EcoMarket

Este script demuestra las 3 funcionalidades principales:
1. Operaciones CRUD básicas
2. Carga paralela del dashboard
3. Creación masiva de productos
"""

import asyncio
import aiohttp
import cliente_ecomarket_async as client


async def ejemplo_1_operaciones_basicas():
    """Demuestra operaciones CRUD individuales"""
    print("\n" + "="*60)
    print("EJEMPLO 1: Operaciones Básicas")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Listar productos
            print("\n📋 Listando productos...")
            productos = await client.listar_productos(session)
            print(f"   ✅ Total: {len(productos)} productos")
            
            # Obtener primer producto
            if productos:
                primer_id = productos[0]['id']
                print(f"\n🔍 Obteniendo producto ID {primer_id}...")
                producto = await client.obtener_producto(session, primer_id)
                print(f"   ✅ Producto: {producto['nombre']} - ${producto['precio']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def ejemplo_2_dashboard_paralelo():
    """Demuestra carga paralela de múltiples endpoints"""
    print("\n" + "="*60)
    print("EJEMPLO 2: Carga Paralela del Dashboard")
    print("="*60)
    
    try:
        print("\n⚡ Ejecutando 3 peticiones EN PARALELO...")
        import time
        inicio = time.perf_counter()
        
        resultado = await client.cargar_dashboard()
        
        fin = time.perf_counter()
        tiempo = fin - inicio
        
        print(f"   ⏱️  Tiempo total: {tiempo:.4f}s")
        print()
        
        # Mostrar resultados
        datos = resultado["datos"]
        errores = resultado["errores"]
        
        if datos["productos"]:
            print(f"   ✅ Productos: {len(datos['productos'])} items cargados")
        
        if datos["categorias"]:
            print(f"   ✅ Categorías: {len(datos['categorias'])} items cargados")
        
        if datos["perfil"]:
            print(f"   ✅ Perfil: {datos['perfil'].get('nombre', 'cargado')}")
        
        if errores:
            print(f"\n   ⚠️  Errores encontrados:")
            for error in errores:
                print(f"      - {error['endpoint']}: {error['error']}")
        else:
            print("\n   🎉 ¡Todos los endpoints cargados exitosamente!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def ejemplo_3_creacion_masiva():
    """Demuestra creación masiva de productos con control de concurrencia"""
    print("\n" + "="*60)
    print("EJEMPLO 3: Creación Masiva de Productos")
    print("="*60)
    
    # Preparar lista de productos a crear
    productos_a_crear = [
        {"nombre": "Manzanas Orgánicas", "precio": 25.0, "categoria": "frutas"},
        {"nombre": "Leche de Cabra", "precio": 35.0, "categoria": "lacteos"},
        {"nombre": "Miel Natural", "precio": 80.0, "categoria": "miel"},
        {"nombre": "Zanahorias", "precio": 15.0, "categoria": "verduras"},
        {"nombre": "Mermelada de Fresa", "precio": 45.0, "categoria": "conservas"},
    ]
    
    try:
        print(f"\n📦 Creando {len(productos_a_crear)} productos en paralelo...")
        print("   (máximo 5 peticiones simultáneas)")
        
        import time
        inicio = time.perf_counter()
        
        creados, fallidos = await client.crear_multiples_productos(
            productos_a_crear,
            max_concurrencia=5
        )
        
        fin = time.perf_counter()
        tiempo = fin - inicio
        
        print(f"\n   ⏱️  Tiempo total: {tiempo:.4f}s")
        print(f"   ✅ Productos creados: {len(creados)}")
        print(f"   ❌ Productos fallidos: {len(fallidos)}")
        
        # Mostrar detalles de creados
        if creados:
            print("\n   📝 Productos creados:")
            for p in creados[:3]:  # Mostrar solo los primeros 3
                print(f"      • ID {p['id']}: {p['nombre']} - ${p['precio']}")
            if len(creados) > 3:
                print(f"      ... y {len(creados) - 3} más")
        
        # Mostrar errores si los hay
        if fallidos:
            print("\n   ⚠️  Productos fallidos:")
            for fallo in fallidos:
                print(f"      • {fallo['datos']['nombre']}: {fallo['error']}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def main():
    """Función principal que ejecuta todos los ejemplos"""
    print("\n" + "█"*60)
    print("█  DEMOSTRACIÓN: Cliente Asíncrono de EcoMarket      █")
    print("█"*60)
    
    print("\n💡 Este script demuestra las ventajas del código asíncrono:")
    print("   • Ejecución paralela de peticiones")
    print("   • Control de concurrencia con semáforos")
    print("   • Manejo robusto de errores")
    print("   • Mejor rendimiento en operaciones I/O")
    
    # Ejecutar ejemplos
    await ejemplo_1_operaciones_basicas()
    await ejemplo_2_dashboard_paralelo()
    await ejemplo_3_creacion_masiva()
    
    print("\n" + "="*60)
    print("✨ Demostración completada")
    print("="*60)
    print("\n📚 Para más información, consulta:")
    print("   • README.md - Guía de uso completa")
    print("   • benchmark.md - Análisis de rendimiento")
    print()


if __name__ == "__main__":
    print("\n⚠️  IMPORTANTE: Asegúrate de que el servidor mock esté corriendo:")
    print("   python servidor_mock.py")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Ejecución interrumpida por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
