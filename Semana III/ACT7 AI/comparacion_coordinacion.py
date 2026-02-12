"""
Benchmarking de Estrategias de Coordinación Asíncrona para EcoMarket Dashboard
==============================================================================

Este script compara 4 estrategias de coordinación de tareas asíncronas:
1. asyncio.gather() - Esperar a que TODAS terminen
2. asyncio.wait(return_when=FIRST_COMPLETED) - Procesar conforme llegan
3. asyncio.as_completed() - Iterar por orden de completación
4. asyncio.wait(return_when=FIRST_EXCEPTION) - Abortar ante primer error

Autor: Antigravity AI
Fecha: 12 de febrero de 2026
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
import json


# ==============================================================================
# SIMULACIÓN DE ENDPOINTS DE ECOMARKET
# ==============================================================================

@dataclass
class EndpointConfig:
    """Configuración de un endpoint simulado."""
    nombre: str
    latencia_ms: int
    probabilidad_error: float = 0.0
    tipo_error: str = "timeout"


class SimuladorEndpoints:
    """Simula endpoints de API con latencias y errores configurables."""
    
    def __init__(self, escenario: str = "normal"):
        self.escenarios = {
            "normal": {
                "productos": EndpointConfig("productos", 200, 0.0),
                "categorias": EndpointConfig("categorias", 100, 0.0),
                "perfil": EndpointConfig("perfil", 500, 0.0),
                "notificaciones": EndpointConfig("notificaciones", 300, 0.0),
            },
            "timeout": {
                "productos": EndpointConfig("productos", 200, 0.0),
                "categorias": EndpointConfig("categorias", 100, 0.0),
                "perfil": EndpointConfig("perfil", 500, 0.0),
                "notificaciones": EndpointConfig("notificaciones", 10000, 1.0, "timeout"),
            },
            "error_rapido": {
                "productos": EndpointConfig("productos", 200, 0.0),
                "categorias": EndpointConfig("categorias", 100, 1.0, "server_error"),
                "perfil": EndpointConfig("perfil", 500, 0.0),
                "notificaciones": EndpointConfig("notificaciones", 300, 0.0),
            },
            "mixto": {
                "productos": EndpointConfig("productos", 150, 0.2, "connection_error"),
                "categorias": EndpointConfig("categorias", 80, 0.1, "timeout"),
                "perfil": EndpointConfig("perfil", 400, 0.0),
                "notificaciones": EndpointConfig("notificaciones", 250, 0.3, "server_error"),
            }
        }
        self.config = self.escenarios.get(escenario, self.escenarios["normal"])
    
    async def llamar_endpoint(self, nombre: str) -> Dict[str, Any]:
        """Simula una llamada a un endpoint."""
        if nombre not in self.config:
            raise ValueError(f"Endpoint desconocido: {nombre}")
        
        endpoint = self.config[nombre]
        
        # Simular latencia
        await asyncio.sleep(endpoint.latencia_ms / 1000)
        
        # Simular error si corresponde
        if endpoint.probabilidad_error > 0:
            import random
            if random.random() < endpoint.probabilidad_error:
                if endpoint.tipo_error == "timeout":
                    raise asyncio.TimeoutError(f"{nombre}: Timeout después de {endpoint.latencia_ms}ms")
                elif endpoint.tipo_error == "server_error":
                    raise Exception(f"{nombre}: Error 500 del servidor")
                elif endpoint.tipo_error == "connection_error":
                    raise ConnectionError(f"{nombre}: Error de conexión")
        
        # Retornar datos simulados
        return {
            "endpoint": nombre,
            "datos": f"Datos de {nombre}",
            "timestamp": time.time()
        }


# ==============================================================================
# MÉTRICAS DE RENDIMIENTO
# ==============================================================================

@dataclass
class MetricasEjecucion:
    """Métricas de una ejecución de estrategia."""
    estrategia: str
    tiempo_total_ms: float = 0.0
    tiempo_primer_dato_ms: float = None
    datos_exitosos: int = 0
    datos_fallidos: int = 0
    errores: List[str] = field(default_factory=list)
    orden_completacion: List[Tuple[str, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "estrategia": self.estrategia,
            "tiempo_total_ms": round(self.tiempo_total_ms, 2),
            "tiempo_primer_dato_ms": round(self.tiempo_primer_dato_ms, 2) if self.tiempo_primer_dato_ms else None,
            "datos_exitosos": self.datos_exitosos,
            "datos_fallidos": self.datos_fallidos,
            "tasa_exito": round(self.datos_exitosos / (self.datos_exitosos + self.datos_fallidos) * 100, 2) if (self.datos_exitosos + self.datos_fallidos) > 0 else 0,
            "errores": self.errores,
            "orden_completacion": [(nombre, round(tiempo_ms, 2)) for nombre, tiempo_ms in self.orden_completacion]
        }


# ==============================================================================
# ESTRATEGIA 1: asyncio.gather()
# ==============================================================================

async def estrategia_gather(simulador: SimuladorEndpoints, tolerante: bool = True) -> MetricasEjecucion:
    """
    Estrategia 1: Esperar a que TODAS las peticiones completen.
    
    Args:
        simulador: Simulador de endpoints
        tolerante: Si es True, usa return_exceptions=True
    """
    metricas = MetricasEjecucion(
        estrategia=f"gather({'tolerante' if tolerante else 'estricto'})"
    )
    
    inicio = time.time()
    
    endpoints = ["productos", "categorias", "perfil", "notificaciones"]
    
    try:
        if tolerante:
            resultados = await asyncio.gather(
                *[simulador.llamar_endpoint(ep) for ep in endpoints],
                return_exceptions=True
            )
            
            for i, resultado in enumerate(resultados):
                if isinstance(resultado, Exception):
                    metricas.datos_fallidos += 1
                    metricas.errores.append(f"{endpoints[i]}: {str(resultado)}")
                else:
                    metricas.datos_exitosos += 1
        else:
            resultados = await asyncio.gather(
                *[simulador.llamar_endpoint(ep) for ep in endpoints]
            )
            metricas.datos_exitosos = len(resultados)
    
    except Exception as e:
        metricas.datos_fallidos = len(endpoints)
        metricas.errores.append(f"Error global: {str(e)}")
    
    finally:
        tiempo_total = (time.time() - inicio) * 1000
        metricas.tiempo_total_ms = tiempo_total
        metricas.tiempo_primer_dato_ms = tiempo_total  # Todo llega al final
    
    return metricas


# ==============================================================================
# ESTRATEGIA 2: asyncio.wait(FIRST_COMPLETED)
# ==============================================================================

async def estrategia_first_completed(simulador: SimuladorEndpoints) -> MetricasEjecucion:
    """
    Estrategia 2: Procesar resultados conforme van llegando.
    """
    metricas = MetricasEjecucion(estrategia="wait_first_completed")
    
    inicio = time.time()
    
    tareas = {
        asyncio.create_task(simulador.llamar_endpoint(ep), name=ep)
        for ep in ["productos", "categorias", "perfil", "notificaciones"]
    }
    
    pending = tareas
    primer_dato = True
    
    while pending:
        done, pending = await asyncio.wait(
            pending,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for tarea in done:
            tiempo_actual = (time.time() - inicio) * 1000
            
            if primer_dato:
                metricas.tiempo_primer_dato_ms = tiempo_actual
                primer_dato = False
            
            try:
                resultado = tarea.result()
                metricas.datos_exitosos += 1
                metricas.orden_completacion.append((tarea.get_name(), tiempo_actual))
            except Exception as e:
                metricas.datos_fallidos += 1
                metricas.errores.append(f"{tarea.get_name()}: {str(e)}")
                metricas.orden_completacion.append((tarea.get_name(), tiempo_actual))
    
    metricas.tiempo_total_ms = (time.time() - inicio) * 1000
    
    return metricas


# ==============================================================================
# ESTRATEGIA 3: asyncio.as_completed()
# ==============================================================================

async def estrategia_as_completed(simulador: SimuladorEndpoints) -> MetricasEjecucion:
    """
    Estrategia 3: Iterar por orden de completación.
    """
    metricas = MetricasEjecucion(estrategia="as_completed")
    
    inicio = time.time()
    
    endpoints = ["productos", "categorias", "perfil", "notificaciones"]
    tareas = [
        asyncio.create_task(simulador.llamar_endpoint(ep), name=ep)
        for ep in endpoints
    ]
    
    primer_dato = True
    
    for tarea in asyncio.as_completed(tareas):
        tiempo_actual = (time.time() - inicio) * 1000
        
        if primer_dato:
            metricas.tiempo_primer_dato_ms = tiempo_actual
            primer_dato = False
        
        try:
            resultado = await tarea
            metricas.datos_exitosos += 1
            
            # Recuperar nombre de tarea
            nombre = None
            for t in tareas:
                if t == tarea:
                    nombre = t.get_name()
                    break
            
            metricas.orden_completacion.append((nombre or "unknown", tiempo_actual))
            
        except Exception as e:
            metricas.datos_fallidos += 1
            metricas.errores.append(f"Error: {str(e)}")
    
    metricas.tiempo_total_ms = (time.time() - inicio) * 1000
    
    return metricas


# ==============================================================================
# ESTRATEGIA 4: asyncio.wait(FIRST_EXCEPTION)
# ==============================================================================

async def estrategia_first_exception(simulador: SimuladorEndpoints) -> MetricasEjecucion:
    """
    Estrategia 4: Abortar inmediatamente ante el primer error.
    """
    metricas = MetricasEjecucion(estrategia="wait_first_exception")
    
    inicio = time.time()
    
    tareas = {
        asyncio.create_task(simulador.llamar_endpoint(ep), name=ep)
        for ep in ["productos", "categorias", "perfil", "notificaciones"]
    }
    
    try:
        done, pending = await asyncio.wait(
            tareas,
            return_when=asyncio.FIRST_EXCEPTION
        )
        
        # Verificar excepciones
        hubo_excepcion = False
        
        for tarea in done:
            try:
                resultado = tarea.result()
                metricas.datos_exitosos += 1
            except Exception as e:
                metricas.datos_fallidos += 1
                metricas.errores.append(f"{tarea.get_name()}: {str(e)}")
                hubo_excepcion = True
        
        if hubo_excepcion:
            # Cancelar tareas pendientes
            for tarea in pending:
                tarea.cancel()
            
            # Esperar cancelaciones
            await asyncio.gather(*pending, return_exceptions=True)
            
            metricas.datos_fallidos += len(pending)
            metricas.errores.append(f"Canceladas {len(pending)} tareas pendientes")
        
        else:
            # No hubo excepciones, esperar el resto
            if pending:
                más_resultados = await asyncio.gather(*pending, return_exceptions=True)
                for resultado in más_resultados:
                    if isinstance(resultado, Exception):
                        metricas.datos_fallidos += 1
                        metricas.errores.append(str(resultado))
                    else:
                        metricas.datos_exitosos += 1
    
    except Exception as e:
        metricas.errores.append(f"Error global: {str(e)}")
    
    finally:
        tiempo_total = (time.time() - inicio) * 1000
        metricas.tiempo_total_ms = tiempo_total
        metricas.tiempo_primer_dato_ms = tiempo_total  # Solo muestra al final (si no hay error)
    
    return metricas


# ==============================================================================
# BENCHMARKING Y ANÁLISIS
# ==============================================================================

async def ejecutar_benchmark(escenario: str, iteraciones: int = 5) -> Dict[str, List[MetricasEjecucion]]:
    """
    Ejecuta benchmark de todas las estrategias en un escenario.
    
    Args:
        escenario: Nombre del escenario a probar
        iteraciones: Número de veces a ejecutar cada estrategia
    """
    print(f"\n{'='*80}")
    print(f"🔬 BENCHMARK: Escenario '{escenario.upper()}' ({iteraciones} iteraciones)")
    print(f"{'='*80}\n")
    
    resultados = {
        "gather_tolerante": [],
        "gather_estricto": [],
        "first_completed": [],
        "as_completed": [],
        "first_exception": []
    }
    
    for i in range(iteraciones):
        print(f"  Iteración {i+1}/{iteraciones}...")
        
        # Ejecutar cada estrategia
        simulador = SimuladorEndpoints(escenario)
        resultados["gather_tolerante"].append(await estrategia_gather(simulador, tolerante=True))
        
        simulador = SimuladorEndpoints(escenario)
        resultados["gather_estricto"].append(await estrategia_gather(simulador, tolerante=False))
        
        simulador = SimuladorEndpoints(escenario)
        resultados["first_completed"].append(await estrategia_first_completed(simulador))
        
        simulador = SimuladorEndpoints(escenario)
        resultados["as_completed"].append(await estrategia_as_completed(simulador))
        
        simulador = SimuladorEndpoints(escenario)
        resultados["first_exception"].append(await estrategia_first_exception(simulador))
    
    return resultados


def analizar_resultados(resultados: Dict[str, List[MetricasEjecucion]]) -> None:
    """Analiza y muestra estadísticas de los resultados."""
    
    print(f"\n{'='*80}")
    print("📊 RESULTADOS DEL BENCHMARK")
    print(f"{'='*80}\n")
    
    # Tabla de resultados
    print(f"{'Estrategia':<25} | {'Tiempo Total (ms)':<20} | {'Primer Dato (ms)':<20} | {'Tasa Éxito':<12}")
    print("-" * 80)
    
    for nombre_estrategia, metricas_list in resultados.items():
        if not metricas_list:
            continue
        
        # Calcular estadísticas
        tiempos_totales = [m.tiempo_total_ms for m in metricas_list]
        tiempos_primer_dato = [m.tiempo_primer_dato_ms for m in metricas_list if m.tiempo_primer_dato_ms is not None]
        tasas_exito = [
            m.datos_exitosos / (m.datos_exitosos + m.datos_fallidos) * 100
            if (m.datos_exitosos + m.datos_fallidos) > 0 else 0
            for m in metricas_list
        ]
        
        tiempo_total_avg = statistics.mean(tiempos_totales)
        tiempo_primer_dato_avg = statistics.mean(tiempos_primer_dato) if tiempos_primer_dato else None
        tasa_exito_avg = statistics.mean(tasas_exito)
        
        print(
            f"{nombre_estrategia:<25} | "
            f"{tiempo_total_avg:>8.2f} ±{statistics.stdev(tiempos_totales) if len(tiempos_totales) > 1 else 0:>7.2f} | "
            f"{tiempo_primer_dato_avg:>8.2f} ±{statistics.stdev(tiempos_primer_dato) if tiempos_primer_dato and len(tiempos_primer_dato) > 1 else 0:>7.2f} | "
            f"{tasa_exito_avg:>10.2f}%"
        )
    
    print("\n")
    
    # Mostrar orden de completación (primera iteración)
    print("📈 Orden de Completación (primera iteración):")
    print("-" * 80)
    
    for nombre_estrategia, metricas_list in resultados.items():
        if metricas_list and metricas_list[0].orden_completacion:
            print(f"\n{nombre_estrategia}:")
            for endpoint, tiempo in metricas_list[0].orden_completacion:
                print(f"  {tiempo:>8.2f}ms - {endpoint}")


def guardar_resultados_json(resultados: Dict[str, List[MetricasEjecucion]], escenario: str) -> None:
    """Guarda los resultados en formato JSON."""
    datos_exportar = {
        "escenario": escenario,
        "timestamp": time.time(),
        "resultados": {}
    }
    
    for nombre_estrategia, metricas_list in resultados.items():
        datos_exportar["resultados"][nombre_estrategia] = [
            m.to_dict() for m in metricas_list
        ]
    
    nombre_archivo = f"benchmark_{escenario}_{int(time.time())}.json"
    
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos_exportar, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Resultados guardados en: {nombre_archivo}\n")


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

async def main():
    """Función principal del benchmark."""
    
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║  BENCHMARK DE ESTRATEGIAS DE COORDINACIÓN ASÍNCRONA - ECOMARKET DASHBOARD ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    escenarios = ["normal", "timeout", "error_rapido", "mixto"]
    
    for escenario in escenarios:
        resultados = await ejecutar_benchmark(escenario, iteraciones=3)
        analizar_resultados(resultados)
        guardar_resultados_json(resultados, escenario)
        
        # Pausa entre escenarios
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*80}")
    print("✅ BENCHMARK COMPLETADO")
    print(f"{'='*80}\n")
    
    print("""
💡 CONCLUSIONES:

1️⃣  GATHER (tolerante):
   ✅ Código más simple
   ❌ Usuario espera todo el tiempo (latencia percibida alta)
   📊 Buena opción si todos los datos son igualmente importantes

2️⃣  FIRST_COMPLETED:
   ✅ Actualización progresiva del UI
   ❌ Código más complejo con bucle while
   📊 Mejor experiencia de usuario

3️⃣  AS_COMPLETED (⭐ RECOMENDADO):
   ✅ Actualización progresiva con código más limpio que FIRST_COMPLETED
   ✅ Buen balance complejidad/rendimiento
   📊 Ideal para EcoMarket dashboard

4️⃣  FIRST_EXCEPTION:
   ✅ Cancela rápido ante errores críticos
   ❌ Puede desperdiciar trabajo ya iniciado
   📊 Útil cuando un error invalida todo el dashboard
    """)


if __name__ == "__main__":
    asyncio.run(main())
