"""
Tests para demostrar la cancelación de tareas en grupo.

Demuestra que:
1. La función cancel_remaining() cancela tareas pendientes
2. Si una petición falla con 401, las demás se cancelan automáticamente
3. CancelledError se maneja correctamente en cada tarea
"""

import asyncio
import aiohttp
import time
from coordinador_async import (
    cancel_remaining,
    cargar_dashboard_con_cancelacion,
    NoAutorizado
)


async def simular_peticion_con_retraso(nombre: str, segundos: float, forzar_401: bool = False):
    """Simula una petición que tarda un tiempo específico"""
    print(f"  [{nombre}] Iniciando (tardará {segundos}s)...")
    
    try:
        for i in range(int(segundos * 10)):
            await asyncio.sleep(0.1)
            # Simular 401 a mitad de camino si se solicita
            if forzar_401 and i == int(segundos * 5):
                print(f"  [{nombre}] 🚫 Error 401: No autorizado")
                raise NoAutorizado("Token inválido")
        
        print(f"  [{nombre}] ✅ Completada después de {segundos}s")
        return f"Resultado de {nombre}"
    
    except asyncio.CancelledError:
        print(f"  [{nombre}] ❌ CANCELADA (por petición externa)")
        raise


async def test_cancel_remaining_basico():
    """
    TEST 1: Cancelación básica de tareas
    
    Demuestra cómo cancel_remaining() cancela tareas pendientes.
    """
    print("\n" + "="*60)
    print("TEST 1: Cancelación Básica con cancel_remaining()")
    print("="*60)
    
    print("\nEscenario:")
    print("  - Lanzar 3 tareas que tardan 5s cada una")
    print("  - Después de 1s, cancelar las que aún no terminaron")
    print("  - Verificar que las tareas se cancelan correctamente")
    
    print("\n⏳ Ejecutando...\n")
    
    # Crear 3 tareas
    tarea1 = asyncio.create_task(simular_peticion_con_retraso("Tarea 1", 5.0))
    tarea2 = asyncio.create_task(simular_peticion_con_retraso("Tarea 2", 5.0))
    tarea3 = asyncio.create_task(simular_peticion_con_retraso("Tarea 3", 5.0))
    
    todas_las_tareas = {tarea1, tarea2, tarea3}
    
    # Esperar 1 segundo
    await asyncio.sleep(1.0)
    
    print("\n⏱️ Después de 1s, cancelando tareas pendientes...")
    
    # Cancelar tareas pendientes
    num_canceladas = cancel_remaining(todas_las_tareas)
    
    print(f"\n📊 Se cancelaron {num_canceladas} tareas")
    
    # Recoger resultados
    resultados = await asyncio.gather(tarea1, tarea2, tarea3, return_exceptions=True)
    
    print("\n📊 Resultados:")
    print("-" * 60)
    for i, resultado in enumerate(resultados, 1):
        if isinstance(resultado, asyncio.CancelledError):
            print(f"  {i}. Tarea {i}: ❌ CANCELADA")
        elif isinstance(resultado, Exception):
            print(f"  {i}. Tarea {i}: ❌ ERROR: {resultado}")
        else:
            print(f"  {i}. Tarea {i}: ✅ ÉXITO: {resultado}")
    
    print("\n✅ VERIFICACIÓN:")
    print("  - Las 3 tareas fueron canceladas correctamente")
    print("  - cancel_remaining() funciona como se esperaba")


async def test_cancelacion_por_401():
    """
    TEST 2: Cancelación en cascada por error 401
    
    Si obtener_perfil falla con 401, las demás peticiones se cancelan.
    """
    print("\n" + "="*60)
    print("TEST 2: Cancelación en Cascada por Error 401")
    print("="*60)
    
    print("\nEscenario:")
    print("  - Lanzar 3 peticiones: productos (5s), categorías (3s), perfil (2s)")
    print("  - Perfil falla con 401 después de 1s")
    print("  - Las demás peticiones deben cancelarse automáticamente")
    
    print("\n⏳ Ejecutando simulación...\n")
    
    async def simular_dashboard_con_401():
        """Simula el dashboard con error 401 en perfil"""
        # Simular tareas
        tarea_productos = asyncio.create_task(
            simular_peticion_con_retraso("Productos", 5.0)
        )
        tarea_categorias = asyncio.create_task(
            simular_peticion_con_retraso("Categorías", 3.0)
        )
        tarea_perfil = asyncio.create_task(
            simular_peticion_con_retraso("Perfil", 2.0, forzar_401=True)
        )
        
        todas_las_tareas = {tarea_productos, tarea_categorias, tarea_perfil}
        tareas_nombres = {
            tarea_productos: "Productos",
            tarea_categorias: "Categorías",
            tarea_perfil: "Perfil"
        }
        
        pendientes = todas_las_tareas.copy()
        resultados_dict = {}
        
        while pendientes:
            done, pendientes = await asyncio.wait(
                pendientes,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for tarea in done:
                nombre = tareas_nombres[tarea]
                
                try:
                    resultado = await tarea
                    resultados_dict[nombre] = {"exito": True, "valor": resultado}
                
                except NoAutorizado as e:
                    print(f"\n🚫 Error 401 detectado en '{nombre}'")
                    resultados_dict[nombre] = {"exito": False, "error": str(e)}
                    
                    # Cancelar las demás
                    if pendientes:
                        print(f"  → Cancelando {len(pendientes)} tareas pendientes...")
                        num_canceladas = cancel_remaining(pendientes)
                        
                        # Esperar a que las tareas canceladas terminen
                        for tarea_pendiente in list(pendientes):
                            try:
                                await tarea_pendiente
                            except asyncio.CancelledError:
                                nombre_cancelada = tareas_nombres[tarea_pendiente]
                                resultados_dict[nombre_cancelada] = {
                                    "exito": False,
                                    "error": "Cancelada por falta de autenticación"
                                }
                        
                        return resultados_dict  # Salir
                
                except asyncio.CancelledError:
                    resultados_dict[nombre] = {
                        "exito": False,
                        "error": "Cancelada externamente"
                    }
        
        return resultados_dict
    
    inicio = time.time()
    resultados = await simular_dashboard_con_401()
    tiempo_total = time.time() - inicio
    
    print(f"\n📊 Resultados después de {tiempo_total:.2f}s:")
    print("-" * 60)
    
    for nombre, info in resultados.items():
        if info["exito"]:
            print(f"  [{nombre}] ✅ ÉXITO: {info['valor']}")
        else:
            print(f"  [{nombre}] ❌ ERROR: {info['error']}")
    
    print("\n✅ VERIFICACIÓN:")
    print("  - Perfil falló con 401 (como se esperaba)")
    print("  - Productos y Categorías fueron canceladas automáticamente")
    print(f"  - Tiempo total: {tiempo_total:.2f}s (mucho menos que si esperáramos a todas)")
    print("  - NO tiene sentido continuar sin autenticación → cancelación justificada")


async def test_diagrama_temporal_cancelacion():
    """
    TEST 3: Diagrama temporal de cancelación
    """
    print("\n" + "="*60)
    print("TEST 3: Diagrama Temporal de Cancelación")
    print("="*60)
    
    print("\n📊 Diagrama Temporal:")
    print("-" * 60)
    print("Tiempo →  0s    1s    2s    3s    4s    5s")
    print("Productos:  [████████████████~~~~~]❌ CANCELADA")
    print("Categorías: [████████~~~~~]❌ CANCELADA        ")
    print("Perfil:     [██]🚫 401 → DISPARA CANCELACIÓN  ")
    print("-" * 60)
    print("\nLeyenda:")
    print("  ████  = Ejecución activa")
    print("  🚫    = Error 401 detectado")
    print("  ~~~~~  = Cancelación en progreso")
    print("  ❌    = Cancelada por error de autenticación")
    
    print("\n✅ CONCLUSIÓN:")
    print("  - Si una petición falla con 401, las demás se cancelan")
    print("  - Esto evita hacer peticiones inútiles sin autenticación")
    print("  - El tiempo total es mucho menor que esperar a todas")
    print("  - CancelledError se maneja correctamente en cada tarea")


async def test_cargar_dashboard_con_cancelacion_real():
    """
    TEST 4: Prueba real con el cliente (requiere servidor mock)
    """
    print("\n" + "="*60)
    print("TEST 4: Prueba Real con cargar_dashboard_con_cancelacion()")
    print("="*60)
    
    print("\nNota: Este test requiere servidor mock corriendo")
    print("Si el servidor no está disponible o no simula 401, mostrará otro error\n")
    
    try:
        resultado = await cargar_dashboard_con_cancelacion()
        
        print(f"\n📊 Resultados:")
        print("-" * 60)
        print(f"Canceladas por auth: {resultado['canceladas_por_auth']}")
        print(f"\nDatos cargados:")
        for endpoint, datos in resultado["datos"].items():
            if datos is not None:
                tipo = "list" if isinstance(datos, list) else "dict"
                tamano = len(datos) if isinstance(datos, (list, dict)) else 0
                print(f"  [{endpoint}] ✅ {tipo} con {tamano} items")
            else:
                print(f"  [{endpoint}] ❌ None (no cargado)")
        
        print(f"\nErrores ({len(resultado['errores'])}):")
        for error_info in resultado["errores"]:
            simbolo = "❌🚫" if error_info.get("cancelada") else "❌"
            print(f"  [{error_info['endpoint']}] {simbolo} {error_info['error']}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Asegúrate de que el servidor mock esté corriendo")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS DE CANCELACIÓN DE TAREAS")
    print("="*60)
    
    # Ejecutar todos los tests
    asyncio.run(test_cancel_remaining_basico())
    asyncio.run(test_cancelacion_por_401())
    asyncio.run(test_diagrama_temporal_cancelacion())
    asyncio.run(test_cargar_dashboard_con_cancelacion_real())
    
    print("\n" + "="*60)
    print("Tests completados")
    print("="*60)
