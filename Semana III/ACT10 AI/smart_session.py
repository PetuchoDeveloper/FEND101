"""
SmartSession: Enhanced aiohttp ClientSession with Connection Pool Monitoring

Este módulo implementa un wrapper inteligente sobre aiohttp.ClientSession que:
- Configura el TCPConnector con límites apropiados
- Monitorea el estado del pool en tiempo real
- Rastrea métricas de uso de conexiones
- Implementa health checks automáticos
- Funciona como drop-in replacement de ClientSession
"""

import asyncio
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import aiohttp
from aiohttp import TCPConnector


class ConnectionPoolStats:
    """Estadísticas del connection pool"""
    
    def __init__(self):
        self.connections_created = 0
        self.connections_reused = 0
        self.connections_closed = 0
        self.acquisition_times = []
        self._start_time = time.time()
    
    def record_new_connection(self):
        """Registra la creación de una nueva conexión TCP"""
        self.connections_created += 1
    
    def record_reused_connection(self):
        """Registra la reutilización de una conexión del pool"""
        self.connections_reused += 1
    
    def record_closed_connection(self):
        """Registra el cierre de una conexión"""
        self.connections_closed += 1
    
    def record_acquisition_time(self, duration: float):
        """Registra el tiempo que tomó adquirir una conexión"""
        self.acquisition_times.append(duration)
    
    def get_average_acquisition_time(self) -> float:
        """Calcula el tiempo promedio de adquisición"""
        if not self.acquisition_times:
            return 0.0
        return sum(self.acquisition_times) / len(self.acquisition_times)
    
    def get_uptime(self) -> float:
        """Retorna el tiempo de vida de la sesión en segundos"""
        return time.time() - self._start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte las estadísticas a diccionario"""
        return {
            "created": self.connections_created,
            "reused": self.connections_reused,
            "closed": self.connections_closed,
            "avg_acquisition_ms": round(self.get_average_acquisition_time() * 1000, 2),
            "uptime_sec": round(self.get_uptime(), 2)
        }


class SmartSession(aiohttp.ClientSession):
    """
    Extended ClientSession con monitoreo de connection pool.
    
    Funciona como drop-in replacement de aiohttp.ClientSession, pero añade:
    - Configuración explícita del TCPConnector
    - Monitoreo en tiempo real del pool
    - Métricas de uso de conexiones
    - Health checks periódicos
    
    Args:
        max_connections: Límite total de conexiones simultáneas (default: 100)
        max_connections_per_host: Límite de conexiones por host (default: 10)
        keepalive_timeout: Tiempo que las conexiones idle permanecen abiertas en segundos (default: 15)
        enable_monitoring: Habilita el monitoreo y logging (default: True)
        health_check_interval: Intervalo en segundos para health checks (default: 5.0)
        **kwargs: Argumentos adicionales para ClientSession
    
    Ejemplo:
        >>> async with SmartSession(max_connections=20) as session:
        ...     async with session.get('http://example.com') as resp:
        ...         data = await resp.json()
        ...     stats = session.get_pool_stats()
        ...     print(f"Conexiones activas: {stats['active']}")
    """
    
    def __init__(
        self,
        max_connections: int = 100,
        max_connections_per_host: int = 10,
        keepalive_timeout: float = 15.0,
        enable_monitoring: bool = True,
        health_check_interval: float = 5.0,
        **kwargs
    ):
        # Crear y configurar el TCPConnector
        connector = TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections_per_host,
            keepalive_timeout=keepalive_timeout,
            enable_cleanup_closed=True,  # Limpia conexiones cerradas automáticamente
            force_close=False,  # Permite keep-alive
            ttl_dns_cache=300  # Cache DNS por 5 minutos
        )
        
        # Inicializar la sesión base con el connector configurado
        super().__init__(connector=connector, **kwargs)
        
        # Configuración de monitoreo
        self._enable_monitoring = enable_monitoring
        self._health_check_interval = health_check_interval
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Almacenar configuración para referencia
        self._max_connections = max_connections
        self._max_connections_per_host = max_connections_per_host
        self._keepalive_timeout = keepalive_timeout
        
        # Estadísticas
        self._stats = ConnectionPoolStats()
        
        # Flag para detener health check
        self._closed = False
    
    async def __aenter__(self):
        """Context manager entry: inicia health check si está habilitado"""
        await super().__aenter__()
        
        if self._enable_monitoring:
            self._health_check_task = asyncio.create_task(self._run_health_check())
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: detiene health check y cierra la sesión"""
        self._closed = True
        
        # Cancelar health check si existe
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Cerrar la sesión base
        return await super().__aexit__(exc_type, exc_val, exc_tb)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Obtiene un snapshot del estado actual del connection pool.
        
        Returns:
            dict: {
                "active": Número de conexiones actualmente en uso,
                "idle": Número de conexiones disponibles en el pool,
                "total": Total de conexiones en el pool,
                "waiting": Número de requests esperando una conexión,
                "config": {
                    "max_connections": Límite configurado,
                    "max_per_host": Límite por host configurado,
                    "keepalive_timeout": Timeout configurado
                },
                "metrics": {
                    "created": Conexiones creadas (lifetime),
                    "reused": Conexiones reutilizadas (lifetime),
                    "closed": Conexiones cerradas (lifetime),
                    "avg_acquisition_ms": Tiempo promedio de adquisición en ms
                }
            }
        """
        connector = self.connector
        
        if not isinstance(connector, TCPConnector):
            return {"error": "Connector no es TCPConnector"}
        
        # Acceder al estado interno del connector
        # Nota: Esto usa APIs internas de aiohttp que pueden cambiar
        active = len(connector._acquired)  # Conexiones actualmente en uso
        
        # Calcular conexiones idle (disponibles en el pool)
        # El connector mantiene un pool de conexiones por host
        idle = 0
        for conns in connector._conns.values():
            idle += len(conns)
        
        total = active + idle
        
        # Calcular cuántos requests están esperando una conexión
        # Esto ocurre cuando active >= max_connections
        waiting = max(0, active - self._max_connections)
        
        return {
            "active": active,
            "idle": idle,
            "total": total,
            "waiting": waiting,
            "config": {
                "max_connections": self._max_connections,
                "max_per_host": self._max_connections_per_host,
                "keepalive_timeout": self._keepalive_timeout
            },
            "metrics": self._stats.to_dict()
        }
    
    async def print_pool_report(self):
        """
        Imprime un reporte formateado del estado del pool.
        
        Útil para debugging y monitoreo en tiempo real.
        """
        stats = self.get_pool_stats()
        
        print("\n┌─────────────────────────────────────────────────────────┐")
        print("│           Connection Pool Status Report                 │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│ Active Connections:       {stats['active']:>4} / {stats['config']['max_connections']:<4}              │")
        print(f"│ Idle Connections:         {stats['idle']:>4}                      │")
        print(f"│ Total Connections:        {stats['total']:>4}                      │")
        print(f"│ Waiting Requests:         {stats['waiting']:>4}                      │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│ Connections Created:      {stats['metrics']['created']:>4}                      │")
        print(f"│ Connections Reused:       {stats['metrics']['reused']:>4}                      │")
        print(f"│ Connections Closed:       {stats['metrics']['closed']:>4}                      │")
        print(f"│ Avg Acquisition Time:     {stats['metrics']['avg_acquisition_ms']:>6.2f} ms              │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│ Max per Host:             {stats['config']['max_per_host']:>4}                      │")
        print(f"│ Keep-Alive Timeout:       {stats['config']['keepalive_timeout']:>4.0f}s                     │")
        print(f"│ Uptime:                   {stats['metrics']['uptime_sec']:>6.1f}s                  │")
        print("└─────────────────────────────────────────────────────────┘\n")
    
    async def _run_health_check(self):
        """
        Task que se ejecuta periódicamente para monitorear el pool.
        
        Detecta:
        - Pool exhaustion (todas las conexiones en uso)
        - Posibles memory leaks (conexiones no liberadas)
        - Alto tiempo de adquisición (indica contención)
        """
        try:
            while not self._closed:
                await asyncio.sleep(self._health_check_interval)
                
                stats = self.get_pool_stats()
                
                # Detectar pool exhaustion
                if stats['active'] >= self._max_connections * 0.9:
                    print(f"⚠️  WARNING: Pool near exhaustion ({stats['active']}/{self._max_connections} connections in use)")
                
                # Detectar alto tiempo de adquisición (>100ms indica contención)
                avg_acq = stats['metrics']['avg_acquisition_ms']
                if avg_acq > 100:
                    print(f"⚠️  WARNING: High connection acquisition time ({avg_acq:.1f}ms)")
                
                # Detectar posible memory leak (muchas conexiones idle sin cerrarse)
                if stats['idle'] > self._max_connections * 0.5 and stats['active'] == 0:
                    print(f"⚠️  INFO: Many idle connections ({stats['idle']}) with no active requests")
        
        except asyncio.CancelledError:
            # Normal al cerrar la sesión
            pass
        except Exception as e:
            print(f"❌ ERROR in health check: {e}")
    
    @asynccontextmanager
    async def monitored_request(self, method: str, url: str, **kwargs):
        """
        Context manager que monitorea una petición individual.
        
        Ejemplo:
            >>> async with session.monitored_request('GET', 'http://example.com') as resp:
            ...     data = await resp.json()
        """
        start_time = time.time()
        
        # Realizar la petición usando el método base
        async with self.request(method, url, **kwargs) as response:
            # Registrar tiempo de adquisición
            acquisition_time = time.time() - start_time
            self._stats.record_acquisition_time(acquisition_time)
            
            # Inferir si la conexión fue reutilizada
            # (esto es una aproximación, aiohttp no expone esta info directamente)
            if acquisition_time < 0.01:  # <10ms sugiere reutilización
                self._stats.record_reused_connection()
            else:
                self._stats.record_new_connection()
            
            yield response


# Funciones de conveniencia para crear sesiones pre-configuradas

def create_high_concurrency_session(**kwargs) -> SmartSession:
    """
    Crea una sesión optimizada para alta concurrencia.
    
    Configuración:
    - 100 conexiones totales
    - 30 conexiones por host
    - Keep-alive de 30 segundos
    
    Ideal para: Dashboards, operaciones paralelas, batch processing
    """
    return SmartSession(
        max_connections=100,
        max_connections_per_host=30,
        keepalive_timeout=30.0,
        **kwargs
    )


def create_rate_limited_session(**kwargs) -> SmartSession:
    """
    Crea una sesión con límites conservadores.
    
    Configuración:
    - 20 conexiones totales
    - 5 conexiones por host
    - Keep-alive de 10 segundos
    
    Ideal para: APIs con rate limiting, recursos limitados
    """
    return SmartSession(
        max_connections=20,
        max_connections_per_host=5,
        keepalive_timeout=10.0,
        **kwargs
    )


def create_balanced_session(**kwargs) -> SmartSession:
    """
    Crea una sesión con configuración balanceada.
    
    Configuración:
    - 50 conexiones totales
    - 10 conexiones por host
    - Keep-alive de 15 segundos
    
    Ideal para: Uso general, aplicaciones típicas
    """
    return SmartSession(
        max_connections=50,
        max_connections_per_host=10,
        keepalive_timeout=15.0,
        **kwargs
    )
