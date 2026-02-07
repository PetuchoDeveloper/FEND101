
import unittest
import logging
import time
from unittest.mock import MagicMock, patch
from io import StringIO
from ecomarket_client import EcoMarketClient, EcoMarketApiError

class TestObservability(unittest.TestCase):
    
    def setUp(self):
        # Capturar logs en un buffer
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s|%(message)s') # Formato simple para facil assert
        self.handler.setFormatter(formatter)
        
        # Configurar logger del cliente
        self.logger = logging.getLogger("EcoMarketClient")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = [self.handler] # Reemplazar handlers existentes
        
        self.client = EcoMarketClient(token="secret_token_123")

    @patch('requests.Session.request')
    def test_log_success_info(self, mock_req):
        """Prueba que un request exitoso genere log INFO."""
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        resp.headers = {'Content-Type': 'application/json'}
        mock_req.return_value = resp
        
        self.client.listar_productos()
        
        logs = self.log_capture.getvalue()
        # print(f"DEBUG LOGS: {logs}")
        
        self.assertIn("INFO|GET", logs)
        self.assertIn("Status: 200", logs)
        self.assertNotIn("secret_token_123", logs) # Security check

    @patch('requests.Session.request')
    def test_log_error_security(self, mock_req):
        """Prueba que un error 401 genere log WARNING/ERROR y oculte token."""
        resp = MagicMock()
        resp.status_code = 401
        resp.json.return_value = {"mensaje": "Unauthorized"}
        resp.headers = {}
        mock_req.return_value = resp
        
        try:
            self.client.listar_productos()
        except EcoMarketApiError:
            pass
            
        logs = self.log_capture.getvalue()
        
        # Check level (Mapped to ERROR because it raised an exception)
        self.assertIn("ERROR|GET", logs)
        self.assertIn("Status: 401", logs)
        # Check security masking
        # Python dict string representation uses single quotes
        self.assertIn("'Authorization': '******'", logs)

    @patch('time.time')
    @patch('requests.Session.request')
    def test_log_slow_request(self, mock_req, mock_time):
        """Prueba que una petición lenta genere WARNING."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = []
        mock_req.return_value = resp
        
        # Mock time.time to simulate 3 seconds duration
        # side_effect: start_time, end_time
        mock_time.side_effect = [1000.0, 1003.0] 
        
        self.client.listar_productos()
        
        logs = self.log_capture.getvalue()
        
        # Should be WARNING because duration > 2000ms
        self.assertIn("WARNING|GET", logs)
        self.assertIn("Time: 3000.00ms", logs)

if __name__ == '__main__':
    unittest.main()
