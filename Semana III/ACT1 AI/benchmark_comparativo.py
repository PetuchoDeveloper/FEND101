"""
Benchmark Comparativo: Callbacks vs Futures vs Async/Await
===========================================================
Mide y compara el rendimiento de los 3 modelos de concurrencia.

Autor: Tutorial de Sistemas Concurrentes
Fecha: 2026-02-11
"""

import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp
import requests

# Configuración
BASE_URL = "http://localhost:3000/api"
TIMEOUT = 10
NUM_ITERATIONS = 5  # Número de veces que se ejecuta cada modelo para promediar

print("=" * 70)
print("📊 BENCHMARK: Comparación de Modelos de Concurrencia")
print("=" * 70)
print(f"\nConfiguración:")
print(f"  • URL Base: {BASE_URL}")
print(f"  • Timeout: {TIMEOUT}s")
print(f"  • Iteraciones por modelo: {NUM_ITERATIONS}")
print(f"  • Endpoints: /productos, /categorias, /perfil")
print("=" * 70)

# =============================================================================
# MODELO 1: CALLBACKS
# =============================================================================

def peticion_sincrona(endpoint):
    """Petición HTTP síncrona genérica"""
    response = requests.get(f"{BASE_URL}/{endpoint}", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def benchmark_callbacks():
    """Mide el tiempo de ejecución con modelo de callbacks"""
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Lanzar las 3 peticiones
        future1 = executor.submit(peticion_sincrona, "productos")
        future2 = executor.submit(peticion_sincrona, "categorias")
        future3 = executor.submit(peticion_sincrona, "perfil")
        
        # Esperar a que terminen
        futures = [future1, future2, future3]
        for future in as_completed(futures):
            _ = future.result()
    
    return time.time() - start


# =============================================================================
# MODELO 2: FUTURES
# =============================================================================

def benchmark_futures():
    """Mide el tiempo de ejecución con modelo de futures"""
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Lanzar las 3 peticiones
        futures = [
            executor.submit(peticion_sincrona, "productos"),
            executor.submit(peticion_sincrona, "categorias"),
            executor.submit(peticion_sincrona, "perfil")
        ]
        
        # Esperar a que terminen
        for future in as_completed(futures):
            _ = future.result()
    
    return time.time() - start


# =============================================================================
# MODELO 3: ASYNC/AWAIT
# =============================================================================

async def peticion_async(session, endpoint):
    """Petición HTTP asíncrona genérica"""
    async with session.get(f"{BASE_URL}/{endpoint}") as response:
        response.raise_for_status()
        return await response.json()


async def benchmark_async_core():
    """Núcleo de la medición async"""
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await asyncio.gather(
            peticion_async(session, "productos"),
            peticion_async(session, "categorias"),
            peticion_async(session, "perfil")
        )


def benchmark_async():
    """Mide el tiempo de ejecución con modelo async/await"""
    start = time.time()
    asyncio.run(benchmark_async_core())
    return time.time() - start


# =============================================================================
# EJECUCIÓN DEL BENCHMARK
# =============================================================================

def ejecutar_benchmark():
    """Ejecuta el benchmark completo para los 3 modelos"""
    
    print("\n🔄 Ejecutando benchmarks...\n")
    
    # Calentar el servidor (primera petición puede ser más lenta)
    print("⏳ Calentando servidor...")
    try:
        requests.get(f"{BASE_URL}/productos", timeout=TIMEOUT)
        print("✅ Servidor listo\n")
    except Exception as e:
        print(f"❌ ERROR: No se puede conectar al servidor mock")
        print(f"   Por favor ejecuta: python servidor_mock.py")
        print(f"   Error: {e}")
        return
    
    resultados = {
        "callbacks": [],
        "futures": [],
        "async": []
    }
    
    # Ejecutar cada modelo NUM_ITERATIONS veces
    for i in range(NUM_ITERATIONS):
        print(f"Iteración {i+1}/{NUM_ITERATIONS}:")
        
        # Modelo 1: Callbacks
        tiempo = benchmark_callbacks()
        resultados["callbacks"].append(tiempo)
        print(f"  • Callbacks: {tiempo:.3f}s")
        
        time.sleep(0.5)  # Breve pausa entre modelos
        
        # Modelo 2: Futures
        tiempo = benchmark_futures()
        resultados["futures"].append(tiempo)
        print(f"  • Futures:   {tiempo:.3f}s")
        
        time.sleep(0.5)
        
        # Modelo 3: Async/Await
        tiempo = benchmark_async()
        resultados["async"].append(tiempo)
        print(f"  • Async:     {tiempo:.3f}s")
        
        print()
    
    return resultados


def calcular_estadisticas(tiempos):
    """Calcula estadísticas de los tiempos"""
    return {
        "min": min(tiempos),
        "max": max(tiempos),
        "promedio": statistics.mean(tiempos),
        "mediana": statistics.median(tiempos),
        "desv_std": statistics.stdev(tiempos) if len(tiempos) > 1 else 0
    }


def mostrar_resultados(resultados):
    """Muestra los resultados del benchmark"""
    print("=" * 70)
    print("📊 RESULTADOS")
    print("=" * 70)
    
    for modelo, tiempos in resultados.items():
        stats = calcular_estadisticas(tiempos)
        
        print(f"\n{modelo.upper()}:")
        print(f"  • Promedio: {stats['promedio']:.3f}s")
        print(f"  • Mediana:  {stats['mediana']:.3f}s")
        print(f"  • Mínimo:   {stats['min']:.3f}s")
        print(f"  • Máximo:   {stats['max']:.3f}s")
        print(f"  • Desv Est: {stats['desv_std']:.3f}s")
    
    # Tabla comparativa
    print("\n" + "=" * 70)
    print("TABLA COMPARATIVA")
    print("=" * 70)
    print(f"\n{'Modelo':<15} {'Promedio':<12} {'Min':<10} {'Max':<10}")
    print("-" * 50)
    
    for modelo, tiempos in resultados.items():
        stats = calcular_estadisticas(tiempos)
        print(f"{modelo.capitalize():<15} {stats['promedio']:.3f}s      {stats['min']:.3f}s    {stats['max']:.3f}s")
    
    # Determinar el ganador
    promedios = {modelo: statistics.mean(tiempos) for modelo, tiempos in resultados.items()}
    ganador = min(promedios, key=promedios.get)
    
    print("\n" + "=" * 70)
    print(f"🏆 GANADOR: {ganador.upper()}")
    print(f"   Tiempo promedio: {promedios[ganador]:.3f}s")
    print("=" * 70)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    resultados = ejecutar_benchmark()
    
    if resultados:
        mostrar_resultados(resultados)
        
        # Guardar resultados en archivo para el análisis
        print("\n💾 Guardando resultados para el análisis...")
        
        with open("resultados_benchmark.txt", "w", encoding="utf-8") as f:
            f.write("RESULTADOS DEL BENCHMARK\n")
            f.write("=" * 50 + "\n\n")
            
            for modelo, tiempos in resultados.items():
                stats = calcular_estadisticas(tiempos)
                f.write(f"{modelo.upper()}:\n")
                f.write(f"  Promedio: {stats['promedio']:.3f}s\n")
                f.write(f"  Mediana:  {stats['mediana']:.3f}s\n")
                f.write(f"  Mínimo:   {stats['min']:.3f}s\n")
                f.write(f"  Máximo:   {stats['max']:.3f}s\n")
                f.write(f"  Desv Est: {stats['desv_std']:.3f}s\n\n")
        
        print("✅ Resultados guardados en: resultados_benchmark.txt")
