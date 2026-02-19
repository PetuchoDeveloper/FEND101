"""
Visualización del Connection Pool en acción

Este script ejecuta 10 peticiones con un pool de 5 conexiones y
loggea cada evento para visualizar:
- Adquisición de conexiones
- Pool exhaustion (cola de espera)
- Reutilización de conexiones
- Liberación de conexiones
"""

import asyncio
import time
from smart_session import SmartSession


MOCK_SERVER_URL = "http://127.0.0.1:8888"
POOL_SIZE = 5
NUM_REQUESTS = 10


class PoolEventLogger:
    """Logger que registra eventos del connection pool"""
    
    def __init__(self):
        self.start_time = time.time()
        self.events = []
    
    def log(self, event: str):
        """Registra un evento con timestamp"""
        elapsed = time.time() - self.start_time
        timestamp = f"[{elapsed:>5.2f}s]"
        message = f"{timestamp} {event}"
        print(message)
        self.events.append((elapsed, event))
    
    def get_summary(self):
        """Retorna un resumen de los eventos"""
        return self.events


async def monitored_request(session: SmartSession, request_id: int, logger: PoolEventLogger):
    """
    Ejecuta una petición y loggea todos los eventos relevantes.
    """
    # Antes de la petición
    stats_before = session.get_pool_stats()
    logger.log(f"Request #{request_id:>2} → Intentando adquirir conexión (Pool: {stats_before['active']}/{POOL_SIZE} activas, {stats_before['idle']} idle)")
    
    if stats_before['active'] >= POOL_SIZE:
        logger.log(f"             ⏳ Request #{request_id:>2} ESPERANDO (pool exhausted)")
    
    start_time = time.time()
    
    try:
        async with session.get(
            f"{MOCK_SERVER_URL}/test",
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            await response.json()
            
            acquisition_time = time.time() - start_time
            stats_after = session.get_pool_stats()
            
            # Determinar si la conexión fue reutilizada
            is_reused = acquisition_time < 0.05  # <50ms sugiere reutilización
            conn_type = "REUTILIZADA" if is_reused else "nueva"
            
            logger.log(f"Request #{request_id:>2} → Conexión adquirida ({conn_type}, {acquisition_time*1000:.1f}ms)")
            
            # Simular procesamiento
            await asyncio.sleep(0.1)  # El server ya tiene delay, este es solo simbólico
            
            # Después de la petición
            logger.log(f"Request #{request_id:>2} → Completada, liberando conexión (vuelve al pool)")
    
    except Exception as e:
        logger.log(f"Request #{request_id:>2} → ❌ ERROR: {e}")


async def visualize_pool():
    """Ejecuta las peticiones y visualiza el comportamiento del pool"""
    
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║          Visualización de Connection Pool                 ║")
    print("║        10 Requests compartiendo 5 Conexiones              ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    logger = PoolEventLogger()
    
    async with SmartSession(
        max_connections=POOL_SIZE,
        max_connections_per_host=POOL_SIZE,
        enable_monitoring=False  # Deshabilitamos health check para no contaminar logs
    ) as session:
        
        logger.log(f"🚀 Iniciando {NUM_REQUESTS} peticiones concurrentes con pool de {POOL_SIZE} conexiones")
        logger.log("")
        
        # Lanzar todas las peticiones concurrentemente
        tasks = [
            monitored_request(session, i+1, logger)
            for i in range(NUM_REQUESTS)
        ]
        
        await asyncio.gather(*tasks)
        
        logger.log("")
        logger.log("✅ Todas las peticiones completadas")
        
        # Mostrar estadísticas finales
        print("\n")
        await session.print_pool_report()
        
        # Análisis
        stats = session.get_pool_stats()
        print("\n📊 Análisis del Comportamiento:")
        print(f"\n   Total de conexiones creadas:    {stats['metrics']['created']}")
        print(f"   Total de conexiones reutilizadas: {stats['metrics']['reused']}")
        print(f"   Total de peticiones:             {NUM_REQUESTS}")
        
        reuse_rate = (stats['metrics']['reused'] / NUM_REQUESTS * 100) if NUM_REQUESTS > 0 else 0
        print(f"\n   Tasa de reutilización:           {reuse_rate:.1f}%")
        
        if stats['metrics']['created'] <= POOL_SIZE:
            print(f"\n   ✅ Eficiencia perfecta: Se crearon solo {stats['metrics']['created']} conexiones")
            print(f"      para {NUM_REQUESTS} peticiones (límite de pool: {POOL_SIZE})")
        else:
            print(f"\n   ⚠️  Se crearon más conexiones de lo esperado ({stats['metrics']['created']} > {POOL_SIZE})")
        
        print("\n💡 Observaciones:")
        print(f"   - Las primeras {POOL_SIZE} peticiones adquieren conexiones nuevas")
        print(f"   - Las siguientes {NUM_REQUESTS - POOL_SIZE} peticiones esperan hasta que se libere una conexión")
        print(f"   - Keep-alive permite reutilizar conexiones sin overhead de TCP handshake")
        print(f"   - Sin keep-alive, cada petición requeriría ~3-way handshake (~10-50ms)")


async def main():
    """Función principal"""
    
    # Verificar servidor mock
    import aiohttp
    
    print("🔍 Verificando servidor mock...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MOCK_SERVER_URL}/config",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    print("✅ Servidor mock detectado\n")
    except:
        print("\n❌ ERROR: Servidor mock no disponible")
        print("\n   Ejecuta en otra terminal:")
        print("   cd 'Semana III/ACT9 AI'")
        print("   python benchmark_mock_server.py\n")
        return
    
    # Configurar delay del servidor a 100ms
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MOCK_SERVER_URL}/config",
                json={"latency_ms": 100},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    config = await response.json()
                    print(f"✅ Servidor configurado con {config['latency_ms']}ms delay\n")
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudo configurar delay del servidor: {e}\n")
    
    # Ejecutar visualización
    await visualize_pool()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Visualización interrumpida")
