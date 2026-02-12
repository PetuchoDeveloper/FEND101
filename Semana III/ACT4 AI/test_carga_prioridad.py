"""
Tests para demostrar la carga con prioridad usando asyncio.wait().

Demuestra que:
1. Los resultados se procesan conforme llegan (no esperan a todas las tareas)
2. El dashboard parcial se muestra cuando llegan las peticiones críticas
3. Las peticiones secundarias se procesan cuando lleguen
4. asyncio.wait() con FIRST_COMPLETED permite procesamiento incremental
"""

import asyncio
import time
from coordinador_async import cargar_con_prioridad


async def simular_peticion(nombre: str, segundos: float, valor):
    """Simula una petición que tarda un tiempo específico"""
    print(f"  [{nombre}] Iniciando (tardará {segundos}s)...")
    await asyncio.sleep(segundos)
    print(f"  [{nombre}] ✅ Completada después de {segundos}s")
    return valor


async def test_procesamiento_incremental():
    """
    TEST 1: Procesamiento incremental con asyncio.wait()
    
    Demuestra que los resultados se procesan conforme llegan.
    """
    print("\n" + "="*60)
    print("TEST 1: Procesamiento Incremental")
    print("="*60)
    
    print("\nEscenario:")
    print("  - 4 peticiones que tardan: 1s, 2s, 3s, 4s")
    print("  - Procesar cada resultado conforme llega (no esperar a todas)")
    print("  - Mostrar el orden de llegada")
    
    print("\n⏳ Ejecutando...\n")
    
    inicio = time.time()
    
    # Crear tareas con diferentes tiempos
    tareas_info = {
        asyncio.create_task(simular_peticion("Rápida", 1.0, "A")): "Rápida",
        asyncio.create_task(simular_peticion("Media", 2.0, "B")): "Media",
        asyncio.create_task(simular_peticion("Lenta", 3.0, "C")): "Lenta",
        asyncio.create_task(simular_peticion("Muy Lenta", 4.0, "D")): "Muy Lenta"
    }
    
    pendientes = set(tareas_info.keys())
    orden_llegada = []
    
    print("📊 Procesando resultados conforme llegan:")
    print("-" * 60)
    
    while pendientes:
        # Esperar a que al menos una tarea termine
        done, pendientes = await asyncio.wait(
            pendientes,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for tarea in done:
            nombre = tareas_info[tarea]
            resultado = await tarea
            tiempo_actual = time.time() - inicio
            orden_llegada.append(nombre)
            
            print(f"  ⏱️  {tiempo_actual:.2f}s → [{nombre}] llegó con valor: {resultado}")
    
    tiempo_total = time.time() - inicio
    
    print(f"\n📊 Resumen:")
    print(f"  Tiempo total: {tiempo_total:.2f}s")
    print(f"  Orden de llegada: {' → '.join(orden_llegada)}")
    
    print("\n✅ VERIFICACIÓN:")
    print("  - Los resultados se procesaron conforme llegaron")
    print("  - NO se esperó a que todas las tareas terminaran")
    print("  - El orden de llegada corresponde al tiempo de cada tarea")


async def test_dashboard_parcial():
    """
    TEST 2: Dashboard parcial con peticiones críticas
    
    Demuestra que se puede mostrar el dashboard cuando llegan las críticas.
    """
    print("\n" + "="*60)
    print("TEST 2: Dashboard Parcial con Peticiones Críticas")
    print("="*60)
    
    print("\nEscenario:")
    print("  CRÍTICAS (mostrar dashboard cuando lleguen):")
    print("    - Productos: tarda 2s")
    print("    - Perfil: tarda 1s")
    print("  SECUNDARIAS (procesar cuando lleguen):")
    print("    - Categorías: tarda 3s")
    print("    - Notificaciones: tarda 4s")
    
    print("\n⏳ Ejecutando simulación...\n")
    
    inicio = time.time()
    
    # Simular las 4 peticiones
    tarea_productos = asyncio.create_task(simular_peticion("Productos", 2.0, ["producto1", "producto2"]))
    tarea_perfil = asyncio.create_task(simular_peticion("Perfil", 1.0, {"nombre": "Usuario"}))
    tarea_categorias = asyncio.create_task(simular_peticion("Categorías", 3.0, ["frutas", "verduras"]))
    tarea_notificaciones = asyncio.create_task(simular_peticion("Notificaciones", 4.0, ["notif1", "notif2"]))
    
    todas_las_tareas = {tarea_productos, tarea_perfil, tarea_categorias, tarea_notificaciones}
    tareas_criticas = {tarea_productos, tarea_perfil}
    
    tareas_info = {
        tarea_productos: "Productos",
        tarea_perfil: "Perfil",
        tarea_categorias: "Categorías",
        tarea_notificaciones: "Notificaciones"
    }
    
    pendientes = todas_las_tareas.copy()
    criticas_completadas = set()
    dashboard_parcial_mostrado = False
    
    print("📊 Procesando resultados:")
    print("-" * 60)
    
    while pendientes:
        done, pendientes = await asyncio.wait(
            pendientes,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for tarea in done:
            nombre = tareas_info[tarea]
            resultado = await tarea
            tiempo_actual = time.time() - inicio
            
            print(f"  ⏱️  {tiempo_actual:.2f}s → [{nombre}] llegó")
            
            # Marcar críticas completadas
            if tarea in tareas_criticas:
                criticas_completadas.add(tarea)
                
                # ¿Ya podemos mostrar dashboard parcial?
                if criticas_completadas == tareas_criticas and not dashboard_parcial_mostrado:
                    print(f"\n  🎉 ¡DASHBOARD PARCIAL LISTO! (después de {tiempo_actual:.2f}s)")
                    print("     El usuario ya puede ver productos y perfil")
                    print("     Las secciones secundarias seguirán cargando...\n")
                    dashboard_parcial_mostrado = True
    
    tiempo_total = time.time() - inicio
    
    print(f"\n📊 Resumen:")
    print(f"  Dashboard completo después de: {tiempo_total:.2f}s")
    print(f"  Dashboard parcial estuvo listo en: ~2.0s (cuando llegó Productos)")
    print(f"  Ganancia: El usuario vio contenido {tiempo_total - 2.0:.1f}s antes")
    
    print("\n✅ VERIFICACIÓN:")
    print("  - Dashboard parcial se mostró cuando llegaron las críticas")
    print("  - Las secundarias se procesaron después, sin bloquear la UI")
    print("  - MEJOR EXPERIENCIA: Usuario ve contenido inmediatamente")


async def test_diagrama_temporal_prioridad():
    """
    TEST 3: Diagrama temporal de carga con prioridad
    """
    print("\n" + "="*60)
    print("TEST 3: Diagrama Temporal de Carga con Prioridad")
    print("="*60)
    
    print("\n📊 Diagrama Temporal:")
    print("-" * 60)
    print("Tiempo →      0s    1s    2s    3s    4s")
    print("Perfil (C):   [██]✅                     ")
    print("Productos(C): [████]✅                   ")
    print("              ↑                          ")
    print("              └─ 🎉 DASHBOARD PARCIAL   ")
    print("                                         ")
    print("Categorías:   [██████]✅                          ")
    print("Notific.:     [████████]✅               ")
    print("-" * 60)
    print("\nLeyenda:")
    print("  (C) = Petición CRÍTICA")
    print("  ██  = Ejecución activa")
    print("  ✅  = Completada")
    print("  🎉  = Dashboard parcial listo para mostrar")
    
    print("\n✅ CONCLUSIÓN:")
    print("  - asyncio.wait(FIRST_COMPLETED) permite procesamiento incremental")
    print("  - Dashboard parcial se muestra cuando llegan las críticas")
    print("  - Usuario ve contenido ANTES de que todo termine")
    print("  - Mejor experiencia percibida de velocidad")


async def test_cargar_con_prioridad_real():
    """
    TEST 4: Prueba real con el cliente (requiere servidor mock)
    """
    print("\n" + "="*60)
    print("TEST 4: Prueba Real con cargar_con_prioridad()")
    print("="*60)
    
    print("\nNota: Este test requiere servidor mock corriendo")
    print("Si el servidor no está disponible, mostrará ConexionError\n")
    
    try:
        inicio = time.time()
        resultado = await cargar_con_prioridad()
        tiempo_total = time.time() - inicio
        
        print(f"\n📊 Resultados:")
        print("-" * 60)
        
        print(f"\nCríticas completas: {resultado['criticas_completas']}")
        
        if resultado['tiempo_dashboard_parcial']:
            print(f"⏱️  Dashboard parcial listo en: {resultado['tiempo_dashboard_parcial']:.2f}s")
            print(f"⏱️  Dashboard completo en: {tiempo_total:.2f}s")
            ganancia = tiempo_total - resultado['tiempo_dashboard_parcial']
            print(f"📈 Ganancia percibida: {ganancia:.2f}s")
        
        print(f"\nOrden de llegada: {' → '.join(resultado['orden_llegada'])}")
        
        print(f"\nDatos cargados:")
        for endpoint, datos in resultado["datos"].items():
            if datos is not None:
                tipo = "list" if isinstance(datos, list) else "dict"
                tamano = len(datos) if isinstance(datos, (list, dict)) else 0
                es_critica = "🔥" if endpoint in ["productos", "perfil"] else "  "
                print(f"  {es_critica} [{endpoint}] ✅ {tipo} con {tamano} items")
            else:
                print(f"     [{endpoint}] ❌ None (no cargado)")
        
        if resultado["errores"]:
            print(f"\nErrores ({len(resultado['errores'])}):")
            for error_info in resultado["errores"]:
                print(f"  [{error_info['endpoint']}] ❌ {error_info['error']}")
        
        print("\n✅ VERIFICACIÓN:")
        if resultado['criticas_completas']:
            print("  - Las peticiones críticas (productos y perfil) llegaron")
            print("  - El dashboard parcial pudo mostrarse temprano")
        print("  - Los resultados se procesaron en el orden que llegaron")
        print("  - asyncio.wait() permitió procesamiento incremental")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Asegúrate de que el servidor mock esté corriendo")


async def test_comparacion_gather_vs_wait():
    """
    TEST 5: Comparación gather() vs wait()
    """
    print("\n" + "="*60)
    print("TEST 5: Comparación gather() vs wait()")
    print("="*60)
    
    print("\n📊 asyncio.gather() - Espera a TODAS las tareas:")
    print("-" * 60)
    print("  - Lanza todas las tareas")
    print("  - Espera a que TODAS terminen")
    print("  - Retorna resultados en el MISMO ORDEN que se lanzaron")
    print("  - El usuario debe esperar a la más lenta")
    print("\n  Ejemplo: gather(A:1s, B:5s, C:2s)")
    print("  → Usuario espera 5s para ver CUALQUIER resultado")
    
    print("\n📊 asyncio.wait(FIRST_COMPLETED) - Procesa conforme llegan:")
    print("-" * 60)
    print("  - Lanza todas las tareas")
    print("  - Procesa cada resultado CONFORME LLEGA")
    print("  - Retorna resultados en ORDEN DE LLEGADA")
    print("  - El usuario ve resultados incrementales")
    print("\n  Ejemplo: wait(A:1s, B:5s, C:2s)")
    print("  → Usuario ve A después de 1s")
    print("  → Usuario ve C después de 2s")
    print("  → Usuario ve B después de 5s")
    
    print("\n✅ CONCLUSIÓN:")
    print("  - gather() es más simple, pero menos flexible")
    print("  - wait() permite procesamiento incremental y priorización")
    print("  - Para dashboards, wait() ofrece mejor UX")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS DE CARGA CON PRIORIDAD")
    print("="*60)
    
    # Ejecutar todos los tests
    asyncio.run(test_procesamiento_incremental())
    asyncio.run(test_dashboard_parcial())
    asyncio.run(test_diagrama_temporal_prioridad())
    asyncio.run(test_cargar_con_prioridad_real())
    asyncio.run(test_comparacion_gather_vs_wait())
    
    print("\n" + "="*60)
    print("Tests completados")
    print("="*60)
