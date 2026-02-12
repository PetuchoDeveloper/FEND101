"""
Script de Demostración y Testing del Sistema de Throttling

Este script demuestra:
1. Creación de 50 productos con throttling
2. Monitoreo en tiempo real de peticiones en vuelo
3. Verificación de límites de concurrencia y rate
4. Generación de gráficas con matplotlib
5. Comparación con/sin throttling

Uso:
    python test_throttle_demo.py --test=full
    python test_throttle_demo.py --test=concurrency
    python test_throttle_demo.py --test=rate
"""

import asyncio
import aiohttp
import time
import argparse
from typing import List, Dict, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime

from throttle import (
    ThrottledClient,
    ConcurrencyLimiter,
    RateLimiter,
    crear_multiples_productos
)


# ============================================================
# DATACLASSES PARA MÉTRICAS
# ============================================================

@dataclass
class RequestMetric:
    """Métrica de una petición individual"""
    timestamp: float  # Tiempo desde inicio
    request_id: int
    in_flight_before: int  # Peticiones en vuelo antes de esta
    in_flight_after: int   # Peticiones en vuelo después de esta
    wait_time: float  # Tiempo esperado por rate limit
    duration: float  # Duración total de la petición
    success: bool


class ThrottleMonitor:
    """
    Monitor en tiempo real del sistema de throttling.
    
    Registra métricas de cada petición para análisis posterior.
    """
    
    def __init__(self):
        self.metrics: List[RequestMetric] = []
        self.start_time: float = 0
        self.requests_per_second: List[Tuple[float, int]] = []  # (timestamp, count)
        self._lock = asyncio.Lock()
        
    def start(self):
        """Inicia el monitoreo"""
        self.start_time = time.time()
        
    async def record_request(
        self,
        request_id: int,
        in_flight_before: int,
        in_flight_after: int,
        wait_time: float,
        duration: float,
        success: bool
    ):
        """Registra métricas de una petición"""
        async with self._lock:
            metric = RequestMetric(
                timestamp=time.time() - self.start_time,
                request_id=request_id,
                in_flight_before=in_flight_before,
                in_flight_after=in_flight_after,
                wait_time=wait_time,
                duration=duration,
                success=success
            )
            self.metrics.append(metric)
    
    def get_max_concurrent(self) -> int:
        """Retorna el máximo de peticiones concurrentes observadas"""
        if not self.metrics:
            return 0
        return max(m.in_flight_after for m in self.metrics)
    
    def get_requests_per_second_timeseries(self) -> List[Tuple[float, int]]:
        """
        Calcula peticiones por segundo en ventanas de 1 segundo.
        
        Returns:
            List[Tuple[float, int]]: Lista de (timestamp, count)
        """
        if not self.metrics:
            return []
        
        # Agrupar peticiones por segundo
        max_time = max(m.timestamp for m in self.metrics)
        buckets = {}
        
        for metric in self.metrics:
            second = int(metric.timestamp)
            buckets[second] = buckets.get(second, 0) + 1
        
        # Convertir a lista ordenada
        result = [(float(s), count) for s, count in sorted(buckets.items())]
        return result
    
    def get_in_flight_timeseries(self) -> List[Tuple[float, int]]:
        """
        Retorna serie temporal de peticiones en vuelo.
        
        Returns:
            List[Tuple[float, int]]: Lista de (timestamp, in_flight)
        """
        if not self.metrics:
            return []
        
        # Crear eventos de inicio y fin
        events = []
        for m in self.metrics:
            events.append((m.timestamp, 1))  # Inicio
            events.append((m.timestamp + m.duration, -1))  # Fin
        
        # Ordenar por tiempo
        events.sort(key=lambda x: x[0])
        
        # Calcular in_flight en cada punto
        timeseries = []
        current_in_flight = 0
        
        for timestamp, delta in events:
            current_in_flight += delta
            timeseries.append((timestamp, current_in_flight))
        
        return timeseries


# ============================================================
# FUNCIÓN DE TESTING CON MONITOREO
# ============================================================

async def test_throttled_creation_with_monitoring(
    num_productos: int = 50,
    max_concurrent: int = 10,
    max_per_second: float = 20
) -> Tuple[Dict, ThrottleMonitor]:
    """
    Crea productos con throttling y monitorea métricas.
    
    Returns:
        Tuple[Dict, ThrottleMonitor]: Resultados y monitor con métricas
    """
    print(f"\n{'='*70}")
    print(f"TEST: Creación de {num_productos} productos con throttling")
    print(f"{'='*70}")
    print(f"Configuración:")
    print(f"  • Max Concurrente: {max_concurrent}")
    print(f"  • Max por Segundo: {max_per_second}")
    print(f"  • Total Productos: {num_productos}")
    print(f"\nIniciando prueba...\n")
    
    monitor = ThrottleMonitor()
    monitor.start()
    
    inicio = time.time()
    
    async with ThrottledClient(max_concurrent, max_per_second) as client:
        # Crear tareas
        tareas = []
        
        for i in range(num_productos):
            producto = {
                "nombre": f"Producto Test {i+1}",
                "descripcion": f"Producto de prueba #{i+1}",
                "precio": 100 + i,
                "categoria": "test",
                "stock": 10
            }
            
            # Wrapper para capturar métricas
            async def crear_con_metricas(prod_data, req_id):
                inicio_req = time.time()
                in_flight_before = client.concurrency_limiter.in_flight
                
                try:
                    resultado = await client.crear_producto(prod_data)
                    success = True
                    return resultado
                except Exception as e:
                    success = False
                    raise
                finally:
                    duracion = time.time() - inicio_req
                    in_flight_after = client.concurrency_limiter.in_flight
                    wait_time = client.rate_limiter.average_wait_time
                    
                    await monitor.record_request(
                        request_id=req_id,
                        in_flight_before=in_flight_before,
                        in_flight_after=in_flight_after,
                        wait_time=wait_time,
                        duration=duracion,
                        success=success
                    )
            
            tareas.append(crear_con_metricas(producto, i))
        
        # Ejecutar todas las tareas
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        
        # Analizar resultados
        exitosos = [r for r in resultados if not isinstance(r, Exception)]
        errores = [r for r in resultados if isinstance(r, Exception)]
        
        tiempo_total = time.time() - inicio
        
        resultado = {
            'num_productos': num_productos,
            'exitosos': len(exitosos),
            'errores': len(errores),
            'tiempo_total': tiempo_total,
            'throughput': num_productos / tiempo_total,
            'max_concurrent_observed': monitor.get_max_concurrent(),
            'metrics': client.get_metrics()
        }
    
    return resultado, monitor


# ============================================================
# VISUALIZACIÓN CON MATPLOTLIB
# ============================================================

def plot_metrics(monitor: ThrottleMonitor, resultado: Dict, max_concurrent: int, max_per_second: float):
    """
    Genera gráficas de las métricas capturadas.
    
    Args:
        monitor: Monitor con métricas
        resultado: Diccionario de resultados
        max_concurrent: Límite configurado de concurrencia
        max_per_second: Límite configurado de rate
    """
    if not monitor.metrics:
        print("No hay métricas para graficar")
        return
    
    # Crear figura con 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle('Métricas de Control de Tráfico HTTP', fontsize=16, fontweight='bold')
    
    # ========================================
    # GRÁFICA 1: Peticiones en Vuelo vs Tiempo
    # ========================================
    in_flight_data = monitor.get_in_flight_timeseries()
    
    if in_flight_data:
        timestamps = [t for t, _ in in_flight_data]
        in_flight_counts = [count for _, count in in_flight_data]
        
        ax1.plot(timestamps, in_flight_counts, linewidth=1.5, color='#2E86AB', label='Peticiones en Vuelo')
        ax1.axhline(y=max_concurrent, color='red', linestyle='--', linewidth=2, label=f'Límite ({max_concurrent})')
        ax1.fill_between(timestamps, in_flight_counts, alpha=0.3, color='#2E86AB')
        
        ax1.set_xlabel('Tiempo (segundos)', fontsize=10)
        ax1.set_ylabel('Peticiones Concurrentes', fontsize=10)
        ax1.set_title('Peticiones en Vuelo vs Tiempo', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')
        
        # Destacar si se violó el límite
        max_observed = max(in_flight_counts)
        if max_observed > max_concurrent:
            ax1.text(
                0.5, 0.95,
                f'⚠️ LÍMITE EXCEDIDO: {max_observed} > {max_concurrent}',
                transform=ax1.transAxes,
                ha='center',
                va='top',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
                color='white',
                fontweight='bold'
            )
        else:
            ax1.text(
                0.5, 0.95,
                f'✅ Límite Respetado (max: {max_observed})',
                transform=ax1.transAxes,
                ha='center',
                va='top',
                bbox=dict(boxstyle='round', facecolor='green', alpha=0.7),
                color='white',
                fontweight='bold'
            )
    
    # ========================================
    # GRÁFICA 2: Peticiones por Segundo
    # ========================================
    rps_data = monitor.get_requests_per_second_timeseries()
    
    if rps_data:
        seconds = [s for s, _ in rps_data]
        counts = [c for _, c in rps_data]
        
        ax2.bar(seconds, counts, width=0.8, color='#A23B72', alpha=0.7, label='Peticiones/Segundo')
        ax2.axhline(y=max_per_second, color='red', linestyle='--', linewidth=2, label=f'Límite ({max_per_second}/s)')
        
        ax2.set_xlabel('Tiempo (segundos)', fontsize=10)
        ax2.set_ylabel('Peticiones por Segundo', fontsize=10)
        ax2.set_title('Rate de Peticiones por Segundo', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.legend(loc='upper right')
        
        # Verificar límite
        max_rps = max(counts)
        if max_rps > max_per_second:
            ax2.text(
                0.5, 0.95,
                f'⚠️ LÍMITE EXCEDIDO: {max_rps} > {max_per_second}',
                transform=ax2.transAxes,
                ha='center',
                va='top',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
                color='white',
                fontweight='bold'
            )
        else:
            ax2.text(
                0.5, 0.95,
                f'✅ Límite Respetado (max: {max_rps}/s)',
                transform=ax2.transAxes,
                ha='center',
                va='top',
                bbox=dict(boxstyle='round', facecolor='green', alpha=0.7),
                color='white',
                fontweight='bold'
            )
    
    # ========================================
    # GRÁFICA 3: Duración de Peticiones
    # ========================================
    request_ids = [m.request_id for m in monitor.metrics]
    durations = [m.duration for m in monitor.metrics]
    wait_times = [m.wait_time for m in monitor.metrics]
    
    ax3.scatter(request_ids, durations, alpha=0.6, s=30, color='#F18F01', label='Duración Total')
    ax3.scatter(request_ids, wait_times, alpha=0.6, s=20, color='#C73E1D', label='Tiempo de Espera')
    
    ax3.set_xlabel('ID de Petición', fontsize=10)
    ax3.set_ylabel('Tiempo (segundos)', fontsize=10)
    ax3.set_title('Duración y Tiempo de Espera por Petición', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper right')
    
    # Calcular estadísticas
    avg_duration = sum(durations) / len(durations) if durations else 0
    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
    
    stats_text = f'Promedio - Duración: {avg_duration:.3f}s | Espera: {avg_wait:.3f}s'
    ax3.text(
        0.5, 0.95,
        stats_text,
        transform=ax3.transAxes,
        ha='center',
        va='top',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
        fontsize=9
    )
    
    # Ajustar layout
    plt.tight_layout()
    
    # Guardar gráfica
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'throttle_metrics_{timestamp}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n📊 Gráfica guardada: {filename}")
    
    # Mostrar
    plt.show()


# ============================================================
# FUNCIÓN DE COMPARACIÓN SIN THROTTLING
# ============================================================

async def test_sin_throttling(num_productos: int = 50) -> Dict:
    """
    Crea productos SIN throttling para comparación.
    
    ADVERTENCIA: Esto puede sobrecargar el servidor!
    """
    print(f"\n{'='*70}")
    print(f"TEST: Creación de {num_productos} productos SIN throttling")
    print(f"{'='*70}")
    print("⚠️  ADVERTENCIA: Todas las peticiones se lanzan simultáneamente!")
    print()
    
    inicio = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Crear todas las peticiones sin límites
        tareas = []
        
        for i in range(num_productos):
            producto = {
                "nombre": f"Producto Test {i+1}",
                "descripcion": f"Producto de prueba #{i+1}",
                "precio": 100 + i,
                "categoria": "test",
                "stock": 10
            }
            
            async def crear_producto_raw(prod):
                url = f"http://localhost:3000/api/productos"
                async with session.post(url, json=prod) as response:
                    return await response.json()
            
            tareas.append(crear_producto_raw(producto))
        
        # ¡Todas a la vez!
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        
        exitosos = [r for r in resultados if not isinstance(r, Exception)]
        errores = [r for r in resultados if isinstance(r, Exception)]
        
        tiempo_total = time.time() - inicio
        
        return {
            'num_productos': num_productos,
            'exitosos': len(exitosos),
            'errores': len(errores),
            'tiempo_total': tiempo_total,
            'throughput': num_productos / tiempo_total if tiempo_total > 0 else 0
        }


# ============================================================
# REPORTE DE RESULTADOS
# ============================================================

def print_report(resultado: Dict, monitor: ThrottleMonitor, max_concurrent: int, max_per_second: float):
    """Imprime reporte detallado de resultados"""
    
    print(f"\n{'='*70}")
    print("REPORTE DE RESULTADOS")
    print(f"{'='*70}\n")
    
    # Resultados generales
    print("📊 Resultados Generales:")
    print(f"  • Total de Productos: {resultado['num_productos']}")
    print(f"  • Exitosos: {resultado['exitosos']} ✅")
    print(f"  • Errores: {resultado['errores']} ❌")
    print(f"  • Tiempo Total: {resultado['tiempo_total']:.2f}s")
    print(f"  • Throughput: {resultado['throughput']:.2f} peticiones/s")
    
    # Verificación de límites
    print(f"\n🔒 Verificación de Límites:")
    max_observed = resultado.get('max_concurrent_observed', 0)
    
    if max_observed <= max_concurrent:
        print(f"  ✅ Concurrencia: {max_observed}/{max_concurrent} (RESPETADO)")
    else:
        print(f"  ❌ Concurrencia: {max_observed}/{max_concurrent} (VIOLADO)")
    
    # Rate limiting
    rps_data = monitor.get_requests_per_second_timeseries()
    if rps_data:
        max_rps = max(count for _, count in rps_data)
        if max_rps <= max_per_second:
            print(f"  ✅ Rate Limit: {max_rps}/{max_per_second}/s (RESPETADO)")
        else:
            print(f"  ❌ Rate Limit: {max_rps}/{max_per_second}/s (VIOLADO)")
    
    # Métricas del cliente
    print(f"\n📈 Métricas del Cliente:")
    metrics = resultado['metrics']
    print(f"  • Total Requests: {metrics['total_requests']}")
    print(f"  • Successful: {metrics['successful_requests']}")
    print(f"  • Failed: {metrics['failed_requests']}")
    print(f"  • Average Wait Time: {metrics['average_wait_time']:.3f}s")
    
    print(f"\n{'='*70}\n")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

async def main():
    """Ejecuta los tests"""
    parser = argparse.ArgumentParser(description='Test de Sistema de Throttling')
    parser.add_argument(
        '--test',
        choices=['full', 'concurrency', 'rate', 'compare'],
        default='full',
        help='Tipo de test a ejecutar'
    )
    parser.add_argument('--num', type=int, default=50, help='Número de productos')
    parser.add_argument('--concurrent', type=int, default=10, help='Límite de concurrencia')
    parser.add_argument('--rate', type=float, default=20, help='Límite de rate (por segundo)')
    
    args = parser.parse_args()
    
    if args.test == 'full':
        # Test completo con gráficas
        resultado, monitor = await test_throttled_creation_with_monitoring(
            num_productos=args.num,
            max_concurrent=args.concurrent,
            max_per_second=args.rate
        )
        print_report(resultado, monitor, args.concurrent, args.rate)
        plot_metrics(monitor, resultado, args.concurrent, args.rate)
    
    elif args.test == 'compare':
        # Comparación con/sin throttling
        print("Ejecutando comparación...")
        
        # Con throttling
        print("\n1️⃣  CON THROTTLING:")
        resultado_throttled, monitor = await test_throttled_creation_with_monitoring(
            num_productos=args.num,
            max_concurrent=args.concurrent,
            max_per_second=args.rate
        )
        
        # Sin throttling
        print("\n2️⃣  SIN THROTTLING:")
        resultado_sin = await test_sin_throttling(num_productos=args.num)
        
        # Comparar
        print(f"\n{'='*70}")
        print("COMPARACIÓN")
        print(f"{'='*70}\n")
        
        print(f"                          CON Throttling    SIN Throttling")
        print(f"{'─'*70}")
        print(f"Tiempo Total:             {resultado_throttled['tiempo_total']:>7.2f}s         {resultado_sin['tiempo_total']:>7.2f}s")
        print(f"Throughput:               {resultado_throttled['throughput']:>7.2f}/s        {resultado_sin['throughput']:>7.2f}/s")
        print(f"Exitosos:                 {resultado_throttled['exitosos']:>7}           {resultado_sin['exitosos']:>7}")
        print(f"Errores:                  {resultado_throttled['errores']:>7}           {resultado_sin['errores']:>7}")
        
        print(f"\n💡 Conclusión:")
        if resultado_sin['errores'] > resultado_throttled['errores']:
            print("   El throttling previno errores causados por sobrecarga!")
        print("   El throttling garantiza uso controlado de recursos del servidor.")
        
        # Graficar throttled
        plot_metrics(monitor, resultado_throttled, args.concurrent, args.rate)
    
    else:
        print(f"Test '{args.test}' no implementado aún")


if __name__ == "__main__":
    asyncio.run(main())
