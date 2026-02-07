"""
Tests para el módulo de Retry

Demuestra el comportamiento de @with_retry con:
- Reintentos exitosos después de errores transitorios
- NO reintentos en errores 4xx
- Exponential backoff con jitter
- Exhaustión de reintentos
"""

import pytest
from unittest.mock import Mock, patch, call
import time

from retry import (
    with_retry,
    RetryConfig,
    RetryExhaustedError,
    ServerError,
    TimeoutError,
    ClientError,
    RetryableError,
    calculate_exponential_delay,
    apply_jitter,
    is_retryable_status,
    raise_for_status_with_retry,
)


# ============================================================
# TESTS DE CONFIGURACIÓN
# ============================================================

class TestRetryConfig:
    """Tests para la clase RetryConfig."""
    
    def test_config_default_values(self):
        """Verificar valores por defecto."""
        config = RetryConfig()
        
        assert config.max_retries == 4
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter_range == 0.25
        assert config.retry_on == (RetryableError,)
    
    def test_config_custom_values(self):
        """Verificar configuración personalizada."""
        config = RetryConfig(
            max_retries=10,
            base_delay=0.5,
            max_delay=30.0,
            jitter_range=0.5,
            retry_on=(ServerError, TimeoutError)
        )
        
        assert config.max_retries == 10
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.jitter_range == 0.5
        assert config.retry_on == (ServerError, TimeoutError)
    
    def test_config_invalid_max_retries(self):
        """max_retries no puede ser negativo."""
        with pytest.raises(ValueError, match="max_retries"):
            RetryConfig(max_retries=-1)
    
    def test_config_invalid_base_delay(self):
        """base_delay debe ser positivo."""
        with pytest.raises(ValueError, match="base_delay"):
            RetryConfig(base_delay=0)
    
    def test_config_invalid_max_delay(self):
        """max_delay debe ser >= base_delay."""
        with pytest.raises(ValueError, match="max_delay"):
            RetryConfig(base_delay=10, max_delay=5)
    
    def test_config_invalid_jitter_range(self):
        """jitter_range debe estar entre 0 y 1."""
        with pytest.raises(ValueError, match="jitter_range"):
            RetryConfig(jitter_range=1.5)


# ============================================================
# TESTS DE CÁLCULOS DE DELAY
# ============================================================

class TestDelayCalculations:
    """Tests para funciones de cálculo de delay."""
    
    def test_exponential_delay_sequence(self):
        """Verificar secuencia: 1s, 2s, 4s, 8s, 16s..."""
        delays = [
            calculate_exponential_delay(i, base_delay=1.0, max_delay=60.0)
            for i in range(5)
        ]
        
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]
    
    def test_exponential_delay_respects_max(self):
        """El delay no debe exceder max_delay."""
        delay = calculate_exponential_delay(10, base_delay=1.0, max_delay=10.0)
        
        assert delay == 10.0  # 2^10 = 1024, pero capped a 10
    
    def test_exponential_delay_custom_base(self):
        """Verificar con base_delay diferente."""
        delays = [
            calculate_exponential_delay(i, base_delay=0.5, max_delay=60.0)
            for i in range(4)
        ]
        
        assert delays == [0.5, 1.0, 2.0, 4.0]
    
    def test_jitter_zero_returns_original(self):
        """Sin jitter, el delay no cambia."""
        delay = apply_jitter(5.0, jitter_range=0)
        assert delay == 5.0
    
    def test_jitter_within_range(self):
        """Jitter debe estar dentro del rango esperado."""
        base_delay = 10.0
        jitter_range = 0.25
        
        # Ejecutar múltiples veces para verificar rango
        for _ in range(100):
            delay = apply_jitter(base_delay, jitter_range)
            
            min_expected = base_delay * (1 - jitter_range)  # 7.5
            max_expected = base_delay * (1 + jitter_range)  # 12.5
            
            assert min_expected <= delay <= max_expected
    
    def test_jitter_adds_randomness(self):
        """Verificar que jitter produce valores diferentes."""
        base_delay = 5.0
        jitter_range = 0.25
        
        delays = [apply_jitter(base_delay, jitter_range) for _ in range(20)]
        unique_delays = set(delays)
        
        # Debería haber variación (muy improbable que todos sean iguales)
        assert len(unique_delays) > 1


# ============================================================
# TESTS DEL DECORADOR - ÉXITO Y REINTENTOS
# ============================================================

class TestWithRetrySuccess:
    """Tests donde el retry eventualmente tiene éxito."""
    
    @patch('retry.time.sleep')
    def test_retry_on_500_eventually_succeeds(self, mock_sleep):
        """Éxito después de 2 errores 500."""
        mock_func = Mock(side_effect=[
            ServerError("Error 500", 500),
            ServerError("Error 502", 502),
            "success"
        ])
        
        @with_retry(max_retries=3, base_delay=1.0, jitter_range=0)
        def fetch():
            return mock_func()
        
        result = fetch()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2
    
    @patch('retry.time.sleep')
    def test_retry_on_503_service_unavailable(self, mock_sleep):
        """503 Service Unavailable se recupera."""
        mock_func = Mock(side_effect=[
            ServerError("Servicio no disponible", 503),
            "recovered"
        ])
        
        @with_retry(max_retries=3, base_delay=1.0, jitter_range=0)
        def call_service():
            return mock_func()
        
        result = call_service()
        
        assert result == "recovered"
        assert mock_func.call_count == 2
    
    @patch('retry.time.sleep')
    def test_retry_on_timeout(self, mock_sleep):
        """Timeout se reintenta automáticamente."""
        mock_func = Mock(side_effect=[
            TimeoutError("Connection timeout"),
            TimeoutError("Read timeout"),
            "finally connected"
        ])
        
        @with_retry(max_retries=4, base_delay=1.0, jitter_range=0)
        def slow_request():
            return mock_func()
        
        result = slow_request()
        
        assert result == "finally connected"
        assert mock_func.call_count == 3
    
    @patch('retry.time.sleep')
    def test_no_retry_needed_on_success(self, mock_sleep):
        """Si funciona a la primera, no hay retry."""
        mock_func = Mock(return_value="immediate success")
        
        @with_retry(max_retries=3)
        def working_function():
            return mock_func()
        
        result = working_function()
        
        assert result == "immediate success"
        assert mock_func.call_count == 1
        mock_sleep.assert_not_called()


# ============================================================
# TESTS DEL DECORADOR - NO REINTENTAR EN 4xx
# ============================================================

class TestNoRetryOn4xx:
    """Tests que verifican que NO se reintenta en errores 4xx."""
    
    @patch('retry.time.sleep')
    def test_no_retry_on_400_bad_request(self, mock_sleep):
        """400 Bad Request NO se reintenta."""
        mock_func = Mock(side_effect=ClientError("Datos inválidos", 400))
        
        @with_retry(max_retries=3, base_delay=1.0)
        def send_invalid_data():
            return mock_func()
        
        with pytest.raises(ClientError) as exc_info:
            send_invalid_data()
        
        assert exc_info.value.status_code == 400
        assert mock_func.call_count == 1  # Solo un intento
        mock_sleep.assert_not_called()
    
    @patch('retry.time.sleep')
    def test_no_retry_on_401_unauthorized(self, mock_sleep):
        """401 Unauthorized NO se reintenta."""
        mock_func = Mock(side_effect=ClientError("Token inválido", 401))
        
        @with_retry(max_retries=5)
        def access_protected_resource():
            return mock_func()
        
        with pytest.raises(ClientError) as exc_info:
            access_protected_resource()
        
        assert exc_info.value.status_code == 401
        assert mock_func.call_count == 1
    
    @patch('retry.time.sleep')
    def test_no_retry_on_404_not_found(self, mock_sleep):
        """404 Not Found NO se reintenta."""
        mock_func = Mock(side_effect=ClientError("Recurso no existe", 404))
        
        @with_retry(max_retries=3)
        def get_missing_resource():
            return mock_func()
        
        with pytest.raises(ClientError):
            get_missing_resource()
        
        assert mock_func.call_count == 1
    
    @patch('retry.time.sleep')
    def test_no_retry_on_422_validation_error(self, mock_sleep):
        """422 Validation Error NO se reintenta."""
        mock_func = Mock(side_effect=ClientError("Falló validación", 422))
        
        @with_retry(max_retries=3)
        def create_with_invalid_schema():
            return mock_func()
        
        with pytest.raises(ClientError):
            create_with_invalid_schema()
        
        assert mock_func.call_count == 1


# ============================================================
# TESTS DEL DECORADOR - EXHAUSTIÓN DE REINTENTOS
# ============================================================

class TestRetryExhaustion:
    """Tests cuando se agotan todos los reintentos."""
    
    @patch('retry.time.sleep')
    def test_max_retries_exhausted(self, mock_sleep):
        """Después de max_retries, lanza RetryExhaustedError."""
        mock_func = Mock(side_effect=ServerError("Servidor caído", 500))
        
        @with_retry(max_retries=3, base_delay=1.0, jitter_range=0)
        def always_fails():
            return mock_func()
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fails()
        
        error = exc_info.value
        assert error.attempts == 4  # 1 inicial + 3 reintentos
        assert isinstance(error.last_exception, ServerError)
        assert mock_func.call_count == 4
    
    @patch('retry.time.sleep')
    def test_zero_retries_fails_immediately(self, mock_sleep):
        """Con max_retries=0, solo hay un intento."""
        mock_func = Mock(side_effect=ServerError("Error", 500))
        
        @with_retry(max_retries=0, base_delay=1.0)
        def single_attempt():
            return mock_func()
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            single_attempt()
        
        assert exc_info.value.attempts == 1
        assert mock_func.call_count == 1
        mock_sleep.assert_not_called()


# ============================================================
# TESTS DE EXPONENTIAL BACKOFF TIMING
# ============================================================

class TestExponentialBackoffTiming:
    """Tests que verifican los tiempos de espera."""
    
    @patch('retry.time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        """Verificar delays: 1s, 2s, 4s (sin jitter)."""
        mock_func = Mock(side_effect=[
            ServerError("Error", 500),
            ServerError("Error", 500),
            ServerError("Error", 500),
            "success"
        ])
        
        @with_retry(max_retries=4, base_delay=1.0, jitter_range=0)
        def function_with_delays():
            return mock_func()
        
        function_with_delays()
        
        # Verificar los tiempos de sleep
        expected_delays = [1.0, 2.0, 4.0]  # 2^0, 2^1, 2^2
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        
        assert actual_delays == expected_delays
    
    @patch('retry.time.sleep')
    def test_max_delay_capping(self, mock_sleep):
        """El delay no debe exceder max_delay."""
        mock_func = Mock(side_effect=[
            ServerError("Error", 500),
            ServerError("Error", 500),
            ServerError("Error", 500),
            ServerError("Error", 500),
            "success"
        ])
        
        @with_retry(max_retries=5, base_delay=1.0, max_delay=3.0, jitter_range=0)
        def capped_delays():
            return mock_func()
        
        capped_delays()
        
        # Delays: 1s, 2s, 3s (capped), 3s (capped)
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        
        assert actual_delays == [1.0, 2.0, 3.0, 3.0]


# ============================================================
# TESTS DE JITTER
# ============================================================

class TestJitter:
    """Tests que verifican que jitter agrega variación."""
    
    @patch('retry.time.sleep')
    def test_jitter_applied(self, mock_sleep):
        """Jitter agrega variación a los delays."""
        mock_func = Mock(side_effect=[
            ServerError("Error", 500),
            ServerError("Error", 500),
            "success"
        ])
        
        @with_retry(max_retries=3, base_delay=10.0, jitter_range=0.25)
        def function_with_jitter():
            return mock_func()
        
        function_with_jitter()
        
        # Con jitter_range=0.25, los delays deben estar en ±25% del base
        # Delay 0: base=10, rango=[7.5, 12.5]
        # Delay 1: base=20, rango=[15, 25]
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        
        assert 7.5 <= delays[0] <= 12.5
        assert 15.0 <= delays[1] <= 25.0
    
    @patch('retry.random.uniform')
    @patch('retry.time.sleep')
    def test_jitter_uses_random(self, mock_sleep, mock_random):
        """Verificar que se usa random.uniform para jitter."""
        mock_random.return_value = 0.1  # Simular +10% jitter
        mock_func = Mock(side_effect=[
            ServerError("Error", 500),
            "success"
        ])
        
        @with_retry(max_retries=2, base_delay=10.0, jitter_range=0.25)
        def check_random():
            return mock_func()
        
        check_random()
        
        # random.uniform debe llamarse con el rango de jitter
        mock_random.assert_called_with(-0.25, 0.25)


# ============================================================
# TESTS DE CALLBACK on_retry
# ============================================================

class TestOnRetryCallback:
    """Tests para el callback on_retry."""
    
    @patch('retry.time.sleep')
    def test_on_retry_called_before_each_retry(self, mock_sleep):
        """Callback se llama antes de cada reintento."""
        callback = Mock()
        mock_func = Mock(side_effect=[
            ServerError("Error 1", 500),
            ServerError("Error 2", 502),
            "success"
        ])
        
        @with_retry(max_retries=3, base_delay=1.0, jitter_range=0, on_retry=callback)
        def with_callback():
            return mock_func()
        
        with_callback()
        
        assert callback.call_count == 2
        
        # Verificar argumentos del callback
        first_call = callback.call_args_list[0]
        assert first_call[0][0] == 1  # attempt
        assert isinstance(first_call[0][1], ServerError)  # exception
        assert first_call[0][2] == 1.0  # delay


# ============================================================
# TESTS DE UTILIDADES
# ============================================================

class TestUtilities:
    """Tests para funciones utilitarias."""
    
    def test_is_retryable_status_5xx(self):
        """5xx son reintentables."""
        assert is_retryable_status(500) is True
        assert is_retryable_status(502) is True
        assert is_retryable_status(503) is True
        assert is_retryable_status(599) is True
    
    def test_is_retryable_status_4xx(self):
        """4xx NO son reintentables."""
        assert is_retryable_status(400) is False
        assert is_retryable_status(401) is False
        assert is_retryable_status(404) is False
        assert is_retryable_status(422) is False
    
    def test_is_retryable_status_2xx_3xx(self):
        """2xx y 3xx NO son reintentables (no son errores)."""
        assert is_retryable_status(200) is False
        assert is_retryable_status(201) is False
        assert is_retryable_status(301) is False
    
    def test_raise_for_status_server_error(self):
        """raise_for_status lanza ServerError para 5xx."""
        with pytest.raises(ServerError) as exc_info:
            raise_for_status_with_retry(500, "Internal Server Error")
        
        assert exc_info.value.status_code == 500
    
    def test_raise_for_status_client_error(self):
        """raise_for_status lanza ClientError para 4xx."""
        with pytest.raises(ClientError) as exc_info:
            raise_for_status_with_retry(404, "Not Found")
        
        assert exc_info.value.status_code == 404


# ============================================================
# TESTS DE INTEGRACIÓN
# ============================================================

class TestIntegration:
    """Tests de integración con escenarios realistas."""
    
    @patch('retry.time.sleep')
    def test_realistic_http_scenario(self, mock_sleep):
        """Escenario: servidor sobrecargado durante deploy."""
        # Simula: 503, 503, 200 (servidor se recupera)
        responses = [
            ServerError("Deploy en progreso", 503),
            ServerError("Aún cargando", 503),
            {"status": "ok", "data": [1, 2, 3]}
        ]
        call_count = 0
        
        @with_retry(max_retries=5, base_delay=0.5, jitter_range=0.1)
        def fetch_data():
            nonlocal call_count
            response = responses[call_count]
            call_count += 1
            if isinstance(response, Exception):
                raise response
            return response
        
        result = fetch_data()
        
        assert result == {"status": "ok", "data": [1, 2, 3]}
        assert call_count == 3
    
    @patch('retry.time.sleep')
    def test_mixed_errors_only_retries_5xx(self, mock_sleep):
        """Mix de errores: 500 se reintenta, 400 falla inmediato."""
        mock_func = Mock()
        
        # Primero función que falla con 500, luego éxito
        @with_retry(max_retries=3, base_delay=1.0, jitter_range=0)
        def success_after_500():
            return mock_func()
        
        # Función que falla con 400
        @with_retry(max_retries=3, base_delay=1.0)
        def fails_with_400():
            raise ClientError("Bad Request", 400)
        
        # Test 500 → éxito
        mock_func.side_effect = [ServerError("Error", 500), "ok"]
        result = success_after_500()
        assert result == "ok"
        assert mock_func.call_count == 2
        
        # Test 400 → falla inmediato
        with pytest.raises(ClientError):
            fails_with_400()


# ============================================================
# EJECUTAR TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
