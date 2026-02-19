"""
Demo de Integración: SmartSession como Drop-in Replacement

Este script demuestra cómo usar SmartSession en lugar de ClientSession
sin cambiar el código existente del cliente de EcoMarket.
"""

import asyncio
import sys
import os

# Agregar la ruta del cliente async existente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ACT8 AI'))

# Importar el cliente async existente
try:
    from cliente_ecomarket_async import (
        listar_productos,
        obtener_producto,
        crear_producto,
        cargar_dashboard,
        crear_multiples_productos
    )
except ImportError as e:
    print(f"❌ Error importando cliente: {e}")
    print("   Asegúrate de que el cliente existe en: Semana III/ACT8 AI/")
    sys.exit(1)

# Importar SmartSession
from smart_session import SmartSession, create_balanced_session


MOCK_SERVER_URL = "http://127.0.0.1:8888"


async def demo_basic_usage():
    """Demo 1: Uso básico como reemplazo de ClientSession"""
    
    print("\n" + "="*70)
    print("Demo 1: Uso Básico - Drop-in Replacement")
    print("="*70 + "\n")
    
    print("📝 ANTES (con ClientSession normal):")
    print("   async with aiohttp.ClientSession() as session:")
    print("       productos = await listar_productos(session)")
    
    print("\n📝 DESPUÉS (con SmartSession):")
    print("   async with SmartSession(max_connections=20) as session:")
    print("       productos = await listar_productos(session)")
    print("       stats = session.get_pool_stats()  # 🎁 Bonus!")
    
    print("\n🚀 Ejecutando...\n")
    
    # Usar SmartSession exactamente como ClientSession
    async with SmartSession(
        max_connections=20,
        max_connections_per_host=10
    ) as session:
        try:
            # Estas son las MISMAS funciones del cliente existente
            # ¡No se requiere ningún cambio!
            productos = await listar_productos(session)
            
            print(f"✅ Listados {len(productos)} productos del mock server")
            
            # Bonus: Ver estadísticas del pool
            stats = session.get_pool_stats()
            print(f"\n📊 Pool Stats:")
            print(f"   Conexiones activas: {stats['active']}")
            print(f"   Conexiones idle:    {stats['idle']}")
            print(f"   Conexiones creadas: {stats['metrics']['created']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("   (Este es un mock server, algunos endpoints pueden no existir)")


async def demo_dashboard_with_monitoring():
    """Demo 2: Cargar dashboard con monitoreo del pool"""
    
    print("\n" + "="*70)
    print("Demo 2: Dashboard con Monitoreo de Pool")
    print("="*70 + "\n")
    
    async with SmartSession(
        max_connections=30,
        enable_monitoring=True,
        health_check_interval=2.0
    ) as session:
        
        print("🚀 Ejecutando múltiples peticiones paralelas...\n")
        
        # Simular carga de dashboard con múltiples endpoints
        tasks = []
        for i in range(10):
            tasks.append(session.get(f"{MOCK_SERVER_URL}/test"))
        
        start_time = asyncio.get_event_loop().time()
        
        # Ejecutar en paralelo
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Cerrar las respuestas
        for resp in responses:
            if hasattr(resp, 'close'):
                resp.close()
        
        print(f"✅ 10 peticiones completadas en {elapsed:.2f}s\n")
        
        # Mostrar reporte del pool
        await session.print_pool_report()
        
        print("💡 Observa cómo el pool reutiliza conexiones en lugar de crear nuevas")


async def demo_batch_operations():
    """Demo 3: Operaciones masivas con límite de concurrencia"""
    
    print("\n" + "="*70)
    print("Demo 3: Creación Masiva con Pool Limitado")
    print("="*70 + "\n")
    
    # Crear sesión con pool pequeño para demostrar cola de espera
    async with SmartSession(
        max_connections=5,  # Pool pequeño intencional
        max_connections_per_host=5,
        enable_monitoring=False
    ) as session:
        
        print("📦 Configuración:")
        print("   Pool size:      5 conexiones")
        print("   Peticiones:     15 concurrentes")
        print("   Expectativa:    10 requests esperarán en cola\n")
        
        print("🚀 Ejecutando...\n")
        
        # Simular 15 peticiones concurrentes con pool de 5
        tasks = []
        for i in range(15):
            tasks.append(session.get(f"{MOCK_SERVER_URL}/test"))
        
        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Cerrar respuestas
        for resp in responses:
            if hasattr(resp, 'close'):
                resp.close()
        
        print(f"✅ 15 peticiones completadas en {elapsed:.2f}s\n")
        
        await session.print_pool_report()
        
        stats = session.get_pool_stats()
        
        print("\n📊 Análisis:")
        print(f"   Conexiones creadas:     {stats['metrics']['created']}")
        print(f"   Conexiones reutilizadas: {stats['metrics']['reused']}")
        
        if stats['metrics']['created'] <= 5:
            print("\n   ✅ Perfecto! Solo se crearon 5 conexiones para 15 peticiones")
            print("      Las otras 10 esperaron en cola y reutilizaron conexiones")
        
        efficiency = (stats['metrics']['reused'] / 15 * 100) if stats['metrics']['reused'] > 0 else 0
        print(f"\n   Eficiencia de reutilización: {efficiency:.1f}%")


async def demo_preset_sessions():
    """Demo 4: Sesiones pre-configuradas"""
    
    print("\n" + "="*70)
    print("Demo 4: Sesiones Pre-configuradas")
    print("="*70 + "\n")
    
    print("SmartSession incluye 3 configuraciones predefinidas:\n")
    
    configs = [
        {
            "name": "create_high_concurrency_session()",
            "desc": "100 conexiones, ideal para dashboards y batch processing",
            "use_case": "Alta concurrencia, múltiples endpoints paralelos"
        },
        {
            "name": "create_balanced_session()",
            "desc": "50 conexiones, balance entre rendimiento y recursos",
            "use_case": "Aplicaciones típicas de producción"
        },
        {
            "name": "create_rate_limited_session()",
            "desc": "20 conexiones, ideal para APIs con rate limiting",
            "use_case": "APIs externas con límites estrictos"
        }
    ]
    
    for i, config in enumerate(configs, 1):
        print(f"{i}. {config['name']}")
        print(f"   {config['desc']}")
        print(f"   Caso de uso: {config['use_case']}")
        print()
    
    print("Ejemplo de uso:")
    print("   async with create_balanced_session() as session:")
    print("       productos = await listar_productos(session)")


async def main():
    """Ejecuta todas las demos"""
    
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║        Demo de Integración: SmartSession                       ║")
    print("║          Drop-in Replacement para ClientSession                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    # Verificar servidor mock
    import aiohttp
    
    print("\n🔍 Verificando servidor mock...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MOCK_SERVER_URL}/config",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    print("✅ Servidor mock detectado")
    except:
        print("\n❌ ERROR: Servidor mock no disponible")
        print("\n   Ejecuta en otra terminal:")
        print("   cd 'Semana III/ACT9 AI'")
        print("   python benchmark_mock_server.py\n")
        
        print("   Mostrando solo Demo 4 (no requiere servidor)...\n")
        await demo_preset_sessions()
        return
    
    # Ejecutar demos
    await demo_basic_usage()
    
    await asyncio.sleep(1)
    
    await demo_dashboard_with_monitoring()
    
    await asyncio.sleep(1)
    
    await demo_batch_operations()
    
    await asyncio.sleep(1)
    
    await demo_preset_sessions()
    
    print("\n" + "="*70)
    print("✅ Todas las demos completadas!")
    print("="*70)
    
    print("\n💡 Puntos clave:")
    print("   1. SmartSession es 100% compatible con ClientSession")
    print("   2. No requiere cambios en el código del cliente existente")
    print("   3. Añade visibilidad del pool de conexiones")
    print("   4. Permite optimizar la configuración según el caso de uso")
    print("   5. El health check detecta problemas automáticamente")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrumpida")
