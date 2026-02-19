"""
Benchmark: Comparación de diferentes configuraciones de Connection Pool

Este script demuestra el impacto de diferentes límites de pool:
- Pool pequeño (5 conexiones): Bottleneck esperado
- Pool medio (20 conexiones): Balance adecuado
- Pool grande (ilimitado): Sin límites

Escenario: 50 peticiones concurrentes con server delay de 100ms
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import aiohttp
from smart_session import SmartSession


# Configuración del servidor mock
MOCK_SERVER_URL = "http://127.0.0.1:8888"
NUM_REQUESTS = 50
SERVER_DELAY_MS = 100


async def configure_mock_server(delay_ms: int):
    """Configura el delay del servidor mock"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MOCK_SERVER_URL}/config",
                json={"latency_ms": delay_ms},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    config = await response.json()
                    print(f"✅ Servidor mock configurado: {config['latency_ms']}ms delay")
                    return True
    except Exception as e:
        print(f"❌ Error configurando servidor mock: {e}")
        print(f"   Asegúrate de que el servidor esté corriendo en {MOCK_SERVER_URL}")
        return False


async def check_mock_server():
    """Verifica que el servidor mock esté disponible"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MOCK_SERVER_URL}/config",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    return True
    except:
        return False


async def make_request(session: SmartSession, request_id: int) -> Dict[str, Any]:
    """
    Hace una petición individual y registra métricas.
    
    Returns:
        dict: {
            "request_id": int,
            "duration": float (seconds),
            "success": bool,
            "error": str (if failed)
        }
    """
    start_time = time.time()
    
    try:
        async with session.get(
            f"{MOCK_SERVER_URL}/test",
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            await response.json()
            duration = time.time() - start_time
            
            return {
                "request_id": request_id,
                "duration": duration,
                "success": True
            }
    
    except Exception as e:
        duration = time.time() - start_time
        return {
            "request_id": request_id,
            "duration": duration,
            "success": False,
            "error": str(e)
        }


async def run_benchmark(
    pool_size: int,
    num_requests: int,
    pool_name: str
) -> Dict[str, Any]:
    """
    Ejecuta un benchmark con una configuración específica de pool.
    
    Args:
        pool_size: Límite de conexiones del pool
        num_requests: Número de peticiones concurrentes
        pool_name: Nombre descriptivo del benchmark
    
    Returns:
        dict: Resultados del benchmark con métricas
    """
    print(f"\n{'='*60}")
    print(f"Benchmark: {pool_name}")
    print(f"Pool size: {pool_size}, Requests: {num_requests}")
    print(f"{'='*60}\n")
    
    # Crear sesión con configuración específica
    async with SmartSession(
        max_connections=pool_size,
        max_connections_per_host=pool_size,
        enable_monitoring=True,
        health_check_interval=2.0
    ) as session:
        
        # Iniciar todas las peticiones concurrentemente
        start_time = time.time()
        
        tasks = [
            make_request(session, i)
            for i in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Obtener estadísticas finales del pool
        pool_stats = session.get_pool_stats()
        
        # Procesar resultados
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        durations = [r["duration"] for r in successful]
        
        # Calcular métricas
        metrics = {
            "pool_name": pool_name,
            "pool_size": pool_size,
            "num_requests": num_requests,
            "total_time": total_time,
            "throughput_rps": num_requests / total_time if total_time > 0 else 0,
            "successful": len(successful),
            "failed": len(failed),
            "latency": {
                "min": min(durations) * 1000 if durations else 0,
                "max": max(durations) * 1000 if durations else 0,
                "mean": statistics.mean(durations) * 1000 if durations else 0,
                "median": statistics.median(durations) * 1000 if durations else 0,
                "p95": statistics.quantiles(durations, n=20)[18] * 1000 if len(durations) >= 20 else (max(durations) * 1000 if durations else 0),
                "p99": statistics.quantiles(durations, n=100)[98] * 1000 if len(durations) >= 100 else (max(durations) * 1000 if durations else 0),
            },
            "pool_stats": pool_stats
        }
        
        # Imprimir reporte
        await session.print_pool_report()
        
        print(f"\n📊 Resultados:")
        print(f"   Tiempo total:      {total_time:.2f}s")
        print(f"   Throughput:        {metrics['throughput_rps']:.1f} req/s")
        print(f"   Exitosas:          {len(successful)}/{num_requests}")
        print(f"   Fallidas:          {len(failed)}")
        print(f"\n⏱️  Latencia:")
        print(f"   Min:               {metrics['latency']['min']:.1f}ms")
        print(f"   Mean:              {metrics['latency']['mean']:.1f}ms")
        print(f"   Median:            {metrics['latency']['median']:.1f}ms")
        print(f"   P95:               {metrics['latency']['p95']:.1f}ms")
        print(f"   P99:               {metrics['latency']['p99']:.1f}ms")
        print(f"   Max:               {metrics['latency']['max']:.1f}ms")
        
        return metrics


def print_comparison_table(results: List[Dict[str, Any]]):
    """Imprime una tabla comparativa de todos los benchmarks"""
    
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════════╗")
    print("║                    COMPARACIÓN DE CONFIGURACIONES DE POOL                      ║")
    print("║                      50 Requests Concurrentes | 100ms Server Delay            ║")
    print("╠════════════════════════════════════════════════════════════════════════════════╣")
    print("║ Config        │ Time(s) │  RPS   │ P95(ms) │ P99(ms) │ Created │ Reused │ Idle ║")
    print("╠═══════════════╪═════════╪════════╪═════════╪═════════╪═════════╪════════╪══════╣")
    
    for r in results:
        pool_name = r['pool_name'].ljust(13)
        time_val = f"{r['total_time']:.2f}".rjust(7)
        rps_val = f"{r['throughput_rps']:.1f}".rjust(6)
        p95_val = f"{r['latency']['p95']:.0f}".rjust(7)
        p99_val = f"{r['latency']['p99']:.0f}".rjust(7)
        created_val = f"{r['pool_stats']['metrics']['created']}".rjust(7)
        reused_val = f"{r['pool_stats']['metrics']['reused']}".rjust(6)
        idle_val = f"{r['pool_stats']['idle']}".rjust(4)
        
        print(f"║ {pool_name} │ {time_val} │ {rps_val} │ {p95_val} │ {p99_val} │ {created_val} │ {reused_val} │ {idle_val} ║")
    
    print("╚════════════════════════════════════════════════════════════════════════════════╝")
    
    # Análisis comparativo
    print("\n📈 Análisis:")
    
    baseline = results[0]
    for i, r in enumerate(results[1:], 1):
        speedup = baseline['total_time'] / r['total_time']
        print(f"\n   {r['pool_name']} vs {baseline['pool_name']}:")
        print(f"   - Speedup: {speedup:.2f}x más rápido")
        print(f"   - Conexiones reutilizadas: {r['pool_stats']['metrics']['reused']}")
        
        if r['pool_stats']['metrics']['created'] > r['pool_size']:
            print(f"   ⚠️  Se crearon más conexiones ({r['pool_stats']['metrics']['created']}) que el límite del pool ({r['pool_size']})")
            print(f"      Esto indica que hubo cierre y reapertura de conexiones")


async def main():
    """Función principal del benchmark"""
    
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║     Benchmark de Connection Pool - ACT10 AI               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Verificar servidor mock
    print("\n🔍 Verificando servidor mock...")
    if not await check_mock_server():
        print("\n❌ ERROR: Servidor mock no disponible")
        print("\n   Ejecuta en otra terminal:")
        print("   cd 'Semana III/ACT9 AI'")
        print("   python benchmark_mock_server.py")
        return
    
    print("✅ Servidor mock detectado")
    
    # Configurar delay del servidor
    if not await configure_mock_server(SERVER_DELAY_MS):
        return
    
    # Definir configuraciones a probar
    benchmarks = [
        {"pool_size": 5, "name": "Small (5)"},
        {"pool_size": 20, "name": "Medium (20)"},
        {"pool_size": 1000, "name": "Unlimited"},
    ]
    
    # Ejecutar benchmarks
    results = []
    
    for config in benchmarks:
        result = await run_benchmark(
            pool_size=config["pool_size"],
            num_requests=NUM_REQUESTS,
            pool_name=config["name"]
        )
        results.append(result)
        
        # Pausa entre benchmarks para limpiar estado
        await asyncio.sleep(2)
    
    # Imprimir tabla comparativa
    print_comparison_table(results)
    
    # Recomendaciones
    print("\n💡 Recomendaciones:")
    print("\n   1. Pool pequeño (5 conexiones):")
    print("      ✓ Usa menos recursos del sistema")
    print("      ✗ Baja throughput con alta concurrencia")
    print("      → Ideal para: APIs con rate limiting estricto")
    
    print("\n   2. Pool medio (20 conexiones):")
    print("      ✓ Balance entre rendimiento y recursos")
    print("      ✓ Buen throughput para la mayoría de casos")
    print("      → Ideal para: Aplicaciones típicas de producción")
    
    print("\n   3. Pool ilimitado (1000 conexiones):")
    print("      ✓ Máximo throughput posible")
    print("      ✗ Alto overhead de sistema (sockets, memoria)")
    print("      ✗ Crea nueva conexión por cada request (no reutiliza)")
    print("      → Ideal para: Ráfagas cortas de alta concurrencia")
    
    print("\n   🎯 Recomendación para EcoMarket:")
    best = results[1]  # Medium pool
    print(f"      Pool de {best['pool_size']} conexiones")
    print(f"      Throughput: {best['throughput_rps']:.1f} req/s")
    print(f"      Latencia P95: {best['latency']['p95']:.0f}ms")
    print(f"      Conexiones reutilizadas: {best['pool_stats']['metrics']['reused']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrumpido por el usuario")
