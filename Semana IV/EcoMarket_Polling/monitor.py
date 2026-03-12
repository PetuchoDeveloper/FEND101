"""
DECISIONES DE DISEÑO — Monitor de Inventario EcoMarket
=======================================================
INTERVALO_BASE = 5s
  → Trade-off: callbacks síncronos alargan el ciclo real.
    Si el observador de logs tarda 2s, el ciclo efectivo es 7s.
    Decisión: aceptable para inventario; en dashboards en tiempo
    real habría que hacer los callbacks asíncronos.

INTERVALO_MAX = 60s
  → Trade-off: cliente descansa más, pero datos pueden tener
    hasta 60s de retraso. Para EcoMarket esto es aceptable.

TIMEOUT = 10s
  → Si el servidor no responde en 10s, el cliente lo trata como
    fallo y aplica backoff. Sin timeout, el ciclo quedaría colgado.

ETAG vs Timestamp:
  → Usamos ETag porque el servidor mock lo soporta. Si no,
    usaríamos un campo updated_at para comparar.

BACKOFF_MULTIPLIER = 1.5
  → Crece gradualmente para no sobrecargar al servidor cuando
    está teniendo problemas, pero tampoco esperar demasiado.

PATRÓN OBSERVER:
  → Permite desacoplar la detección de cambios (polling) de
    la reacción (UI, alertas, logs). Para migrar a WebSocket,
    solo cambiamos la clase base, los observadores no cambian.

AUTOR: [Tu nombre]
FECHA: 2026-03-12
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_URL = "http://localhost:3000/api"
INTERVALO_BASE = 5          # segundos
INTERVALO_MAX = 60          # segundos
TIMEOUT = 10                # segundos
BACKOFF_MULTIPLIER = 1.5    # multiplicador para backoff


# ============================================================
# EXCEPCIONES
# ============================================================

class PollingError(Exception):
    """Error base para el sistema de polling."""
    pass


class ServidorNoDisponibleError(PollingError):
    """El servidor no responde o está caído."""
    pass


class DatosInvalidosError(PollingError):
    """Los datos recibidos no son válidos."""
    pass


# ============================================================
# CLASE OBSERVABLE (Patrón Observer)
# ============================================================

class Observable:
    """
    Implementación del patrón Observer.

    Permite desacoplar la detección de eventos de su manejo.
    Múltiples observadores pueden suscribirse a un mismo evento.

    Ejemplo:
        >>> observable = Observable()
        >>> observable.suscribir("datos_actualizados", mi_callback)
        >>> observable.notificar("datos_actualizados", {"datos": []})
    """

    def __init__(self):
        """Inicializa el diccionario de observadores."""
        # Diccionario: cada clave es un nombre de evento,
        # su valor es una lista de funciones (callbacks) suscritas
        self._observadores: Dict[str, List[Callable]] = {}

    def suscribir(self, evento: str, callback: Callable) -> None:
        """
        Suscribe un callback a un evento.

        Args:
            evento: Nombre del evento a observar
            callback: Función que se llamará cuando ocurra el evento
        """
        # Si es la primera suscripción a este evento, crear lista
        if evento not in self._observadores:
            self._observadores[evento] = []

        # Agregar el callback a la lista de ese evento
        self._observadores[evento].append(callback)
        self._log_evento(f"Nuevo observador suscrito a '{evento}'")

    def desuscribir(self, evento: str, callback: Callable) -> bool:
        """
        Desuscribe un callback de un evento.

        Args:
            evento: Nombre del evento
            callback: Función callback a remover

        Returns:
            True si se encontró y removió, False si no existía
        """
        if evento in self._observadores:
            if callback in self._observadores[evento]:
                self._observadores[evento].remove(callback)
                self._log_evento(f"Observador removido de '{evento}'")
                return True
        return False

    def notificar(self, evento: str, datos: Any = None) -> None:
        """
        Notifica a todos los observadores de un evento.

        Ejecuta todos los callbacks del evento con los datos proporcionados.
        Un callback que falle NO afecta a los demás.

        Args:
            evento: Nombre del evento a notificar
            datos: Datos a pasar a los callbacks
        """
        if evento not in self._observadores:
            return

        for callback in self._observadores[evento]:
            try:
                callback(datos)
            except Exception as e:
                # Un callback roto NO detiene a los demás
                self._log_evento(f"ERROR: Observador falló en '{evento}': {e}")

    def _log_evento(self, mensaje: str) -> None:
        """Log interno de eventos del Observable."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [Observable] {mensaje}")


# ============================================================
# CLASE SERVICIO POLLING
# ============================================================

class ServicioPolling(Observable):
    """
    Servicio de polling adaptativo para EcoMarket.

    Extiende Observable para permitir que componentes se suscriban
    a eventos como datos_actualizados, error_servidor, etc.

    Características:
    - Polling con ETag para eficiencia (304 = sin cambios)
    - Intervalo adaptativo: crece con 304, se resetea con 200
    - Backoff ante errores (5xx, timeout)
    - Límites: INTERVALO_BASE <= intervalo <= INTERVALO_MAX
    - Detención limpia sin tareas huérfanas

    Ejemplo:
        >>> monitor = ServicioPolling("http://localhost:3000/api/productos", 5)
        >>> monitor.suscribir("datos_actualizados", actualizar_ui)
        >>> await monitor.iniciar()  # Inicia el polling
        >>> await monitor.detener()  # Detiene limpiamente
    """

    def __init__(self, url: str, intervalo_base: int = INTERVALO_BASE):
        """
        Inicializa el servicio de polling.

        Args:
            url: URL del endpoint a monitorear
            intervalo_base: Intervalo inicial en segundos
        """
        super().__init__()

        self.url = url
        self.intervalo_base = intervalo_base
        self.intervalo_actual = intervalo_base
        self.intervalo_max = INTERVALO_MAX

        self.ultimo_etag: Optional[str] = None
        self._activo = False
        self._session: Optional[aiohttp.ClientSession] = None

        # Estadísticas para debugging
        self._ciclos = 0
        self._cambios_detectados = 0
        self._errores = 0

    async def iniciar(self) -> None:
        """
        Inicia el ciclo de polling.

        El ciclo continúa mientras _activo sea True.
        Cada iteración consulta el servidor y espera
        el intervalo_actual antes de la siguiente.
        """
        # TODO: poner _activo = True
        self._activo = True

        # Crear sesión HTTP persistente
        self._session = aiohttp.ClientSession()

        self._log(f"Polling iniciado - URL: {self.url}")
        self._log(f"Intervalo base: {self.intervalo_base}s, Máximo: {self.intervalo_max}s")

        # TODO: ciclo "mientras _activo: await _consultar()"
        while self._activo:
            self._ciclos += 1
            self._log(f"=== Ciclo #{self._ciclos} | Intervalo: {self.intervalo_actual:.1f}s ===")

            try:
                await self._consultar()
            except Exception as e:
                self._log(f"ERROR inesperado en ciclo: {e}")
                self._errores += 1

            if self._activo:
                # TODO: await dormir(intervalo)
                await asyncio.sleep(self.intervalo_actual)

        # Limpiar al detener
        if self._session:
            await self._session.close()
            self._session = None

        self._log("Polling detenido limpiamente")

    async def _consultar(self) -> None:
        """
        Realiza una consulta al servidor.

        Gestiona:
        - Headers ETag/If-None-Match para eficiencia
        - Respuestas 200 (con cambios), 304 (sin cambios)
        - Errores 5xx (backoff), timeouts (backoff)
        - JSON parsing con manejo de errores
        """
        if not self._session:
            raise ServidorNoDisponibleError("No hay sesión HTTP activa")

        try:
            # TODO: preparar headers con ETag si existe
            headers = {}
            if self.ultimo_etag:
                headers["If-None-Match"] = self.ultimo_etag
                self._log(f"Enviando If-None-Match: {self.ultimo_etag}")

            # TODO: GET a url con timeout
            timeout = aiohttp.ClientTimeout(total=TIMEOUT)
            async with self._session.get(self.url, headers=headers, timeout=timeout) as response:

                # Manejar diferentes status codes
                if response.status == 200:
                    # TODO: si 200 → guardar etag, notificar("datos_actualizados")
                    await self._manejar_200(response)

                elif response.status == 304:
                    # TODO: si 304 → aumentar intervalo (backoff)
                    self._manejar_304()

                elif response.status >= 500:
                    # TODO: si 5xx → notificar("error_servidor"), backoff
                    await self._manejar_5xx(response)

                elif response.status >= 400:
                    # Errores 4xx no se reintentan (problema del cliente)
                    self._log(f"Error 4xx: {response.status} - No se reintenta")
                    self.notificar("error_cliente", {"status": response.status})

                else:
                    self._log(f"Status inesperado: {response.status}")

        except asyncio.TimeoutError:
            # TODO: capturar TimeoutError → notificar("timeout")
            self._manejar_timeout()

        except aiohttp.ClientConnectorError as e:
            self._log(f"Error de conexión: {e}")
            self._errores += 1
            self.notificar("error_conexion", {"error": str(e)})
            self._aplicar_backoff()

        except Exception as e:
            self._log(f"Error inesperado: {e}")
            self._errores += 1
            raise

    async def _manejar_200(self, response: aiohttp.ClientResponse) -> None:
        """Maneja respuesta 200 OK - hay cambios."""
        # Guardar nuevo ETag
        self.ultimo_etag = response.headers.get("ETag")
        self._log(f"Nuevo ETag recibido: {self.ultimo_etag}")

        try:
            # Parsear JSON
            datos = await response.json()

            # Resetear intervalo al base (hay actividad)
            self.intervalo_actual = self.intervalo_base
            self._log(f"Datos recibidos - Reset intervalo a {self.intervalo_actual}s")

            self._cambios_detectados += 1

            # Notificar a observadores
            self.notificar("datos_actualizados", {
                "ciclo": self._ciclos,
                "etag": self.ultimo_etag,
                "datos": datos,
                "timestamp": datetime.now().isoformat()
            })

        except json.JSONDecodeError as e:
            self._log(f"Error parseando JSON: {e}")
            self.notificar("error_datos", {"error": str(e)})

    def _manejar_304(self) -> None:
        """Maneja respuesta 304 Not Modified - sin cambios."""
        self._log("304 Not Modified - Sin cambios")

        # Aumentar intervalo gradualmente (backoff)
        self._aplicar_backoff()

        self.notificar("sin_cambios", {
            "ciclo": self._ciclos,
            "intervalo_actual": self.intervalo_actual,
            "timestamp": datetime.now().isoformat()
        })

    async def _manejar_5xx(self, response: aiohttp.ClientResponse) -> None:
        """Maneja errores 5xx del servidor."""
        texto = await response.text()
        self._log(f"Error servidor {response.status}: {texto[:100]}")
        self._errores += 1

        self.notificar("error_servidor", {
            "status": response.status,
            "mensaje": texto[:200],
            "ciclo": self._ciclos
        })

        # Aplicar backoff
        self._aplicar_backoff()

    def _manejar_timeout(self) -> None:
        """Maneja timeout de la petición."""
        self._log(f"TIMEOUT después de {TIMEOUT}s")
        self._errores += 1

        self.notificar("timeout", {
            "timeout": TIMEOUT,
            "ciclo": self._ciclos,
            "timestamp": datetime.now().isoformat()
        })

        self._aplicar_backoff()

    def _aplicar_backoff(self) -> None:
        """
        Aumenta el intervalo de polling gradualmente.

        Usa BACKOFF_MULTIPLIER hasta alcanzar INTERVALO_MAX.
        Esto protege al servidor cuando hay problemas.
        """
        nuevo_intervalo = self.intervalo_actual * BACKOFF_MULTIPLIER
        self.intervalo_actual = min(nuevo_intervalo, self.intervalo_max)
        self._log(f"Backoff aplicado - Nuevo intervalo: {self.intervalo_actual:.1f}s")

    def detener(self) -> None:
        """
        Detiene el polling limpiamente.

        La bandera _activo se pone en False.
        El ciclo termina en el próximo await, sin matar nada a la fuerza.
        """
        # TODO: _activo = False
        self._activo = False
        self._log("Señal de detención recibida - Terminando ciclo actual...")

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Retorna estadísticas del polling."""
        return {
            "ciclos_totales": self._ciclos,
            "cambios_detectados": self._cambios_detectados,
            "errores": self._errores,
            "intervalo_actual": self.intervalo_actual,
            "intervalo_base": self.intervalo_base,
            "intervalo_max": self.intervalo_max,
            "ultimo_etag": self.ultimo_etag,
            "activo": self._activo
        }

    def _log(self, mensaje: str) -> None:
        """Log con timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [Polling] {mensaje}")


# ============================================================
# OBSERVADORES (Funciones callback)
# ============================================================

def observador_ui(datos: Dict[str, Any]) -> None:
    """
    Observador de UI - Actualiza la interfaz de usuario.
    Simula una UI que muestra los productos actualizados.
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] [UI] 🖥️  Actualizando interfaz...")

    if datos and "datos" in datos:
        productos = datos["datos"]
        if isinstance(productos, list):
            print(f"  └─> {len(productos)} productos en inventario")
            for p in productos[:3]:  # Mostrar solo los primeros 3
                print(f"      • {p.get('nombre', 'N/A')}: ${p.get('precio', 0)} ({p.get('stock', 0)} unidades)")
            if len(productos) > 3:
                print(f"      ... y {len(productos) - 3} más")
        elif isinstance(productos, dict):
            print(f"  └─> Producto: {productos.get('nombre', 'N/A')}")

    print(f"  └─> ETag: {datos.get('etag', 'N/A')}")
    print(f"  └─> Ciclo #{datos.get('ciclo', 'N/A')}\n")


def observador_alertas(datos: Dict[str, Any]) -> None:
    """
    Observador de Alertas - Detecta productos agotados.
    Emite alertas cuando detecta stock = 0.
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    if not datos or "datos" not in datos:
        return

    productos = datos["datos"]
    alertas = []

    if isinstance(productos, list):
        for producto in productos:
            if producto.get("stock", 1) == 0:
                alertas.append(producto.get("nombre", "Producto desconocido"))
    elif isinstance(productos, dict) and productos.get("stock", 1) == 0:
        alertas.append(productos.get("nombre", "Producto desconocido"))

    if alertas:
        print(f"\n[{timestamp}] [ALERTA] 🚨 Productos agotados detectados:")
        for alerta in alertas:
            print(f"  ⚠️  {alerta}")
        print()


def observador_logs(datos: Dict[str, Any]) -> None:
    """
    Observador de Logs - Registra eventos en consola.
    Similar a un sistema de logging a archivo.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    evento = "desconocido"

    if "datos" in datos:
        evento = "datos_actualizados"
    elif "timeout" in datos:
        evento = "timeout"
    elif "status" in datos:
        evento = f"error_{datos.get('status', 'unknown')}"

    # Simular escritura a archivo de log
    log_line = f"{timestamp} | EVENTO: {evento} | Ciclo: {datos.get('ciclo', 'N/A')}\n"

    # En una implementación real, escribiríamos a archivo:
    # with open("ecomarket.log", "a") as f:
    #     f.write(log_line)

    # Por ahora, solo mostramos en consola (silencioso)
    # print(f"[LOG] {log_line.strip()}")


def observador_errores(datos: Dict[str, Any]) -> None:
    """
    Observador de Errores - Maneja errores del servidor.
    Muestra mensajes de error amigables al usuario.
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n[{timestamp}] [ERROR HANDLER] ⚠️  Error detectado:")

    if "timeout" in datos:
        print(f"  └─> ⏱️ Timeout después de {datos.get('timeout', 'N/A')}s")
    elif "status" in datos:
        status = datos.get("status", 0)
        if status >= 500:
            print(f"  └─> 🔥 Error del servidor ({status})")
        else:
            print(f"  └─> ❌ Error del cliente ({status})")
    elif "error" in datos:
        print(f"  └─> 💥 {datos.get('error', 'Error desconocido')}")

    print(f"  └─> Ciclo #{datos.get('ciclo', 'N/A')}")
    print(f"  └─> Aplicando backoff...\n")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

async def main():
    """
    Función principal - Demostración del sistema de polling.

    Inicia el monitor, lo deja correr por unos ciclos, y luego lo detiene.
    """
    print("=" * 60)
    print("🌿 EcoMarket - Monitor de Inventario con Polling")
    print("=" * 60)
    print(f"URL: {BASE_URL}/productos")
    print(f"Intervalo base: {INTERVALO_BASE}s")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Intervalo máximo: {INTERVALO_MAX}s")
    print("=" * 60)
    print()

    # Crear instancia del servicio de polling
    monitor = ServicioPolling(f"{BASE_URL}/productos", INTERVALO_BASE)

    # Suscribir observadores
    print("📡 Suscribiendo observadores...")
    monitor.suscribir("datos_actualizados", observador_ui)
    monitor.suscribir("datos_actualizados", observador_alertas)
    monitor.suscribir("datos_actualizados", observador_logs)
    monitor.suscribir("sin_cambios", observador_logs)
    monitor.suscribir("error_servidor", observador_errores)
    monitor.suscribir("error_conexion", observador_errores)
    monitor.suscribir("timeout", observador_errores)
    print("✅ 4 observadores suscritos")
    print()

    # Iniciar polling en segundo plano
    print("▶️  Iniciando polling (Ctrl+C para detener)...")
    print("-" * 60)

    try:
        # Ejecutar por 30 segundos o 6 ciclos (lo que ocurra primero)
        tarea_polling = asyncio.create_task(monitor.iniciar())

        # Esperar 30 segundos o hasta que el usuario presione Ctrl+C
        await asyncio.sleep(30)

        # Detener limpiamente
        print("\n" + "-" * 60)
        monitor.detener()

        # Esperar a que termine el ciclo actual
        await asyncio.wait_for(tarea_polling, timeout=10)

    except KeyboardInterrupt:
        print("\n\n🛑 Detención solicitada por usuario...")
        monitor.detener()
        try:
            await asyncio.wait_for(tarea_polling, timeout=10)
        except asyncio.TimeoutError:
            print("⚠️  La tarea no terminó a tiempo, forzando cancelación...")
            tarea_polling.cancel()
    except asyncio.TimeoutError:
        print("\n⏰ Tiempo máximo de ejecución alcanzado")

    # Mostrar estadísticas finales
    print("\n" + "=" * 60)
    print("📊 ESTADÍSTICAS FINALES")
    print("=" * 60)
    stats = monitor.obtener_estadisticas()
    for clave, valor in stats.items():
        print(f"  {clave}: {valor}")
    print("=" * 60)
    print("✅ Monitor detenido correctamente")


if __name__ == "__main__":
    # Ejecutar el loop de eventos
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa terminado por el usuario")
