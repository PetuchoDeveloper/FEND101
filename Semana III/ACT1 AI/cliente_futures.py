"""
Modelo 2: FUTURES usando concurrent.futures.ThreadPoolExecutor
===============================================================
Este ejemplo demuestra cómo usar Future objects para manejar respuestas HTTP concurrentes.

Escenario: Cargar simultáneamente productos, categorías y perfil de usuario.

Autor: Tutorial de Sistemas Concurrentes
Fecha: 2026-02-11
"""

import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED, ALL_COMPLETED

# Configuración
BASE_URL = "http://localhost:3000/api"
TIMEOUT = 10

# =============================================================================
# 📚 CONCEPTOS CLAVE DEL MODELO DE FUTURES
# =============================================================================
#
# ¿Qué es un Future?
# - Es un "objeto promesa" que representa un resultado futuro
# - Se obtiene INMEDIATAMENTE cuando lanzas la tarea con .submit()
# - Puedes consultar su estado (.done(), .running(), .cancelled())
# - Puedes obtener el resultado con .result() (bloquea hasta que termine)
#
# Ventajas:
# ✅ Más explícito que callbacks - ves claramente qué esperar
# ✅ Fácil esperar a "el primero que termine" o "todos"
# ✅ Manejo de errores más limpio con try/except en .result()
# ✅ Puedes cancelar futures si aún no empezaron
#
# Desventajas:
# ❌ Menos reactivo que callbacks (debes "preguntar" activamente por resultados)
# ❌ .result() bloquea el thread actual
# ❌ Más código boilerplate para iterar sobre futures
#
# =============================================================================


def hacer_peticion_productos():
    """Petición HTTP para obtener productos"""
    print(f"  🔵 [Thread {id(threading.current_thread())}] GET /productos iniciado")
    start = time.time()
    
    response = requests.get(f"{BASE_URL}/productos", timeout=TIMEOUT)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /productos completado en {elapsed:.2f}s")
    
    return {"endpoint": "productos", "data": response.json(), "time": elapsed}


def hacer_peticion_categorias():
    """Petición HTTP para obtener categorías"""
    print(f"  🟢 [Thread] GET /categorias iniciado")
    start = time.time()
    
    response = requests.get(f"{BASE_URL}/categorias", timeout=TIMEOUT)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /categorias completado en {elapsed:.2f}s")
    
    return {"endpoint": "categorias", "data": response.json(), "time": elapsed}


def hacer_peticion_perfil():
    """Petición HTTP para obtener perfil"""
    print(f"  🟡 [Thread] GET /perfil iniciado")
    start = time.time()
    
    response = requests.get(f"{BASE_URL}/perfil", timeout=TIMEOUT)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /perfil completado en {elapsed:.2f}s")
    
    return {"endpoint": "perfil", "data": response.json(), "time": elapsed}


# =============================================================================
# MÉTODO 1: Usando as_completed() - Procesar conforme van terminando
# =============================================================================

def cargar_datos_con_as_completed():
    """
    Lanza 3 peticiones HTTP en paralelo y procesa resultados conforme terminan.
    
    🔑 FLUJO:
    1. .submit() lanza cada tarea y retorna un Future inmediatamente
    2. as_completed() nos da un iterador que retorna Futures en orden de terminación
    3. .result() obtiene el valor (bloquea si aún no terminó, pero ya sabemos que sí)
    4. Procesamos cada resultado apenas esté listo
    """
    print("=" * 70)
    print("🚀 MODELO 2: FUTURES con as_completed()")
    print("=" * 70)
    print("\n📋 Iniciando carga concurrente de datos...\n")
    
    start_total = time.time()
    resultados = {}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        
        # PASO 1: Lanzar las 3 peticiones y guardar los Future objects
        futures = {
            executor.submit(hacer_peticion_productos): "productos",
            executor.submit(hacer_peticion_categorias): "categorias",
            executor.submit(hacer_peticion_perfil): "perfil"
        }
        
        print("🎯 Las 3 peticiones fueron LANZADAS\n")
        print(f"📊 Estado inicial de los Futures:")
        for f, nombre in futures.items():
            print(f"   • {nombre}: done={f.done()}, running={f.running()}")
        
        print(f"\n⏳ Esperando resultados (en orden de terminación)...\n")
        
        # PASO 2: Iterar sobre futures conforme van terminando
        for future in as_completed(futures):
            endpoint_name = futures[future]
            
            try:
                # .result() obtiene el valor retornado
                # Si hubo excepción en el thread, se lanzará aquí
                resultado = future.result()
                
                resultados[endpoint_name] = resultado
                
                print(f"\n📦 Future de '{endpoint_name}' completado:")
                print(f"   ⏱️  Tiempo: {resultado['time']:.2f}s")
                print(f"   📊 Datos: {len(resultado['data'])} items")
                
            except Exception as e:
                print(f"\n❌ Error en '{endpoint_name}': {type(e).__name__}: {e}")
                resultados[endpoint_name] = {"error": str(e)}
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"✅ TODAS LAS PETICIONES COMPLETADAS")
    print(f"⏱️  Tiempo total: {elapsed_total:.2f}s")
    print(f"📊 Resultados exitosos: {sum(1 for r in resultados.values() if 'error' not in r)}/{len(resultados)}")
    print("=" * 70)
    
    return resultados


# =============================================================================
# MÉTODO 2: Usando wait() - Esperar a todos o al primero
# =============================================================================

def cargar_datos_con_wait():
    """
    Lanza 3 peticiones HTTP y espera a que TODAS terminen con wait().
    
    🔑 DIFERENCIAS con as_completed():
    - as_completed(): Procesa conforme van terminando (streaming)
    - wait(): Espera a un conjunto completo y retorna (done, not_done)
    """
    print("\n\n" + "=" * 70)
    print("🚀 MODELO 2: FUTURES con wait()")
    print("=" * 70)
    print("\n📋 Iniciando carga concurrente de datos...\n")
    
    start_total = time.time()
    resultados = {}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        
        # Lanzar las 3 peticiones
        future_productos = executor.submit(hacer_peticion_productos)
        future_categorias = executor.submit(hacer_peticion_categorias)
        future_perfil = executor.submit(hacer_peticion_perfil)
        
        futures = [future_productos, future_categorias, future_perfil]
        nombres = ["productos", "categorias", "perfil"]
        
        print("🎯 Las 3 peticiones fueron LANZADAS\n")
        
        # PASO 2: Esperar a que TODOS terminen
        print("⏳ Esperando a que TODOS los Futures terminen...\n")
        done, not_done = wait(futures, return_when=ALL_COMPLETED)
        
        print(f"✅ wait() retornó: {len(done)} completados, {len(not_done)} pendientes\n")
        
        # PASO 3: Procesar todos los resultados
        for future, nombre in zip(futures, nombres):
            try:
                resultado = future.result()
                resultados[nombre] = resultado
                print(f"📦 '{nombre}': {len(resultado['data'])} items en {resultado['time']:.2f}s")
                
            except Exception as e:
                print(f"❌ '{nombre}': {type(e).__name__}: {e}")
                resultados[nombre] = {"error": str(e)}
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"✅ PROCESO COMPLETADO")
    print(f"⏱️  Tiempo total: {elapsed_total:.2f}s")
    print("=" * 70)
    
    return resultados


# =============================================================================
# ESCENARIO DE ERROR: ¿Cómo manejar el error de UN future sin perder los demás?
# =============================================================================

def hacer_peticion_categorias_con_timeout():
    """Simula timeout en categorías"""
    print(f"  🟢 [Thread] GET /categorias iniciado (forzará timeout)")
    
    # Timeout muy corto para forzar error
    response = requests.get(f"{BASE_URL}/categorias?delay=15", timeout=2)
    response.raise_for_status()
    
    return {"endpoint": "categorias", "data": response.json(), "time": 0}


def demo_manejo_error_individual():
    """
    Demuestra cómo manejar el error de UN future sin perder los demás resultados.
    
    🔑 RESPUESTA: Cada .result() se envuelve en try/except individualmente.
    """
    print("\n\n" + "=" * 70)
    print("🚨 DEMO: MANEJO DE ERROR INDIVIDUAL (timeout en /categorias)")
    print("=" * 70)
    print("\nPregunta: ¿Cómo obtenemos los resultados exitosos sin perder datos?\n")
    
    start_total = time.time()
    resultados_validos = []
    errores = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        
        # Lanzar las 3 peticiones (una fallará)
        futures_dict = {
            executor.submit(hacer_peticion_productos): "productos",
            executor.submit(hacer_peticion_categorias_con_timeout): "categorias",
            executor.submit(hacer_peticion_perfil): "perfil"
        }
        
        print("🎯 Peticiones lanzadas (categorias fallará con timeout)\n")
        
        # Procesar cada future INDIVIDUALMENTE con manejo de errores
        for future in as_completed(futures_dict):
            endpoint = futures_dict[future]
            
            try:
                # Intentar obtener el resultado
                resultado = future.result()
                resultados_validos.append(resultado)
                print(f"✅ '{endpoint}': Éxito - {len(resultado['data'])} items")
                
            except requests.Timeout:
                # Error específico de timeout
                errores.append({"endpoint": endpoint, "error": "Timeout"})
                print(f"⏱️  '{endpoint}': TIMEOUT - Ignorado, continuamos con los demás")
                
            except Exception as e:
                # Cualquier otro error
                errores.append({"endpoint": endpoint, "error": str(e)})
                print(f"❌ '{endpoint}': ERROR - {type(e).__name__}")
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"📊 RESUMEN:")
    print(f"   ✅ Peticiones exitosas: {len(resultados_validos)}")
    print(f"   ❌ Peticiones fallidas: {len(errores)}")
    print(f"   ⏱️  Tiempo total: {elapsed_total:.2f}s")
    print(f"\n💡 CONCLUSIÓN: Obtuvimos {len(resultados_validos)} resultados válidos")
    print(f"   a pesar del error en {len(errores)} petición(es)")
    print("=" * 70)
    
    return resultados_validos, errores


# =============================================================================
# EJECUCIÓN
# =============================================================================

import threading

if __name__ == "__main__":
    # Método 1: as_completed() - Procesar conforme terminan
    cargar_datos_con_as_completed()
    
    # Método 2: wait() - Esperar a todos
    cargar_datos_con_wait()
    
    # Demo de manejo de errores
    # demo_manejo_error_individual()  # Descomentar para ver escenario de error
