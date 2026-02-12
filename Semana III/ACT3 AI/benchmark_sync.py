"""
Benchmark para cliente SÍNCRONO de EcoMarket

Mide el tiempo de ejecución de cargar_dashboard_sync() que ejecuta
3 peticiones GET de forma SECUENCIAL (una tras otra).
"""

import time
import sys
import os

# Importar el cliente síncrono original desde Semana II
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'Semana II', 'ACT9 AI'))

import cliente_ecomarket as client


def cargar_dashboard_sync():
    """
    Versión SÍNCRONA de cargar_dashboard.
    
    Ejecuta 3 peticiones de forma SECUENCIAL:
    1. listar_productos()
    2. obtener_categorias() - simulado como otra petición a productos
    3. obtener_perfil() - simulado como obtener el primer producto
    
    Nota: Como la API mock no tiene endpoints /categorias ni /perfil,
    simulamos con operaciones equivalentes.
    """
    resultados = {
        "productos": None,
        "categorias": None,
        "perfil": None
    }
    errores = []
    
    # Petición 1: Listar productos
    try:
        resultados["productos"] = client.listar_productos()
    except Exception as e:
        errores.append({"endpoint": "productos", "error": str(e)})
    
    # Petición 2: Categorías (simulado como listar productos con filtro)
    try:
        resultados["categorias"] = client.listar_productos(categoria="frutas")
    except Exception as e:
        errores.append({"endpoint": "categorias", "error": str(e)})
    
    # Petición 3: Perfil (simulado como obtener producto con ID 1)
    try:
        resultados["perfil"] = client.obtener_producto(1)
    except Exception as e:
        errores.append({"endpoint": "perfil", "error": str(e)})
    
    return {
        "datos": resultados,
        "errores": errores
    }


def ejecutar_benchmark(iteraciones=5):
    """
    Ejecuta el benchmark múltiples veces y calcula el promedio.
    
    Args:
        iteraciones: Número de veces a repetir el benchmark
    
    Returns:
        dict: Estadísticas de tiempo
    """
    tiempos = []
    
    print(f"🔄 Ejecutando benchmark SÍNCRONO ({iteraciones} iteraciones)...")
    print()
    
    for i in range(iteraciones):
        inicio = time.perf_counter()
        
        try:
            resultado = cargar_dashboard_sync()
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


if __name__ == "__main__":
    print("=" * 60)
    print("BENCHMARK: Cliente SÍNCRONO (requests)")
    print("=" * 60)
    print()
    print("Este benchmark mide el tiempo de cargar 3 endpoints")
    print("de forma SECUENCIAL (uno tras otro).")
    print()
    
    stats = ejecutar_benchmark(iteraciones=5)
    
    if stats:
        print()
        print("📊 RESULTADOS:")
        print(f"  • Promedio: {stats['promedio']:.4f}s")
        print(f"  • Mínimo:   {stats['minimo']:.4f}s")
        print(f"  • Máximo:   {stats['maximo']:.4f}s")
        print()
        
        # Guardar en archivo para comparación
        with open("benchmark_sync_results.txt", "w") as f:
            f.write(f"PROMEDIO={stats['promedio']:.6f}\n")
            f.write(f"MINIMO={stats['minimo']:.6f}\n")
            f.write(f"MAXIMO={stats['maximo']:.6f}\n")
            f.write(f"TIEMPOS={','.join(f'{t:.6f}' for t in stats['tiempos'])}\n")
        
        print("✅ Resultados guardados en benchmark_sync_results.txt")
    else:
        print("❌ No se pudo completar el benchmark")
