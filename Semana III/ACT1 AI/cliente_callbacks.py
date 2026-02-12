"""
Modelo 1: CALLBACKS usando concurrent.futures
===============================================
Este ejemplo demuestra cómo usar callbacks para manejar respuestas HTTP concurrentes.

Escenario: Cargar simultáneamente productos, categorías y perfil de usuario.

Autor: Tutorial de Sistemas Concurrentes
Fecha: 2026-02-11
"""

import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración
BASE_URL = "http://localhost:3000/api"
TIMEOUT = 10

# =============================================================================
# 📚 CONCEPTOS CLAVE DEL MODELO DE CALLBACKS
# =============================================================================
# 
# ¿Qué es un callback?
# - Es una función que se ejecuta CUANDO una tarea asíncrona termina
# - En lugar de "esperar bloqueando", registras "qué hacer cuando termine"
#
# Ventajas:
# ✅ Control fino sobre cada resultado individual
# ✅ Puedes procesar resultados apenas estén listos (no esperar a todos)
# ✅ Manejo de errores por callback (cada uno independiente)
#
# Desventajas:
# ❌ "Callback Hell" si anidas muchos callbacks
# ❌ Código más verboso que otros modelos
# ❌ Difícil rastrear el flujo de ejecución
#
# =============================================================================


def hacer_peticion_productos():
    """
    Petición síncrona (blocking) para obtener productos.
    Esta función se ejecutará en un thread separado del pool.
    """
    print(f"  🔵 [Thread] Iniciando petición GET /productos...")
    start = time.time()
    
    response = requests.get(f"{BASE_URL}/productos", timeout=TIMEOUT)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /productos completado en {elapsed:.2f}s")
    
    return {"endpoint": "productos", "data": response.json(), "time": elapsed}


def hacer_peticion_categorias():
    """
    Petición síncrona (blocking) para obtener categorías.
    Esta función se ejecutará en un thread separado del pool.
    """
    print(f"  🟢 [Thread] Iniciando petición GET /categorias...")
    start = time.time()
    
    response = requests.get(f"{BASE_URL}/categorias", timeout=TIMEOUT)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /categorias completado en {elapsed:.2f}s")
    
    return {"endpoint": "categorias", "data": response.json(), "time": elapsed}


def hacer_peticion_perfil():
    """
    Petición síncrona (blocking) para obtener perfil del usuario.
    Esta función se ejecutará en un thread separado del pool.
    """
    print(f"  🟡 [Thread] Iniciando petición GET /perfil...")
    start = time.time()
    
    response = requests.get(f"{BASE_URL}/perfil", timeout=TIMEOUT)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /perfil completado en {elapsed:.2f}s")
    
    return {"endpoint": "perfil", "data": response.json(), "time": elapsed}


# =============================================================================
# CALLBACKS: Funciones que se ejecutan cuando una tarea termina
# =============================================================================

def callback_exito(future):
    """
    Este callback se ejecuta cuando un Future completa CON ÉXITO.
    
    Args:
        future: Objeto Future que contiene el resultado
    """
    try:
        # .result() obtiene el valor retornado por la función
        # Si hubo una excepción, .result() la lanzará aquí
        resultado = future.result()
        
        endpoint = resultado['endpoint']
        tiempo = resultado['time']
        data = resultado['data']
        
        print(f"\n📦 CALLBACK ÉXITO para '{endpoint}':")
        print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
        print(f"   📊 Datos recibidos: {len(data)} items")
        
    except Exception as e:
        # Si hubo error, lo manejamos aquí
        print(f"\n❌ CALLBACK ERROR: {type(e).__name__}: {e}")


# =============================================================================
# FUNCIÓN PRINCIPAL: Lanzar peticiones con callbacks
# =============================================================================

def cargar_datos_con_callbacks():
    """
    Lanza 3 peticiones HTTP en paralelo y procesa cada una con un callback.
    
    🔑 FLUJO:
    1. Creamos un ThreadPoolExecutor con 3 workers
    2. .submit() lanza cada tarea y retorna un Future inmediatamente
    3. .add_done_callback() registra qué función ejecutar cuando termine
    4. El programa principal NO SE BLOQUEA esperando
    5. Cuando cada Future termina, su callback se ejecuta automáticamente
    """
    print("=" * 70)
    print("🚀 MODELO 1: CALLBACKS")
    print("=" * 70)
    print("\n📋 Iniciando carga concurrente de datos...\n")
    
    start_total = time.time()
    
    # Crear un pool de 3 threads
    with ThreadPoolExecutor(max_workers=3) as executor:
        
        # PASO 1: Lanzar las 3 peticiones (retorna Future objects)
        # ⚠️ Estas llamadas NO BLOQUEAN - retornan inmediatamente
        future_productos = executor.submit(hacer_peticion_productos)
        future_categorias = executor.submit(hacer_peticion_categorias) 
        future_perfil = executor.submit(hacer_peticion_perfil)
        
        print("🎯 Las 3 peticiones fueron LANZADAS (no esperando resultados)\n")
        
        # PASO 2: Registrar callbacks para cada Future
        # Cuando cada Future termine, ejecutará callback_exito automáticamente
        future_productos.add_done_callback(callback_exito)
        future_categorias.add_done_callback(callback_exito)
        future_perfil.add_done_callback(callback_exito)
        
        print("🔔 Callbacks registrados. Esperando a que terminen...\n")
        
        # PASO 3: Esperar a que TODOS los futures terminen
        # (Si no hacemos esto, el programa terminaría antes que los callbacks)
        # El context manager 'with' espera automáticamente, pero lo hacemos explícito:
        futures = [future_productos, future_categorias, future_perfil]
        
        # Esperar a que todos completen (bloqueante, pero SOLO aquí)
        for future in as_completed(futures):
            # as_completed() retorna futures conforme VAN TERMINANDO
            # Los callbacks ya se ejecutaron, aquí solo esperamos
            pass
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"✅ TODAS LAS PETICIONES COMPLETADAS")
    print(f"⏱️  Tiempo total: {elapsed_total:.2f}s")
    print("=" * 70)


# =============================================================================
# ESCENARIO DE ERROR: ¿Qué pasa si /categorias falla con timeout?
# =============================================================================

def hacer_peticion_categorias_con_timeout():
    """
    Simula un timeout en la petición de categorías.
    """
    print(f"  🟢 [Thread] Iniciando petición GET /categorias (con timeout)...")
    start = time.time()
    
    # Timeout muy corto para forzar el error
    response = requests.get(f"{BASE_URL}/categorias?delay=15", timeout=2)
    elapsed = time.time() - start
    
    response.raise_for_status()
    print(f"  ✅ [Thread] /categorias completado en {elapsed:.2f}s")
    
    return {"endpoint": "categorias", "data": response.json(), "time": elapsed}


def callback_con_manejo_error(future):
    """
    Callback que maneja TANTO éxito como error para cada Future.
    
    ⚠️ IMPORTANTE: Si una petición falla, las demás NO se ven afectadas.
    Cada callback maneja su propio error independientemente.
    """
    try:
        resultado = future.result()
        endpoint = resultado['endpoint']
        print(f"\n✅ CALLBACK: '{endpoint}' completado exitosamente")
        
    except requests.Timeout as e:
        print(f"\n⏱️ CALLBACK TIMEOUT: La petición tardó demasiado")
        print(f"   ℹ️  Las demás peticiones siguen ejecutándose normalmente")
        
    except requests.HTTPError as e:
        print(f"\n❌ CALLBACK HTTP ERROR: {e}")
        print(f"   ℹ️  Las demás peticiones siguen ejecutándose normalmente")
        
    except Exception as e:
        print(f"\n💥 CALLBACK ERROR INESPERADO: {type(e).__name__}: {e}")


def demo_error_timeout():
    """
    Demuestra qué pasa cuando UNA petición falla (timeout en /categorias).
    
    🔑 RESPUESTA: Las demás peticiones NO se enteran y completan normalmente.
    """
    print("\n\n" + "=" * 70)
    print("🚨 DEMO: ERROR DE TIMEOUT EN /categorias")
    print("=" * 70)
    print("Pregunta: ¿Se enteran las demás peticiones del error?\n")
    
    start_total = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_productos = executor.submit(hacer_peticion_productos)
        future_categorias = executor.submit(hacer_peticion_categorias_con_timeout)
        future_perfil = executor.submit(hacer_peticion_perfil)
        
        # Registrar callbacks que manejan errores
        future_productos.add_done_callback(callback_con_manejo_error)
        future_categorias.add_done_callback(callback_con_manejo_error)
        future_perfil.add_done_callback(callback_con_manejo_error)
        
        # Esperar a todos
        futures = [future_productos, future_categorias, future_perfil]
        for future in as_completed(futures):
            pass
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"✅ Todas las tareas terminaron (con o sin error)")
    print(f"⏱️  Tiempo total: {elapsed_total:.2f}s")
    print(f"\n💡 CONCLUSIÓN: El error en /categorias NO afectó a /productos ni /perfil")
    print("=" * 70)


# =============================================================================
# EJECUCIÓN
# =============================================================================

if __name__ == "__main__":
    # Demo normal (sin errores)
    cargar_datos_con_callbacks()
    
    # Demo con timeout
    # demo_error_timeout()  # Descomentar para ver el escenario de error
