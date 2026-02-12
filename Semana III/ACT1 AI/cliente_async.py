"""
Modelo 3: ASYNC/AWAIT usando asyncio + aiohttp
===============================================
Este ejemplo demuestra cómo usar async/await para manejar respuestas HTTP concurrentes.

Escenario: Cargar simultáneamente productos, categorías y perfil de usuario.

Autor: Tutorial de Sistemas Concurrentes
Fecha: 2026-02-11
"""

import asyncio
import aiohttp
import time

# Configuración
BASE_URL = "http://localhost:3000/api"
TIMEOUT = 10

# =============================================================================
# 📚 CONCEPTOS CLAVE DEL MODELO ASYNC/AWAIT
# =============================================================================
#
# ¿Qué es async/await?
# - Sintaxis moderna para programación asíncrona (desde Python 3.5+)
# - `async def` define una coroutine (función asíncrona)
# - `await` pausa la ejecución HASTA que la tarea async termine
# - El event loop (asyncio) gestiona la concurrencia automáticamente
#
# Ventajas:
# ✅ Código más limpio y legible (parece síncrono pero es async)
# ✅ Sin threads - más eficiente en I/O intensivo
# ✅ gather() facilita lanzar múltiples tareas en paralelo
# ✅ return_exceptions=True maneja errores sin detener otras tareas
#
# Desventajas:
# ❌ Requiere librerías async (aiohttp en vez de requests)
# ❌ "Contagio async" - toda la cadena debe ser async
# ❌ No apto para tareas CPU-intensivas (solo I/O)
# ❌ Debugging más complejo que código síncrono
#
# =============================================================================


# =============================================================================
# FUNCIONES ASYNC: Peticiones HTTP asíncronas
# =============================================================================

async def hacer_peticion_productos(session):
    """
    Petición asíncrona para obtener productos.
    
    Args:
        session: aiohttp.ClientSession reutilizable
        
    Returns:
        dict con endpoint, data y time
        
    ⚠️ IMPORTANTE: Esta función es una COROUTINE (async def)
    No retorna inmediatamente - debe ser "awaited"
    """
    print(f"  🔵 [Coroutine] Iniciando async GET /productos...")
    start = time.time()
    
    # await pausa ESTA coroutine hasta que la petición HTTP termine
    # Mientras espera, el event loop puede ejecutar OTRAS coroutines
    async with session.get(f"{BASE_URL}/productos") as response:
        response.raise_for_status()
        data = await response.json()
        
        elapsed = time.time() - start
        print(f"  ✅ [Coroutine] /productos completado en {elapsed:.2f}s")
        
        return {"endpoint": "productos", "data": data, "time": elapsed}


async def hacer_peticion_categorias(session):
    """Petición asíncrona para obtener categorías"""
    print(f"  🟢 [Coroutine] Iniciando async GET /categorias...")
    start = time.time()
    
    async with session.get(f"{BASE_URL}/categorias") as response:
        response.raise_for_status()
        data = await response.json()
        
        elapsed = time.time() - start
        print(f"  ✅ [Coroutine] /categorias completado en {elapsed:.2f}s")
        
        return {"endpoint": "categorias", "data": data, "time": elapsed}


async def hacer_peticion_perfil(session):
    """Petición asíncrona para obtener perfil"""
    print(f"  🟡 [Coroutine] Iniciando async GET /perfil...")
    start = time.time()
    
    async with session.get(f"{BASE_URL}/perfil") as response:
        response.raise_for_status()
        data = await response.json()
        
        elapsed = time.time() - start
        print(f"  ✅ [Coroutine] /perfil completado en {elapsed:.2f}s")
        
        return {"endpoint": "perfil", "data": data, "time": elapsed}


# =============================================================================
# MÉTODO 1: Usando asyncio.gather() - Lanzar todo en paralelo
# =============================================================================

async def cargar_datos_con_gather():
    """
    Lanza 3 peticiones HTTP en paralelo usando asyncio.gather().
    
    🔑 FLUJO:
    1. Creamos una ClientSession compartida (para reutilizar conexiones)
    2. gather() lanza las 3 coroutines EN PARALELO
    3. gather() espera a que TODAS terminen
    4. Retorna una lista con los resultados en el mismo orden
    
    ⚠️ Por defecto, si UNA falla, gather() lanza la excepción
    ✅ Con return_exceptions=True, retorna excepciones como valores
    """
    print("=" * 70)
    print("🚀 MODELO 3: ASYNC/AWAIT con gather()")
    print("=" * 70)
    print("\n📋 Iniciando carga concurrente de datos...\n")
    
    start_total = time.time()
    
    # Crear una sesión HTTP asíncrona (reutiliza conexiones)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # PASO 1: Lanzar las 3 coroutines EN PARALELO con gather()
        # ⚠️ gather() NO BLOQUEA - retorna inmediatamente un awaitable
        print("🎯 Lanzando las 3 peticiones con gather()...\n")
        
        # Las 3 coroutines se ejecutarán CONCURRENTEMENTE
        resultados = await asyncio.gather(
            hacer_peticion_productos(session),
            hacer_peticion_categorias(session),
            hacer_peticion_perfil(session),
            return_exceptions=False  # Si hay error, se lanzará excepción
        )
        
        # PASO 2: Procesar resultados (ya están todos listos)
        print("\n📦 Resultados de gather():")
        for resultado in resultados:
            endpoint = resultado['endpoint']
            tiempo = resultado['time']
            items = len(resultado['data'])
            print(f"   • {endpoint}: {items} items en {tiempo:.2f}s")
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"✅ TODAS LAS PETICIONES COMPLETADAS")
    print(f"⏱️  Tiempo total: {elapsed_total:.2f}s")
    print("=" * 70)
    
    return resultados


# =============================================================================
# MÉTODO 2: gather() con return_exceptions=True - Manejo de errores robusto
# =============================================================================

async def hacer_peticion_categorias_con_timeout(session):
    """Simula timeout en categorías"""
    print(f"  🟢 [Coroutine] GET /categorias (forzará timeout)...")
    
    # Crear un timeout muy corto para THIS request específicamente
    timeout = aiohttp.ClientTimeout(total=2)
    async with session.get(f"{BASE_URL}/categorias?delay=15", timeout=timeout) as response:
        response.raise_for_status()
        data = await response.json()
        
        return {"endpoint": "categorias", "data": data, "time": 0}


async def cargar_datos_con_manejo_errores():
    """
    Lanza 3 peticiones y maneja errores individuales con return_exceptions=True.
    
    🔑 DIFERENCIA CLAVE:
    - return_exceptions=False (default): Si UNA falla, se lanza excepción
    - return_exceptions=True: Excepciones se retornan como valores en la lista
    
    ✅ Esto permite obtener resultados exitosos AUNQUE otras fallen
    """
    print("\n\n" + "=" * 70)
    print("🚀 MODELO 3: ASYNC/AWAIT con return_exceptions=True")
    print("=" * 70)
    print("\n🚨 Escenario: /categorias fallará con timeout\n")
    
    start_total = time.time()
    
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        print("🎯 Lanzando peticiones (categorias fallará)...\n")
        
        # gather() con return_exceptions=True
        # ✅ Las excepciones se retornan como items en la lista de resultados
        resultados = await asyncio.gather(
            hacer_peticion_productos(session),
            hacer_peticion_categorias_con_timeout(session),
            hacer_peticion_perfil(session),
            return_exceptions=True  # 🔑 CLAVE: Errores como valores, no excepciones
        )
        
        # PASO 2: Filtrar resultados exitosos vs errores
        print("\n📊 Procesando resultados:\n")
        
        exitosos = []
        errores = []
        
        for i, resultado in enumerate(resultados):
            # Verificar si es una excepción
            if isinstance(resultado, Exception):
                tipo_error = type(resultado).__name__
                print(f"   ❌ Petición {i+1}: ERROR - {tipo_error}: {resultado}")
                errores.append({"index": i, "error": str(resultado)})
            else:
                endpoint = resultado['endpoint']
                items = len(resultado['data'])
                print(f"   ✅ {endpoint}: {items} items")
                exitosos.append(resultado)
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"📊 RESUMEN:")
    print(f"   ✅ Peticiones exitosas: {len(exitosos)}")
    print(f"   ❌ Peticiones fallidas: {len(errores)}")
    print(f"   ⏱️  Tiempo total: {elapsed_total:.2f}s")
    print(f"\n💡 CONCLUSIÓN: Obtuvimos {len(exitosos)} resultados válidos")
    print(f"   a pesar del timeout en /categorias")
    print("=" * 70)
    
    return exitosos, errores


# =============================================================================
# MÉTODO 3: Manejo manual con try/except dentro de cada coroutine
# =============================================================================

async def hacer_peticion_segura(session, url, nombre):
    """
    Wrapper que maneja errores DENTRO de la coroutine.
    
    Ventaja: gather() siempre retorna resultados (nunca excepciones)
    """
    try:
        print(f"  🔷 [Coroutine] {nombre} iniciado...")
        start = time.time()
        
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            elapsed = time.time() - start
            
            print(f"  ✅ [Coroutine] {nombre} completado en {elapsed:.2f}s")
            
            return {
                "endpoint": nombre,
                "data": data,
                "time": elapsed,
                "success": True
            }
            
    except asyncio.TimeoutError:
        print(f"  ⏱️  [Coroutine] {nombre} - TIMEOUT")
        return {
            "endpoint": nombre,
            "error": "Timeout",
            "success": False
        }
        
    except aiohttp.ClientError as e:
        print(f"  ❌ [Coroutine] {nombre} - ERROR: {e}")
        return {
            "endpoint": nombre,
            "error": str(e),
            "success": False
        }


async def cargar_datos_con_wrappers():
    """
    Usa wrappers que manejan errores internamente.
    
    ✅ Ventaja: gather() NUNCA lanzará excepciones
    ✅ Código más limpio para manejar múltiples peticiones
    """
    print("\n\n" + "=" * 70)
    print("🚀 MODELO 3: ASYNC/AWAIT con wrappers seguros")
    print("=" * 70)
    print("\n📋 Iniciando carga con manejo de errores interno...\n")
    
    start_total = time.time()
    
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        resultados = await asyncio.gather(
            hacer_peticion_segura(session, f"{BASE_URL}/productos", "productos"),
            hacer_peticion_segura(session, f"{BASE_URL}/categorias", "categorias"),
            hacer_peticion_segura(session, f"{BASE_URL}/perfil", "perfil")
        )
        
        print("\n📊 Resultados:\n")
        exitosos = [r for r in resultados if r.get('success')]
        fallidos = [r for r in resultados if not r.get('success')]
        
        for r in resultados:
            if r.get('success'):
                print(f"   ✅ {r['endpoint']}: {len(r['data'])} items")
            else:
                print(f"   ❌ {r['endpoint']}: {r.get('error')}")
    
    elapsed_total = time.time() - start_total
    
    print("\n" + "=" * 70)
    print(f"✅ Proceso completado: {len(exitosos)}/{len(resultados)} exitosas")
    print(f"⏱️  Tiempo total: {elapsed_total:.2f}s")
    print("=" * 70)
    
    return exitosos, fallidos


# =============================================================================
# EJECUCIÓN
# =============================================================================

def main():
    """
    Función principal para ejecutar los ejemplos async.
    
    ⚠️ asyncio.run() crea el event loop automáticamente
    """
    # Ejemplo 1: gather() básico
    asyncio.run(cargar_datos_con_gather())
    
    # Ejemplo 2: gather() con return_exceptions=True
    # asyncio.run(cargar_datos_con_manejo_errores())  # Descomentar para ver
    
    # Ejemplo 3: Wrappers con manejo interno
    # asyncio.run(cargar_datos_con_wrappers())  # Descomentar para ver


if __name__ == "__main__":
    main()
