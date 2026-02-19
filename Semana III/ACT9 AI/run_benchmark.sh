#!/bin/bash

# Script de ejecución completa del benchmark
# Este script automatiza todo el proceso: servidor mock + benchmark

echo "🔬 Iniciando Benchmark Completo: Sync vs Async"
echo "=============================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "benchmark_sync_vs_async.py" ]; then
    echo "❌ Error: Ejecuta este script desde ACT9 AI/"
    exit 1
fi

# Activar virtual environment si existe
if [ -d "venv" ]; then
    echo "📦 Activando virtual environment..."
    source venv/bin/activate
fi

# Verificar dependencias
echo "🔍 Verificando dependencias..."
python3 -c "import aiohttp, requests, matplotlib, tabulate, psutil" 2>/dev/null
if [  $? -ne 0 ]; then
    echo "⚠️ Instalando dependencias..."
    pip install -q -r requirements.txt
fi

# Iniciar servidor mock en background
echo "🚀 Iniciando servidor mock..."
python3 benchmark_mock_server.py > mock_server.log 2>&1 &
MOCK_PID=$!

# Esperar a que el servidor esté listo
sleep 2

# Verificar que el servidor está corriendo
curl -s http://127.0.0.1:8888/config > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: El servidor mock no se inició correctamente"
    kill $MOCK_PID 2>/dev/null
    exit 1
fi

echo "✅ Servidor mock corriendo (PID: $MOCK_PID)"

# Ejecutar benchmark
echo ""
echo "📊 Ejecutando benchmark..."
echo "=============================================="

python3 benchmark_sync_vs_async.py "$@"

BENCHMARK_EXIT=$?

# Detener servidor mock
echo ""
echo "🛑 Deteniendo servidor mock..."
kill $MOCK_PID 2>/dev/null
wait $MOCK_PID 2>/dev/null

if [ $BENCHMARK_EXIT -eq 0 ]; then
    echo "✅ Benchmark completado exitosamente"
    echo ""
    echo "📂 Archivos generados:"
    ls -lh benchmark_results.png recomendaciones.md 2>/dev/null | awk '{print "   - " $9 " (" $5 ")"}'
else
    echo "❌ El benchmark falló con código: $BENCHMARK_EXIT"
    exit $BENCHMARK_EXIT
fi
