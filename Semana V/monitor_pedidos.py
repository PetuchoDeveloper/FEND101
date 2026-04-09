"""
DECISIONES DE DISEÑO — Cliente EcoMarket / Hito 1
==================================================
TIMEOUT_HTTP = 10s
  → Trade-off: Si el timeout es muy corto, fallarán peticiones lentas legítimas. Si es muy largo, el cliente queda bloqueado esperando.
    Decisión: 10s es adecuado para consultas de estado de pedidos que deberían responder rápidamente, previniendo congelamiento del cliente.

INTERVALO_POLLING_BASE = 5s
  → Trade-off: Menos datos obsoletos pero más peticiones y uso continuo de recursos/red.
    Decisión: 5s permite actualizaciones casi en tiempo real de los pedidos, importante para identificar retrasos sin saturar.

REINTENTOS_MAX = Infinito (con backoff hasta 60s)
  → Trade-off: Resiliencia ante caídas largas versus cerrar el worker.
    Decisión: Al ser un monitor de fondo, se mantiene reintentando pero con backoff y jitter para reducir carga.

JITTER EN BACKOFF:
  → Trade-off: Se agrega aleatoriedad al tiempo de espera (jitter). 
    Decisión: Esto beneficia al CLIENTE mitigando el problema de "Thundering Herd". Si múltiples clientes experimentan desconexiones, con tiempos de espera aleatorios no volverán a conectarse e intentar todo a la vez.

AUTOR: [Tu nombre]
FECHA: 2026-04-08
"""

import asyncio
import aiohttp
import json
import random
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
    pass

class ServidorNoDisponibleError(PollingError):
    pass

class DatosInvalidosError(PollingError):
    pass


# ============================================================
# CLASE OBSERVABLE
# ============================================================

class Observable:
    def __init__(self):
        self._observadores: Dict[str, List[Callable]] = {}

    def suscribir(self, evento: str, callback: Callable) -> None:
        if evento not in self._observadores:
            self._observadores[evento] = []
        self._observadores[evento].append(callback)
        self._log_evento(f"Nuevo observador suscrito a '{evento}'")

    def desuscribir(self, evento: str, callback: Callable) -> bool:
        if evento in self._observadores and callback in self._observadores[evento]:
            self._observadores[evento].remove(callback)
            self._log_evento(f"Observador removido de '{evento}'")
            return True
        return False

    def notificar(self, evento: str, datos: Any = None) -> None:
        if evento not in self._observadores:
            return
        for callback in self._observadores[evento]:
            try:
                callback(datos)
            except Exception as e:
                self._log_evento(f"ERROR: Observador falló en '{evento}': {e}")

    def _log_evento(self, mensaje: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [Observable] {mensaje}")


# ============================================================
# CLASE MONITOR DE PEDIDOS (Simulacro)
# ============================================================

class MonitorPedidos(Observable):
    def __init__(self, url: str, intervalo_base: int = INTERVALO_BASE):
        super().__init__()
        self.url = url
        self.intervalo_base = intervalo_base
        self.intervalo_actual = intervalo_base
        self.intervalo_max = INTERVALO_MAX

        self.ultimo_etag: Optional[str] = None
        self._activo = False
        self._session: Optional[aiohttp.ClientSession] = None

        self._ciclos = 0
        self._cambios_detectados = 0
        self._errores = 0

    async def iniciar(self) -> None:
        self._activo = True
        self._session = aiohttp.ClientSession()

        self._log(f"Monitor de Pedidos iniciado - URL: {self.url}")

        while self._activo:
            self._ciclos += 1
            self._log(f"=== Ciclo #{self._ciclos} | Intervalo: {self.intervalo_actual:.1f}s ===")

            try:
                await self._consultar_pedidos()
            except Exception as e:
                self._log(f"ERROR inesperado en ciclo: {e}")
                self._errores += 1

            if self._activo:
                await asyncio.sleep(self.intervalo_actual)

        if self._session:
            await self._session.close()
            self._session = None

        self._log("Monitor de Pedidos detenido limpiamente")

    async def _consultar_pedidos(self) -> None:
        if not self._session:
            raise ServidorNoDisponibleError("No hay sesión HTTP activa")

        try:
            headers = {}
            if self.ultimo_etag:
                headers["If-None-Match"] = self.ultimo_etag
                self._log(f"Enviando If-None-Match: {self.ultimo_etag}")

            timeout = aiohttp.ClientTimeout(total=TIMEOUT)
            async with self._session.get(self.url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    await self._manejar_200(response)
                elif response.status == 304:
                    self._manejar_304()
                elif response.status >= 500:
                    await self._manejar_5xx(response)
                elif response.status >= 400:
                    self._log(f"Error 4xx: {response.status} - No se reintenta")
                    self.notificar("error_cliente", {"status": response.status})
                else:
                    self._log(f"Status inesperado: {response.status}")

        except asyncio.TimeoutError:
            self._manejar_timeout()
        except aiohttp.ClientConnectorError as e:
            self._log(f"Error de conexión: {e}")
            self._errores += 1
            self.notificar("error_conexion", {"error": str(e)})
            self._aplicar_backoff()
        except Exception as e:
            self._log(f"Error inesperado al consultar pedidos: {e}")
            self._errores += 1

    async def _manejar_200(self, response: aiohttp.ClientResponse) -> None:
        self.ultimo_etag = response.headers.get("ETag")
        
        try:
            datos = await response.json()
            # Validación robusta del body en caso de estar malformado (Reto 4)
            if datos is None or "pedidos" not in datos or datos["pedidos"] is None:
                self._log("Respuesta 200 pero cuerpo malformado o sin pedidos")
                self.notificar("error_datos", {"error": "Formato de respuesta incorrecto"})
                return

            self.intervalo_actual = self.intervalo_base
            self._cambios_detectados += 1

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
        self._log("304 Not Modified - Sin cambios")
        self._aplicar_backoff()
        self.notificar("sin_cambios", {
            "ciclo": self._ciclos,
            "intervalo_actual": self.intervalo_actual,
            "timestamp": datetime.now().isoformat()
        })

    async def _manejar_5xx(self, response: aiohttp.ClientResponse) -> None:
        texto = await response.text()
        self._log(f"Error servidor {response.status}: {texto[:100]}")
        self._errores += 1

        self.notificar("error_servidor", {
            "status": response.status,
            "mensaje": texto[:200],
            "ciclo": self._ciclos
        })
        self._aplicar_backoff()

    def _manejar_timeout(self) -> None:
        self._log(f"TIMEOUT después de {TIMEOUT}s")
        self._errores += 1

        self.notificar("timeout", {
            "timeout": TIMEOUT,
            "ciclo": self._ciclos,
            "timestamp": datetime.now().isoformat()
        })
        self._aplicar_backoff()

    def _aplicar_backoff(self) -> None:
        nuevo_intervalo = self.intervalo_actual * BACKOFF_MULTIPLIER
        # Agregar jitter para mitigar el Thundering Herd (Reto 5)
        jitter = random.uniform(0, 2)
        self.intervalo_actual = min(nuevo_intervalo + jitter, self.intervalo_max)
        self._log(f"Backoff aplicado - Nuevo intervalo con jitter: {self.intervalo_actual:.1f}s")

    def detener(self) -> None:
        self._activo = False
        self._log("Señal de detención recibida - Terminando ciclo actual...")

    def _log(self, mensaje: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [MonitorPedidos] {mensaje}")


# ============================================================
# OBSERVADORES
# ============================================================

def observador_pedidos_ui(datos: Dict[str, Any]) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] [UI] 🖥️  Actualizando lista de pedidos...")

    if datos and "datos" in datos:
        data = datos["datos"]
        pedidos = data.get("pedidos", [])
        print(f"  └─> {len(pedidos)} pedidos totales (registrados: {data.get('total_registros')})")
        for p in pedidos:
            print(f"      • Pedido {p.get('id', 'N/A')}: {p.get('cliente', 'N/A')} - ${p.get('total', 0)} ({p.get('status', 'N/A')})")

    print(f"  └─> ETag: {datos.get('etag', 'N/A')}")
    print(f"  └─> Ciclo #{datos.get('ciclo', 'N/A')}\n")

def observador_pedidos_criticos(datos: Dict[str, Any]) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    if not datos or "datos" not in datos:
        return

    data = datos["datos"]
    pedidos = data.get("pedidos", [])
    alertas = []

    for p in pedidos:
        if p.get("status") == "RETRASADO":
            alertas.append(f"Pedido {p.get('id')} de {p.get('cliente')} por ${p.get('total')}")

    if alertas:
        print(f"\n[{timestamp}] [ALERTA] 🚨 Pedidos RETRASADOS detectados:")
        for alerta in alertas:
            print(f"  ⚠️  {alerta}")
        print()

def observador_errores(datos: Dict[str, Any]) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] [ERROR] ⚠️  Falla detectada:")
    if "timeout" in datos:
        print(f"  └─> Timeout ({datos.get('timeout')}s)")
    elif "status" in datos:
        print(f"  └─> HTTP {datos.get('status')}")
    elif "error" in datos:
        print(f"  └─> {datos.get('error')}")


# ============================================================
# EJECUCIÓN (Punto de entrada general)
# ============================================================

async def main():
    print("=" * 60)
    print("🌿 EcoMarket - Monitor de Pedidos Simulacro")
    print("=" * 60)

    monitor = MonitorPedidos(f"{BASE_URL}/pedidos", INTERVALO_BASE)
    
    monitor.suscribir("datos_actualizados", observador_pedidos_ui)
    monitor.suscribir("datos_actualizados", observador_pedidos_criticos)
    monitor.suscribir("error_servidor", observador_errores)
    monitor.suscribir("error_cliente", observador_errores)
    monitor.suscribir("error_conexion", observador_errores)
    monitor.suscribir("error_datos", observador_errores)
    monitor.suscribir("timeout", observador_errores)

    tarea_polling = asyncio.create_task(monitor.iniciar())

    try:
        # Simulando tiempo de ejecución en main
        await asyncio.sleep(15) 
        monitor.detener()
        await asyncio.wait_for(tarea_polling, timeout=10)
    except KeyboardInterrupt:
        monitor.detener()
        try:
            await asyncio.wait_for(tarea_polling, timeout=10)
        except asyncio.TimeoutError:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma terminado.")
