
import unittest
import requests
import threading
import time
from ecomarket_client import EcoMarketClient, EcoMarketApiError, EcoMarketNetworkError, EcoMarketDataError

# URL donde vive nuestro mock server (ecomarket_web.py)
CHAOS_URL = "http://localhost:5000/api/chaos"

class TestChaosScenarios(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Asumimos que el servidor ya está corriendo. 
        # En un entorno CI real, lo levantaríamos aquí con subprocess.
        pass

    def setUp(self):
        # Cliente con un timeout ligeramente mayor al delay de latencia pero menor al de timeout
        self.client = EcoMarketClient(base_url=CHAOS_URL, timeout=5)

    def test_01_latency(self):
        """Escenario 1: Red Lenta (3s delay)"""
        print("\n🐢 Probando Latencia...")
        start = time.time()
        # Pasamos el flag de caos via categoria
        prods = self.client.listar_productos(categoria="CHAOS:latency")
        duration = time.time() - start
        
        self.assertGreaterEqual(duration, 3.0)
        self.assertEqual(len(prods), 1)
        print(f"   Pasado (Duración: {duration:.2f}s)")

    def test_02_flaky(self):
        """Escenario 2: Servidor Intermitente (503)"""
        print("\n🎲 Probando Servidor Intermitente...")
        with self.assertRaises(EcoMarketApiError) as cm:
            self.client.listar_productos(categoria="CHAOS:flaky")
        
        self.assertEqual(cm.exception.status_code, 503)
        print(f"   Pasado (Capturó 503 Service Unavailable)")

    def test_03_truncated(self):
        """Escenario 3: Respuesta Truncada"""
        print("\n✂️ Probando JSON Truncado...")
        with self.assertRaises(EcoMarketDataError):
            self.client.listar_productos(categoria="CHAOS:truncated")
        print("   Pasado (Capturó JSON inválido)")

    def test_04_html_response(self):
        """Escenario 4: HTML Inesperado"""
        print("\n📄 Probando HTML Inesperado...")
        try:
            self.client.listar_productos(categoria="CHAOS:html")
        except EcoMarketDataError as e:
            print(f"   Pasado (Capturó error de datos: {e})")
        except Exception as e:
            self.fail(f"Debería haber lanzado EcoMarketDataError, pero lanzó {type(e)}")

    def test_05_timeout(self):
        """Escenario 5: Timeout (Server duerme 15s, cliente tiene 5s)"""
        print("\n⏱️ Probando Timeout...")
        start = time.time()
        with self.assertRaises(EcoMarketNetworkError):
            self.client.listar_productos(categoria="CHAOS:timeout")
        duration = time.time() - start
        
        # Debe haber cortado cerca de los 5s, no esperado a los 15s
        self.assertLess(duration, 10) 
        print(f"   Pasado (Abortó a los {duration:.2f}s)")

if __name__ == '__main__':
    print("="*60)
    print("EJECUTANDO SUITE DE CAOS")
    print("Asegúrate de que 'python ecomarket_web.py' esté corriendo en otra terminal")
    print("="*60)
    unittest.main()
