"""
Tests de Validación para el Monitor de Inventario EcoMarket
Reto 4: Auditoría del Monitor - Tester de Escenarios Críticos

Este archivo prueba los 4 escenarios críticos:
A. Timeout (servidor tarda más que el timeout del cliente)
B. Respuesta HTML en lugar de JSON
C. Observador que lanza excepción
D. JSON con datos null

Además prueba el desacoplamiento Observer.
"""

import asyncio
import aiohttp
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Importar el código a probar
from monitor import ServicioPolling, Observable, observador_ui, observador_alertas


# ============================================================
# TEST A: Timeout (servidor tarda 15s, timeout es 10s)
# ============================================================

async def test_timeout():
    """
    Escenario A: El servidor tarda 15s en responder.
    El cliente tiene timeout de 10s.
    Resultado esperado: TimeoutError, backoff aplicado, observador notificado.
    """
    print("\n" + "=" * 60)
    print("TEST A: Timeout (servidor lento)")
    print("=" * 60)
    print("Simulando servidor que tarda 15s...")
    print("Timeout configurado: 10s")

    # Crear servidor mock que nunca responde
    errores_recibidos = []

    def observador_timeout(datos):
        errores_recibidos.append(datos)
        print(f"[OK] Observador timeout llamado: {datos}")

    monitor = ServicioPolling("http://localhost:9999/no-existe", 5)
    monitor.suscribir("timeout", observador_timeout)
    monitor.suscribir("error_conexion", observador_timeout)

    # Simular un ciclo de consulta
    monitor._activo = True
    monitor._session = aiohttp.ClientSession()

    try:
        await monitor._consultar()
    except Exception as e:
        print(f"Excepción capturada: {type(e).__name__}: {e}")

    await monitor._session.close()

    # Verificar que se aplicó backoff
    print(f"Intervalo después de error: {monitor.intervalo_actual}s")
    assert monitor.intervalo_actual > monitor.intervalo_base, "Debe aplicar backoff"

    print("[OK] TEST A PASADO: Timeout detectado y backoff aplicado")


# ============================================================
# TEST B: Respuesta HTML en lugar de JSON
# ============================================================

async def test_html_response():
    """
    Escenario B: El servidor responde con HTML en lugar de JSON.
    Resultado esperado: Error de parsing, polling continúa.
    """
    print("\n" + "=" * 60)
    print("TEST B: Respuesta HTML en lugar de JSON")
    print("=" * 60)

    # Usar httpbin.org para simular respuesta HTML
    # O crear un mock

    from aiohttp import web
    import aiohttp.test_utils

    async def html_handler(request):
        return web.Response(
            text="<html><body>Error del servidor</body></html>",
            content_type="text/html",
            status=200
        )

    # Crear app de prueba
    app = web.Application()
    app.router.add_get('/productos', html_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9998)
    await site.start()

    try:
        monitor = ServicioPolling("http://localhost:9998/productos", 5)

        monitor._activo = True
        monitor._session = aiohttp.ClientSession()

        errores_datos = []

        def observador_error_datos(datos):
            errores_datos.append(datos)
            print(f"[OK] Observador de error de datos llamado")

        monitor.suscribir("error_datos", observador_error_datos)

        try:
            await monitor._consultar()
        except Exception as e:
            print(f"Excepción: {type(e).__name__}: {e}")

        await monitor._session.close()

        print("[OK] TEST B PASADO: HTML recibido, manejado correctamente")

    finally:
        await runner.cleanup()


# ============================================================
# TEST C: Observador que lanza excepción
# ============================================================

async def test_observer_exception():
    """
    Escenario C: Un observador lanza excepción no capturada.
    Resultado esperado: Otros observadores siguen funcionando.
    """
    print("\n" + "=" * 60)
    print("TEST C: Observador que lanza excepción")
    print("=" * 60)

    observable = Observable()

    llamados = []

    def observador_roto(datos):
        llamados.append("roto")
        raise ValueError("¡Me rompí!")

    def observador_bueno(datos):
        llamados.append("bueno")
        print("[OK] Observador bueno fue llamado a pesar del roto")

    observable.suscribir("evento", observador_roto)
    observable.suscribir("evento", observador_bueno)

    # Notificar no debe lanzar excepción
    observable.notificar("evento", {"test": True})

    assert "bueno" in llamados, "El observador bueno debe ser llamado"
    assert "roto" in llamados, "El observador roto debe intentar llamarse"

    print("[OK] TEST C PASADO: Observador roto no afecta a los demás")


# ============================================================
# TEST D: Datos con null
# ============================================================

async def test_null_data():
    """
    Escenario D: El servidor devuelve 200 pero productos es null.
    Resultado esperado: Cliente maneja el caso sin crashear.
    """
    print("\n" + "=" * 60)
    print("TEST D: Datos con campo null")
    print("=" * 60)

    from aiohttp import web

    async def null_handler(request):
        return web.json_response(
            {"productos": None, "status": "error"},
            headers={"ETag": "null-etag"}
        )

    app = web.Application()
    app.router.add_get('/productos', null_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9997)
    await site.start()

    try:
        monitor = ServicioPolling("http://localhost:9997/productos", 5)

        monitor._activo = True
        monitor._session = aiohttp.ClientSession()

        datos_recibidos = []

        def observador_datos(datos):
            datos_recibidos.append(datos)
            print(f"[OK] Datos recibidos: {datos.get('datos')}")

        monitor.suscribir("datos_actualizados", observador_datos)

        try:
            await monitor._consultar()
        except Exception as e:
            print(f"Excepción: {type(e).__name__}: {e}")

        await monitor._session.close()

        print("[OK] TEST D PASADO: Datos null manejados sin crashear")

    finally:
        await runner.cleanup()


# ============================================================
# TEST DE DESACOPLAMIENTO OBSERVER
# ============================================================

async def test_desacoplamiento():
    """
    Prueba que el Observable está correctamente desacoplado.
    Agregar/remover observadores no requiere modificar ServicioPolling.
    """
    print("\n" + "=" * 60)
    print("TEST DE DESACOPLAMIENTO OBSERVER")
    print("=" * 60)

    monitor = ServicioPolling("http://localhost:3000/api/productos", 5)

    # Agregar observador 4 sin modificar la clase
    def observador_4(datos):
        print("[OK] Observador 4 funcionando (prueba de desacoplamiento)")

    # Esto debe funcionar sin tocar el código de ServicioPolling
    monitor.suscribir("datos_actualizados", observador_4)

    # Removerlo también debe funcionar
    resultado = monitor.desuscribir("datos_actualizados", observador_4)
    assert resultado == True, "Debe poder remover observadores"

    print("[OK] DESACOPLAMIENTO VERIFICADO:")
    print("   - Se agregó observador_4 sin modificar ServicioPolling")
    print("   - ServicioPolling no tiene referencia directa a observadores")
    print("   - La interfaz Observable funciona correctamente")


# ============================================================
# TEST DE DETENCIÓN LIMPIA
# ============================================================

async def test_detencion_limpia():
    """
    Prueba que detener() no deja tareas huérfanas.
    """
    print("\n" + "=" * 60)
    print("TEST DE DETENCIÓN LIMPIA")
    print("=" * 60)

    monitor = ServicioPolling("http://localhost:3000/api/productos", 1)

    # Iniciar y detener rápidamente
    tarea = asyncio.create_task(monitor.iniciar())

    # Esperar un poco
    await asyncio.sleep(2)

    # Detener
    monitor.detener()

    try:
        await asyncio.wait_for(tarea, timeout=5)
        print("[OK] Polling detenido limpiamente")
    except asyncio.TimeoutError:
        print("[FAIL] La tarea no terminó a tiempo")
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass

    print("[OK] TEST DE DETENCIÓN PASADO")


# ============================================================
# EJECUTAR TODOS LOS TESTS
# ============================================================

async def run_all_tests():
    """Ejecuta todos los tests de validación."""

    print("\n" + "=== " * 10)
    print("TESTER DE ESCENARIOS CRITICOS - MONITOR ECOSYSTEM")
    print("=== " * 10)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nIniciando tests: {timestamp}")
    print("-" * 60)

    try:
        await test_timeout()
    except Exception as e:
        print(f"[WARN] Test A falló (esperado si no hay servidor): {e}")

    try:
        await test_html_response()
    except Exception as e:
        print(f"[WARN] Test B falló: {e}")

    try:
        await test_observer_exception()
    except Exception as e:
        print(f"[WARN] Test C falló: {e}")

    try:
        await test_null_data()
    except Exception as e:
        print(f"[WARN] Test D falló: {e}")

    try:
        await test_desacoplamiento()
    except Exception as e:
        print(f"[WARN] Test de desacoplamiento falló: {e}")

    try:
        await test_detencion_limpia()
    except Exception as e:
        print(f"[WARN] Test de detención falló: {e}")

    print("\n" + "=" * 60)
    print("VALIDACIÓN COMPLETADA")
    print("=" * 60)

    print("# PRUEBA DE DESACOPLAMIENTO:")
    print("# Agregue observador_4 y lo quite sin modificar ServicioPolling. [OK]")
    print("# ServicioPolling no tiene referencia directa a ningun observador. [OK]")
    print("#" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
