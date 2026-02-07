
import unittest
from unittest.mock import patch, MagicMock
from ecomarket_client import EcoMarketClient, EcoMarketApiError, EcoMarketNetworkError, EcoMarketDataError
import requests

class TestEcoMarketClient(unittest.TestCase):
    
    def setUp(self):
        self.client = EcoMarketClient(base_url="https://api.test.com")

    @patch('requests.Session.request')
    def test_listar_productos_success(self, mock_request):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = [{"id": 1, "nombre": "Test"}]
        mock_request.return_value = mock_response

        # Call method
        productos = self.client.listar_productos()

        # Assertions
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0]["nombre"], "Test")
        mock_request.assert_called_with("GET", "https://api.test.com/productos", timeout=10, params={})

    @patch('requests.Session.request')
    def test_api_error_500(self, mock_request):
        # Setup mock response for 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "Internal Server Error"
        # json() might raise value error if html is returned
        mock_response.json.side_effect = ValueError("No JSON")
        mock_request.return_value = mock_response

        # Assert exception
        with self.assertRaises(EcoMarketApiError) as cm:
            self.client.listar_productos()
        
        self.assertIn("[500]", str(cm.exception))

    @patch('requests.Session.request')
    def test_timeout_error(self, mock_request):
        # Setup mock to raise timeout
        mock_request.side_effect = requests.exceptions.Timeout("Time's up!")

        # Assert exception
        with self.assertRaises(EcoMarketNetworkError):
            self.client.listar_productos()

if __name__ == '__main__':
    unittest.main()
