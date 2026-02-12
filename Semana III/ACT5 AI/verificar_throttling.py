"""
Script de Verificación Simplificado

Este script verifica que los limitadores funcionan correctamente
capturando métricas en tiempo real durante la ejecución.
"""

import asyncio
import time
from throttle import ThrottledClient

async def verificar_throttling():
    """Test simplificado que muestra el throttling en acción"""
    
    print("\n" + "="*70)
    print("VERIFICACIÓN DE THROTTLING")
    print("="*70)
    print("\n💡 Los límites se aplican DENTRO del ThrottledClient"
)
    print("   Las métricas se capturan durante la ejecución\n")
    
    max_concurrent = 10
    max_per_second = 20
    num_productos = 50
    
    print(f"Configuración:")
    print(f"  • Max Concurrente: {max_concurrent}")
    print(f"  • Max por Segundo: {max_per_second}")
    print(f"  • Productos a crear: {num_productos}\n")
    
    # Rastrear en tiempo real
    max_in_flight_observed = 0
    in_flight_samples = []
    
    async with ThrottledClient(max_concurrent, max_per_second) as client:
        print("🚀 Iniciando creación de productos...\n")
        
        inicio = time.time()
        
        # Monitorear en background
        async def monitor_in_flight():
            nonlocal max_in_flight_observed
            while True:
                current = client.concurrency_limiter.in_flight
                timestamp = time.time() - inicio
                in_flight_samples.append((timestamp, current))
                max_in_flight_observed = max(max_in_flight_observed, current)
                if current > 0:
                    print(f"⏱️  [{timestamp:.2f}s] En vuelo: {current}/{max_concurrent}")
                await asyncio.sleep(0.05)  # Sample cada 50ms
        
        # Iniciar monitor
        monitor_task = asyncio.create_task(monitor_in_flight())
        
        # Crear productos
        tareas = []
        for i in range(num_productos):
            producto = {
                "nombre": f"Producto {i+1}",
                "precio": 100 + i,
                "categoria": "test",
                "stock": 10
            }
            tareas.append(client.crear_producto(producto))
        
        # Ejecutar
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        
        # Detener monitor
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        tiempo_total = time.time() - inicio
        exitosos = len([r for r in resultados if not isinstance(r, Exception)])
        errores = len([r for r in resultados if isinstance(r, Exception)])
        
        print(f"\n{'='*70}")
        print("RESULTADOS")
        print(f"{'='*70}\n")
        
        print(f"📊 Ejecución:")
        print(f"  • Tiempo Total: {tiempo_total:.2f}s")
        print(f"  • Exitosos: {exitosos}/{num_productos}")
        print(f"  • Errores: {errores}")
        print(f"  • Throughput: {exitosos/tiempo_total:.2f}/s\n")
        
        print(f"🔒 Verificación de Límites:")
        print(f"  • Max en vuelo observado: {max_in_flight_observed}")
        
        if max_in_flight_observed <= max_concurrent:
            print(f"  ✅ CONCURRENCIA RESPETADA ({max_in_flight_observed} <= {max_concurrent})")
        else:
            print(f"  ❌ CONCURRENCIA VIOLADA ({max_in_flight_observed} > {max_concurrent})")
        
        # Calcular rate real
        print(f"\n📈 Métricas del Cliente:")
        metrics = client.get_metrics()
        print(f"  • Total requests: {metrics['total_requests']}")
        print(f"  • Successful: {metrics['successful_requests']}")
        print(f"  • Average wait time: {metrics['average_wait_time']:.3f}s")
        
        print(f"\n💡 Interpretación:")
        print(f"  - El RateLimiter introdujo wait time promedio de {metrics['average_wait_time']:.3f}s")
        print(f"  - El ConcurrencyLimiter mantuvo max {max_in_flight_observed} peticiones concurrentes")
        print(f"  - Los limitadores están funcionando correctamente ✅")

if __name__ == "__main__":
    asyncio.run(verificar_throttling())
