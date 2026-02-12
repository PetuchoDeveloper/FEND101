"""
Ejemplo de uso completo del cliente con control de flujo avanzado.

Este archivo demuestra las tres características principales:
1. Timeout individual por petición
2. Cancelación de tareas en grupo
3. Carga con prioridad
"""

import asyncio
import aiohttp
from coordinador_async import (
    ejecutar_con_timeout,
    listar_productos,
    obtener_categorias,
    obtener_perfil,
    cargar_dashboard_con_cancelacion,
    cargar_con_prioridad,
    TimeoutError,
    NoAutorizado
)


async def ejemplo_1_timeout_individual():
    """
    EJEMPLO 1: Timeout individual por petición
    
    Demuestra cómo cada petición puede tener su propio timeout.
    """
    print("\n" + "="*70)
    print("EJEMPLO 1: Timeout Individual por Petición")
    print("="*70)
    
    print("\nLanzando 3 peticiones con diferentes timeouts:")
    print("  • Productos: timeout de 5 segundos")
    print("  • Categorías: timeout de 3 segundos")
    print("  • Perfil: timeout de 2 segundos")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Ejecutar en paralelo con timeouts específicos
            resultados = await asyncio.gather(
                listar_productos(session, timeout=5.0),
                obtener_categorias(session, timeout=3.0),
                obtener_perfil(session, timeout=2.0),
                return_exceptions=True
            )
            
            nombres = ["Productos (5s)", "Categorías (3s)", "Perfil (2s)"]
            
            print("\n📊 Resultados:")
            print("-" * 70)
            
            for nombre, resultado in zip(nombres, resultados):
                if isinstance(resultado, TimeoutError):
                    print(f"  ⏱️  [{nombre}] TIMEOUT")
                elif isinstance(resultado, Exception):
                    print(f"  ❌ [{nombre}] ERROR: {type(resultado).__name__}")
                else:
                    tipo = "list" if isinstance(resultado, list) else "dict"
                    tamano = len(resultado) if isinstance(resultado, (list, dict)) else 0
                    print(f"  ✅ [{nombre}] {tipo} con {tamano} elementos")
            
            print("\n💡 Ventaja: Cada petición tiene su timeout óptimo")
            print("   Peticiones rápidas fallan rápido si hay problemas")
            print("   Peticiones lentas tienen tiempo suficiente")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Asegúrate de que el servidor mock esté corriendo en localhost:3000")


async def ejemplo_2_cancelacion_grupo():
    """
    EJEMPLO 2: Cancelación de tareas en grupo
    
    Demuestra la cancelación automática cuando hay error 401.
    """
    print("\n" + "="*70)
    print("EJEMPLO 2: Cancelación Automática por Error 401")
    print("="*70)
    
    print("\nEscenario:")
    print("  • Si obtener_perfil falla con 401 (No Autorizado)")
    print("  • Las demás peticiones se cancelan automáticamente")
    print("  • No tiene sentido continuar sin autenticación válida")
    
    try:
        resultado = await cargar_dashboard_con_cancelacion()
        
        print("\n📊 Resultados:")
        print("-" * 70)
        
        print(f"\nCanceladas por autenticación: {resultado['canceladas_por_auth']}")
        
        if resultado['canceladas_por_auth']:
            print("\n🚫 Error de autenticación detectado!")
            print("   → Las peticiones pendientes fueron canceladas")
            print("   → Redirigir al usuario a la página de login")
        
        print(f"\nDatos cargados:")
        for endpoint, datos in resultado["datos"].items():
            if datos is not None:
                tipo = "list" if isinstance(datos, list) else "dict"
                tamano = len(datos) if isinstance(datos, (list, dict)) else 0
                print(f"  ✅ [{endpoint}] {tipo} con {tamano} elementos")
            else:
                print(f"  ❌ [{endpoint}] No cargado")
        
        if resultado["errores"]:
            print(f"\nErrores detectados ({len(resultado['errores'])}):")
            for error_info in resultado["errores"]:
                simbolo = "🔴" if error_info.get("cancelada") else "❌"
                print(f"  {simbolo} [{error_info['endpoint']}] {error_info['error']}")
        
        print("\n💡 Ventaja: Detección rápida de problemas de autenticación")
        print("   Se evita hacer peticiones inútiles que también fallarían")
        print("   Tiempo de respuesta mucho menor")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Asegúrate de que el servidor mock esté corriendo")


async def ejemplo_3_carga_prioridad():
    """
    EJEMPLO 3: Carga con prioridad
    
    Demuestra el procesamiento incremental de resultados.
    """
    print("\n" + "="*70)
    print("EJEMPLO 3: Carga con Prioridad (Procesamiento Incremental)")
    print("="*70)
    
    print("\nEstrategia:")
    print("  🔥 CRÍTICAS: Productos y Perfil")
    print("     → Sin estos, no se puede mostrar el dashboard")
    print("  📌 SECUNDARIAS: Categorías y Notificaciones")
    print("     → Mejoran la experiencia pero no son esenciales")
    
    print("\n⏳ Cargando dashboard con priorización...")
    
    try:
        import time
        inicio = time.time()
        
        resultado = await cargar_con_prioridad()
        
        tiempo_total = time.time() - inicio
        
        print("\n📊 Resultados:")
        print("-" * 70)
        
        if resultado['criticas_completas']:
            print("\n🎉 ¡DASHBOARD PARCIAL DISPONIBLE!")
            if resultado['tiempo_dashboard_parcial']:
                print(f"   Listo en: {resultado['tiempo_dashboard_parcial']:.2f}s")
                print(f"   Dashboard completo en: {tiempo_total:.2f}s")
                ganancia = tiempo_total - resultado['tiempo_dashboard_parcial']
                print(f"   📈 Usuario vio contenido {ganancia:.2f}s antes")
        else:
            print("\n⚠️ No se pudieron cargar las peticiones críticas")
            print("   No es posible mostrar el dashboard parcial")
        
        print(f"\nOrden de llegada de las respuestas:")
        for i, endpoint in enumerate(resultado['orden_llegada'], 1):
            es_critica = "🔥" if endpoint in ["productos", "perfil"] else "📌"
            print(f"  {i}. {es_critica} {endpoint.capitalize()}")
        
        print(f"\nDatos finales:")
        for endpoint, datos in resultado["datos"].items():
            if datos is not None:
                tipo = "list" if isinstance(datos, list) else "dict"
                tamano = len(datos) if isinstance(datos, (list, dict)) else 0
                es_critica = "🔥" if endpoint in ["productos", "perfil"] else "📌"
                print(f"  {es_critica} [{endpoint}] ✅ {tipo} con {tamano} elementos")
            else:
                print(f"     [{endpoint}] ❌ No disponible")
        
        if resultado["errores"]:
            print(f"\nErrores ({len(resultado['errores'])}):")
            for error_info in resultado["errores"]:
                print(f"  ❌ [{error_info['endpoint']}] {error_info['error']}")
        
        print("\n💡 Ventaja: Dashboard parcial disponible antes")
        print("   El usuario ve productos y perfil inmediatamente")
        print("   Las secciones secundarias aparecen después, sin bloquear la UI")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Asegúrate de que el servidor mock esté corriendo")


async def ejemplo_4_comparacion():
    """
    EJEMPLO 4: Comparación de estrategias
    
    Compara gather() vs wait() visualmente.
    """
    print("\n" + "="*70)
    print("EJEMPLO 4: Comparación de Estrategias")
    print("="*70)
    
    print("\n📊 asyncio.gather() (usado en ACT3 AI):")
    print("-" * 70)
    print("  • Espera a que TODAS las tareas terminen")
    print("  • Retorna resultados en el MISMO orden que se lanzaron")
    print("  • El usuario debe esperar a la petición más lenta")
    print("  • Simple pero inflexible")
    
    print("\n  Ejemplo: gather(productos:2s, categorias:3s, perfil:1s, notif:4s)")
    print("  → Usuario espera 4s para ver CUALQUIER resultado")
    
    print("\n📊 asyncio.wait(FIRST_COMPLETED) (usado en ACT4 AI):")
    print("-" * 70)
    print("  • Procesa resultados conforme llegan")
    print("  • Retorna resultados en ORDEN DE LLEGADA")
    print("  • El usuario ve resultados incrementales")
    print("  • Más complejo pero mucho más flexible")
    
    print("\n  Ejemplo: wait(productos:2s, categorias:3s, perfil:1s, notif:4s)")
    print("  → Usuario ve perfil en 1s")
    print("  → Usuario ve productos en 2s → 🎉 Dashboard parcial")
    print("  → Usuario ve categorías en 3s")
    print("  → Usuario ve notificaciones en 4s → Dashboard completo")
    
    print("\n📈 Métricas Comparadas:")
    print("-" * 70)
    print("                                 gather()    wait()    Mejora")
    print("  Tiempo hasta 1er dato visible    4s         1s       75% ⬇")
    print("  Tiempo hasta dashboard parcial   4s         2s       50% ⬇")
    print("  Tiempo hasta dashboard completo  4s         4s        0%")
    
    print("\n💡 Conclusión:")
    print("   wait() ofrece mejor UX percibida al mostrar contenido incremental")
    print("   gather() es más simple pero el usuario espera más tiempo")


async def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "="*70)
    print("EJEMPLOS DE CONTROL DE FLUJO ASÍNCRONO - ACT4 AI")
    print("="*70)
    print("\nNOTA: Para que algunos ejemplos funcionen, necesitas:")
    print("  1. Servidor mock corriendo en localhost:3000")
    print("  2. Endpoints: /api/productos, /api/categorias, /api/perfil")
    print("\nSi no tienes el servidor, los ejemplos mostrarán errores de conexión")
    print("pero igual demuestran la lógica de control de flujo.")
    
    # Ejecutar todos los ejemplos
    await ejemplo_1_timeout_individual()
    await ejemplo_2_cancelacion_grupo()
    await ejemplo_3_carga_prioridad()
    await ejemplo_4_comparacion()
    
    print("\n" + "="*70)
    print("FIN DE LOS EJEMPLOS")
    print("="*70)
    print("\nPara profundizar:")
    print("  • Revisa README.md para documentación completa")
    print("  • Revisa diagramas.md para diagramas temporales detallados")
    print("  • Ejecuta los tests individuales para ver casos específicos")


if __name__ == "__main__":
    asyncio.run(main())
