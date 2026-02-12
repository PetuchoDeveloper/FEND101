"""
Benchmark para cliente ASÍNCRONO de EcoMarket

Mide el tiempo de ejecución de cargar_dashboard() que ejecuta
3 peticiones GET de forma PARALELA (simultáneas).
"""

import asyncio
import time
import cliente_ecomarket_async as client


async def ejecutar_benchmark(iteraciones=5):
    """
    Ejecuta el benchmark múltiples veces y calcula el promedio.
    
    Args:
        iteraciones: Número de veces a repetir el benchmark
    
    Returns:
        dict: Estadísticas de tiempo
    """
    tiempos = []
    
    print(f"🔄 Ejecutando benchmark ASÍNCRONO ({iteraciones} iteraciones)...")
    print()
    
    for i in range(iteraciones):
        inicio = time.perf_counter()
        
        try:
            resultado = await client.cargar_dashboard()
            fin = time.perf_counter()
            tiempo = fin - inicio
            tiempos.append(tiempo)
            
            num_errores = len(resultado["errores"])
            print(f"  Iteración {i+1}: {tiempo:.4f}s (errores: {num_errores})")
        
        except Exception as e:
            print(f"  Iteración {i+1}: ERROR - {e}")
    
    if not tiempos:
        return None
    
    promedio = sum(tiempos) / len(tiempos)
    minimo = min(tiempos)
    maximo = max(tiempos)
    
    return {
        "promedio": promedio,
        "minimo": minimo,
        "maximo": maximo,
        "tiempos": tiempos
    }


async def main():
    print("=" * 60)
    print("BENCHMARK: Cliente ASÍNCRONO (aiohttp)")
    print("=" * 60)
    print()
    print("Este benchmark mide el tiempo de cargar 3 endpoints")
    print("de forma PARALELA (simultáneos).")
    print()
    
    stats = await ejecutar_benchmark(iteraciones=5)
    
    if stats:
        print()
        print("📊 RESULTADOS:")
        print(f"  • Promedio: {stats['promedio']:.4f}s")
        print(f"  • Mínimo:   {stats['minimo']:.4f}s")
        print(f"  • Máximo:   {stats['maximo']:.4f}s")
        print()
        
        # Guardar en archivo para comparación
        with open("benchmark_async_results.txt", "w") as f:
            f.write(f"PROMEDIO={stats['promedio']:.6f}\n")
            f.write(f"MINIMO={stats['minimo']:.6f}\n")
            f.write(f"MAXIMO={stats['maximo']:.6f}\n")
            f.write(f"TIEMPOS={','.join(f'{t:.6f}' for t in stats['tiempos'])}\n")
        
        print("✅ Resultados guardados en benchmark_async_results.txt")
    else:
        print("❌ No se pudo completar el benchmark")


if __name__ == "__main__":
    asyncio.run(main())
