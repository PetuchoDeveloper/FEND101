# ACT8 AI - Suite de Pruebas Async para Cliente EcoMarket

## 📋 Descripción

Este proyecto implementa una **suite completa de 20 tests** usando `pytest + pytest-asyncio + aioresponses` para validar el cliente HTTP asíncrono de EcoMarket. Los tests cubren 4 categorías críticas:

1. **Equivalencia Funcional** (5 tests)
2. **Concurrencia Correcta** (5 tests)
3. **Timeouts y Cancelación** (5 tests)
4. **Edge Cases de Concurrencia** (5 tests)

## 📁 Estructura del Proyecto

```
ACT8 AI/
├── README.md                      # Este archivo
├── test_cliente_async.py          # Suite principal (20 tests)
├── conftest.py                    # Fixtures compartidos
├── pytest.ini                     # Configuración de pytest
├── requirements.txt               # Dependencias
├── cliente_ecomarket_async.py     # Módulo a testear (copiado de ACT3)
├── validadores.py                 # Validación de esquemas (copiado de ACT7)
├── url_builder.py                 # Constructor de URLs seguras (copiado de ACT3)
└── reporte_bugs.md                # Reporte de bugs encontrados (generado después de tests)
```

## 🚀 Instalación

```bash
cd "Semana III/ACT8 AI"
pip install -r requirements.txt
```

**Dependencias necesarias:**
- pytest==8.0.0
- pytest-asyncio==0.23.5
- aiohttp==3.9.3
- aioresponses==0.7.6

## 🧪 Ejecución de Tests

### Ejecutar Suite Completa

```bash
pytest -v test_cliente_async.py
```

### Ejecutar por Categoría

```bash
# Solo tests de equivalencia funcional
pytest -v -m funcional

# Solo tests de concurrencia
pytest -v -m concurrencia

# Solo tests de timeout/cancelación
pytest -v -m timeout

# Solo edge cases
pytest -v -m edge_case
```

### Ejecutar Test Específico

```bash
pytest -v test_cliente_async.py::test_gather_tres_peticiones_exitosas
```

### Generar Reporte de Coverage

```bash
pytest --cov=cliente_ecomarket_async --cov-report=html test_cliente_async.py
```

El reporte HTML se generará en `htmlcov/index.html`.

## 📊 Categorías de Tests

### 1️⃣ Equivalencia Funcional (5 tests)

Verifican que las funciones asíncronas retornan exactamente lo mismo que las síncronas.

- `test_listar_productos_async_vs_sync`: Estructura de respuesta idéntica
- `test_validacion_datos_productos`: Validación de esquema funciona igual
- `test_manejo_errores_http_401_403_500`: Errores HTTP se manejan igual
- `test_timeout_individual_respetado`: Timeout configurable por función
- `test_respuesta_malformada_json`: JSON inválido lanza excepción apropiada

### 2️⃣ Concurrencia Correcta (5 tests)

Prueban que `gather()`, semáforos y coordinación funcionan correctamente.

- `test_gather_tres_peticiones_exitosas`: 3 peticiones paralelas completan
- `test_gather_un_fallo_con_return_exceptions`: Manejo tolerante de errores
- `test_gather_sin_return_exceptions_propaga_error`: Modo estricto propaga errores
- `test_cargar_dashboard_un_fallo_de_cuatro`: Dashboard parcial funciona
- `test_semaforo_limita_concurrencia`: Límite de concurrencia respetado

### 3️⃣ Timeouts y Cancelación (5 tests)

Validan que timeouts individuales y cancelación en cadena funcionan correctamente.

- `test_timeout_individual_cancela_solo_peticion_lenta`: Timeout aislado
- `test_error_401_cancela_peticiones_en_cadena`: Cancelación en cadena por auth
- `test_timeout_global_dashboard_respetado`: Timeout global del dashboard
- `test_cancelled_error_no_deja_sesiones_abiertas`: Cleanup de recursos
- `test_peticion_cancelada_no_genera_log_errors`: Logs apropiados

### 4️⃣ Edge Cases de Concurrencia (5 tests)

Situaciones extremas y errores compuestos.

- `test_todas_peticiones_fallan_simultaneamente`: Todos los endpoints fallan
- `test_servidor_cierra_conexion_mitad_respuesta`: Connection reset
- `test_respuesta_llega_despues_del_timeout`: Respuesta tardía ignorada
- `test_dos_peticiones_mismo_endpoint`: Parámetros diferentes
- `test_sesion_cierra_correctamente_despues_gather_con_errores`: Cleanup con errores

## 🐛 Proceso de Testing y Bug Reporting

1. **Ejecutar tests**: `pytest -v test_cliente_async.py`
2. **Identificar fallos**: Revisar output de pytest
3. **Documentar en `reporte_bugs.md`**: Cada bug con reproducción y descripción
4. **Aplicar correcciones**: Modificar `cliente_ecomarket_async.py`
5. **Re-ejecutar tests**: Validar que los fixes funcionan
6. **Actualizar reporte**: Agregar sección "Corrección Aplicada"

## 📈 Métricas Esperadas

- **Coverage esperado**: > 85% del código del cliente async
- **Tests exitosos**: 20/20 si el código es correcto
- **Tiempo de ejecución**: < 5 segundos (con mocks)

## 💡 Ejemplos de Uso

### Ver Resultado de un Test

```bash
pytest -v test_cliente_async.py::test_gather_tres_peticiones_exitosas -s
```

### Ejecutar Solo Tests que Fallaron

```bash
pytest --lf  # last-failed
```

### Modo Verbose con Output Capturado

```bash
pytest -vv -s test_cliente_async.py
```

## 🔍 Interpretación de Resultados

- ✅ **PASSED**: Test exitoso, comportamiento correcto
- ❌ **FAILED**: Bug detectado, revisar traceback
- ⚠️ **XFAIL**: Fallo esperado (si se marcó con `@pytest.mark.xfail`)
- ⏭️ **SKIPPED**: Test omitido (si se marcó con `@pytest.mark.skip`)

## 📚 Referencias

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [aioresponses](https://github.com/pnuckowski/aioresponses)
- [aiohttp testing](https://docs.aiohttp.org/en/stable/testing.html)

---

**Autor**: Antigravity AI (QA Specialist)  
**Fecha**: 12 de febrero de 2026  
**Versión**: 1.0
