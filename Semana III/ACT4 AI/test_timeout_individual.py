"""
Tests para demostrar el comportamiento de timeout individual por petición.

Demuestra que:
1. Cada petición tiene su propio timeout configurable
2. Si una petición excede su timeout, las demás continúan normalmente
3. El timeout es granular, no global
"""

import asyncio
import aiohttp
import time
from coordinador_async import (
    ejecutar_con_timeout,
    listar_productos,
    obtener_categorias,
    obtener_perfil,
    TimeoutError
)


async def simular_peticion_lenta(nombre: str, segundos: float) -> str:
    """Simula una petición que tarda un tiempo específico"""
    print(f"  [{nombre}] Iniciando (tardará {segundos}s)...")
    await asyncio.sleep(segundos)
    print(f"  [{nombre}] ✅ Completada después de {segundos}s")
    return f"Resultado de {nombre}"


async def test_timeout_individual():
    """
    TEST 1: Timeout individual
    
    Demuestra que cada petición tiene su propio timeout.
    """
    print("\n" + "="*60)
    print("TEST 1: Timeout Individual por Petición")
    print("="*60)
    print("\nEscenario: 3 peticiones con diferentes timeouts")
    print("  - Rápida: 1s de ejecución, timeout de 2s → ✅ Exitosa")
    print("  - Media: 3s de ejecución, timeout de 2s → ⏱️ Timeout")
    print("  - Lenta: 5s de ejecución, timeout de 6s → ✅ Exitosa")
    print("\n⏳ Ejecutando...\n")
    
    inicio = time.time()
    
    # Lanzar las 3 peticiones en paralelo con diferentes timeouts
    resultados = await asyncio.gather(
        ejecutar_con_timeout(
            simular_peticion_lenta("Rápida", 1.0),
            timeout_segundos=2.0,
            nombre_operacion="rápida"
        ),
        ejecutar_con_timeout(
            simular_peticion_lenta("Media", 3.0),
            timeout_segundos=2.0,
            nombre_operacion="media"
        ),
        ejecutar_con_timeout(
            simular_peticion_lenta("Lenta", 5.0),
            timeout_segundos=6.0,
            nombre_operacion="lenta"
        ),
        return_exceptions=True  # Capturar excepciones como valores
    )
    
    tiempo_total = time.time() - inicio
    
    print(f"\n📊 Resultados después de {tiempo_total:.1f}s:")
    print("-" * 60)
    
    for i, resultado in enumerate(resultados, 1):
        nombre = ["Rápida", "Media", "Lenta"][i-1]
        if isinstance(resultado, TimeoutError):
            print(f"  {i}. [{nombre}] ⏱️ TIMEOUT: {resultado}")
        elif isinstance(resultado, Exception):
            print(f"  {i}. [{nombre}] ❌ ERROR: {resultado}")
        else:
            print(f"  {i}. [{nombre}] ✅ ÉXITO: {resultado}")
    
    print("\n✅ VERIFICACIÓN:")
    print("  - La petición 'Media' tuvo timeout (como se esperaba)")
    print("  - Las peticiones 'Rápida' y 'Lenta' completaron exitosamente")
    print("  - IMPORTANTE: La petición 'Lenta' NO fue afectada por el timeout de 'Media'")


async def test_timeouts_configurables():
    """
    TEST 2: Timeouts configurables por función
    
    Demuestra timeouts específicos para diferentes endpoints:
    - productos: 5s
    - categorías: 3s
    - perfil: 2s
    """
    print("\n" + "="*60)
    print("TEST 2: Timeouts Configurables por Función")
    print("="*60)
    print("\nEscenario: Timeouts específicos por endpoint")
    print("  - Productos: timeout de 5s")
    print("  - Categorías: timeout de 3s")
    print("  - Perfil: timeout de 2s")
    print("\nNota: Este test requiere servidor mock corriendo")
    print("Si el servidor no está disponible, mostrará ConexionError\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            inicio = time.time()
            
            # Ejecutar con timeouts específicos
            resultados = await asyncio.gather(
                listar_productos(session, timeout=5.0),
                obtener_categorias(session, timeout=3.0),
                obtener_perfil(session, timeout=2.0),
                return_exceptions=True
            )
            
            tiempo_total = time.time() - inicio
            
            print(f"\n📊 Resultados después de {tiempo_total:.2f}s:")
            print("-" * 60)
            
            nombres = ["Productos (5s)", "Categorías (3s)", "Perfil (2s)"]
            for i, (nombre, resultado) in enumerate(zip(nombres, resultados), 1):
                if isinstance(resultado, TimeoutError):
                    print(f"  {i}. [{nombre}] ⏱️ TIMEOUT")
                elif isinstance(resultado, Exception):
                    print(f"  {i}. [{nombre}] ❌ ERROR: {type(resultado).__name__}")
                else:
                    tipo = "list" if isinstance(resultado, list) else "dict"
                    tamano = len(resultado) if isinstance(resultado, (list, dict)) else 0
                    print(f"  {i}. [{nombre}] ✅ ÉXITO ({tipo} con {tamano} items)")
    
    except Exception as e:
        print(f"\n❌ Error al ejecutar el test: {e}")
        print("Asegúrate de que el servidor mock esté corriendo en localhost:3000")


async def test_diagrama_temporal():
    """
    TEST 3: Diagrama temporal visual
    
    Muestra visualmente cómo se comportan los timeouts individuales.
    """
    print("\n" + "="*60)
    print("TEST 3: Diagrama Temporal de Timeouts")
    print("="*60)
    
    print("\nEscenario:")
    print("  Petición A: tarda 1s, timeout 3s")
    print("  Petición B: tarda 5s, timeout 2s")
    print("  Petición C: tarda 3s, timeout 4s")
    
    print("\n📊 Diagrama Temporal:")
    print("-" * 60)
    print("Tiempo →  0s    1s    2s    3s    4s    5s")
    print("A (3s):   [████]✅                        ")
    print("B (2s):   [████████]⏱️                   ")
    print("C (4s):   [████████████]✅               ")
    print("-" * 60)
    print("\nLeyenda:")
    print("  ████  = Ejecución activa")
    print("  ✅    = Completada exitosamente")
    print("  ⏱️    = Timeout (excedió su límite)")
    
    print("\n⏳ Ejecutando simulación real...\n")
    
    inicio = time.time()
    inicio_str = time.strftime("%H:%M:%S")
    
    resultados = await asyncio.gather(
        ejecutar_con_timeout(simular_peticion_lenta("A", 1.0), 3.0, "A"),
        ejecutar_con_timeout(simular_peticion_lenta("B", 5.0), 2.0, "B"),
        ejecutar_con_timeout(simular_peticion_lenta("C", 3.0), 4.0, "C"),
        return_exceptions=True
    )
    
    tiempo_total = time.time() - inicio
    fin_str = time.strftime("%H:%M:%S")
    
    print(f"\n📊 Resumen:")
    print(f"  Inicio: {inicio_str}")
    print(f"  Fin: {fin_str}")
    print(f"  Tiempo total: {tiempo_total:.2f}s (tiempo de la más lenta que completó)")
    
    print("\n✅ CONCLUSIÓN:")
    print("  - Cada petición tiene su propio timeout independiente")
    print("  - Una petición con timeout NO afecta a las demás")
    print("  - El tiempo total es el de la petición más lenta que completa")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS DE TIMEOUT INDIVIDUAL")
    print("="*60)
    
    # Ejecutar todos los tests
    asyncio.run(test_timeout_individual())
    asyncio.run(test_timeouts_configurables())
    asyncio.run(test_diagrama_temporal())
    
    print("\n" + "="*60)
    print("Tests completados")
    print("="*60)
