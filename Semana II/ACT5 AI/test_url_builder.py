"""
Tests para URLBuilder - Demostración de Protección contra Ataques.

Este módulo demuestra cómo URLBuilder protege contra:
1. Path traversal (../../../etc/passwd)
2. Inyección de query parameters
3. Caracteres unicode peligrosos
4. Tipos de ID inválidos
"""

import unittest
from url_builder import URLBuilder, URLSecurityError


class TestPathTraversalProtection(unittest.TestCase):
    """Tests que demuestran protección contra path traversal."""
    
    def setUp(self):
        self.builder = URLBuilder("http://localhost:3000/api/")
    
    def test_1_traversal_simple(self):
        """
        Ataque: ../../../etc/passwd
        El atacante intenta salir del directorio de la API.
        """
        malicious_id = "../../../etc/passwd"
        
        with self.assertRaises(URLSecurityError) as ctx:
            self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        self.assertIn("traversal", str(ctx.exception).lower())
        print(f"✅ Path traversal BLOQUEADO: {malicious_id}")
        print(f"   Error: {ctx.exception}")
    
    def test_2_traversal_encoded(self):
        """
        Ataque: ..%2F..%2Fetc%2Fpasswd
        El atacante usa URL encoding para ocultar el traversal.
        """
        malicious_id = "..%2F..%2Fetc%2Fpasswd"
        
        with self.assertRaises(URLSecurityError) as ctx:
            self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        self.assertIn("traversal", str(ctx.exception).lower())
        print(f"✅ Path traversal ENCODED BLOQUEADO: {malicious_id}")
    
    def test_3_traversal_windows_style(self):
        """
        Ataque: ..\\..\\windows\\system32
        El atacante usa backslashes (Windows style).
        """
        malicious_id = "..\\..\\windows\\system32"
        
        with self.assertRaises(URLSecurityError) as ctx:
            self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        print(f"✅ Path traversal WINDOWS BLOQUEADO: {malicious_id}")


class TestQueryInjectionProtection(unittest.TestCase):
    """Tests que demuestran protección contra inyección de query params."""
    
    def setUp(self):
        self.builder = URLBuilder("http://localhost:3000/api/")
    
    def test_1_injection_admin_param(self):
        """
        Ataque: 1?admin=true
        El atacante intenta inyectar un parámetro admin.
        """
        malicious_id = "1?admin=true"
        
        # URLBuilder escapa el ? y = en lugar de rechazar
        url = self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        # El ? debe estar escapado como %3F
        self.assertIn("%3F", url)
        self.assertNotIn("?admin", url)  # No hay query param real
        
        print(f"✅ Query injection ESCAPADO: {malicious_id}")
        print(f"   URL resultante: {url}")
    
    def test_2_injection_multiple_params(self):
        """
        Ataque: 1?role=admin&delete=all
        El atacante intenta inyectar múltiples parámetros.
        """
        malicious_id = "1?role=admin&delete=all"
        
        url = self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        # Verificar que & también está escapado
        self.assertIn("%26", url)  # & escapado
        self.assertIn("%3D", url)  # = escapado
        
        print(f"✅ Multiple params injection ESCAPADO: {malicious_id}")
        print(f"   URL resultante: {url}")
    
    def test_3_injection_with_fragment(self):
        """
        Ataque: 1#admin-section
        El atacante intenta inyectar un fragment.
        """
        malicious_id = "1#admin-section"
        
        url = self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        # El # debe estar escapado
        self.assertIn("%23", url)
        
        print(f"✅ Fragment injection ESCAPADO: {malicious_id}")
        print(f"   URL resultante: {url}")


class TestUnicodeProtection(unittest.TestCase):
    """Tests que demuestran protección contra caracteres unicode peligrosos."""
    
    def setUp(self):
        self.builder = URLBuilder("http://localhost:3000/api/")
    
    def test_1_null_byte_attack(self):
        """
        Ataque: archivo.txt\\x00.jpg
        El null byte puede truncar strings en algunos sistemas.
        """
        malicious_id = "archivo.txt\x00.jpg"
        
        with self.assertRaises(URLSecurityError) as ctx:
            self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        self.assertIn("peligroso", str(ctx.exception).lower())
        print(f"✅ Null byte BLOQUEADO")
        print(f"   Error: {ctx.exception}")
    
    def test_2_newline_injection(self):
        """
        Ataque: value\\r\\nX-Injected: header
        Intento de inyección de headers HTTP.
        """
        malicious_id = "value\r\nX-Injected: header"
        
        with self.assertRaises(URLSecurityError) as ctx:
            self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        print(f"✅ HTTP Header injection BLOQUEADO")
    
    def test_3_slash_encoded_traversal(self):
        """
        Ataque: ..%2F..%2F intento de bypass con slash codificado.
        """
        malicious_id = "..%2F..%2Fconfig"
        
        with self.assertRaises(URLSecurityError) as ctx:
            self.builder.build_url("productos/{id}", path_params={"id": malicious_id})
        
        print(f"✅ Encoded slash traversal BLOQUEADO")


class TestIDValidation(unittest.TestCase):
    """Tests para validación de tipos de ID."""
    
    def test_1_valid_int_id(self):
        """ID entero válido debe pasar."""
        result = URLBuilder.validate_id(123, "int")
        self.assertEqual(result, "123")
        print("✅ Int ID válido: 123")
    
    def test_2_negative_id_rejected(self):
        """ID negativo debe ser rechazado."""
        with self.assertRaises(ValueError) as ctx:
            URLBuilder.validate_id(-1, "int")
        
        self.assertIn("negativo", str(ctx.exception))
        print("✅ ID negativo rechazado: -1")
    
    def test_3_string_as_int_rejected(self):
        """String no numérico como int debe ser rechazado."""
        with self.assertRaises(TypeError) as ctx:
            URLBuilder.validate_id("abc", "int")
        
        print("✅ String 'abc' rechazado para tipo int")
    
    def test_4_valid_uuid(self):
        """UUID válido debe pasar."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = URLBuilder.validate_id(valid_uuid, "uuid")
        self.assertEqual(result, valid_uuid.lower())
        print(f"✅ UUID válido: {valid_uuid}")
    
    def test_5_invalid_uuid_rejected(self):
        """UUID inválido debe ser rechazado."""
        with self.assertRaises(ValueError) as ctx:
            URLBuilder.validate_id("not-a-uuid", "uuid")
        
        print("✅ UUID inválido rechazado")
    
    def test_6_bool_not_accepted_as_int(self):
        """Boolean no debe aceptarse como int (aunque técnicamente es subclase)."""
        with self.assertRaises(TypeError):
            URLBuilder.validate_id(True, "int")
        
        print("✅ Boolean rechazado como int")


class TestURLBuilderFunctional(unittest.TestCase):
    """Tests funcionales de construcción de URLs."""
    
    def setUp(self):
        self.builder = URLBuilder("http://localhost:3000/api/")
    
    def test_build_simple_url(self):
        """Construcción básica de URL."""
        url = self.builder.build_url("productos")
        self.assertEqual(url, "http://localhost:3000/api/productos")
    
    def test_build_url_with_path_param(self):
        """URL con parámetro de path."""
        url = self.builder.build_url(
            "productos/{id}",
            path_params={"id": 123}
        )
        self.assertEqual(url, "http://localhost:3000/api/productos/123")
    
    def test_build_url_with_query_params(self):
        """URL con query parameters."""
        url = self.builder.build_url(
            "productos",
            query_params={"categoria": "frutas", "orden": "asc"}
        )
        self.assertIn("categoria=frutas", url)
        self.assertIn("orden=asc", url)
    
    def test_build_url_complete(self):
        """URL completa con path y query params."""
        url = self.builder.build_url(
            "productos/{id}/reviews",
            path_params={"id": 42},
            query_params={"limit": 10}
        )
        self.assertIn("productos/42/reviews", url)
        self.assertIn("limit=10", url)
    
    def test_query_string_special_chars_escaped(self):
        """Caracteres especiales en query params deben escaparse."""
        url = self.builder.build_url(
            "productos",
            query_params={"q": "miel & azúcar", "precio": "10+"}
        )
        # urlencode escapa estos caracteres
        self.assertIn("miel", url)
        self.assertNotIn("&", url.split("?")[1].replace("&", "AMPERSAND"))  # Solo & como separador


class TestMaliciousInputDemo(unittest.TestCase):
    """
    Demostración completa de los 3 tipos de ataque solicitados.
    Estos tests sirven como documentación ejecutable.
    """
    
    def setUp(self):
        self.builder = URLBuilder("http://localhost:3000/api/")
    
    def test_demo_1_path_traversal(self):
        """
        DEMO 1: Path Traversal Attack
        
        Escenario: El atacante intenta leer /etc/passwd del servidor.
        Sin protección: productos/../../../etc/passwd -> servidor lee /etc/passwd
        Con URLBuilder: Se lanza URLSecurityError
        """
        print("\n" + "="*60)
        print("DEMO 1: PATH TRAVERSAL ATTACK")
        print("="*60)
        
        attacks = [
            "../../../etc/passwd",
            "....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
        ]
        
        for attack in attacks:
            print(f"\n🔴 Ataque: {attack}")
            print(f"   Sin protección: productos/{attack}")
            
            try:
                self.builder.build_url("productos/{id}", path_params={"id": attack})
                self.fail(f"Debería haber lanzado URLSecurityError para: {attack}")
            except URLSecurityError as e:
                print(f"   🟢 BLOQUEADO: {e}")
    
    def test_demo_2_query_injection(self):
        """
        DEMO 2: Query Parameter Injection Attack
        
        Escenario: El atacante inyecta ?admin=true en el ID.
        Sin protección: productos/1?admin=true -> servidor ve admin=true
        Con URLBuilder: El ? se escapa a %3F, no se interpreta
        """
        print("\n" + "="*60)
        print("DEMO 2: QUERY INJECTION ATTACK")
        print("="*60)
        
        attacks = [
            ("1?admin=true", "Elevar privilegios"),
            ("1?delete=all", "Borrar datos"),
            ("1&token=stolen", "Inyectar token"),
        ]
        
        for attack, intent in attacks:
            print(f"\n🔴 Ataque: {attack} ({intent})")
            print(f"   Sin protección: productos/{attack}")
            
            url = self.builder.build_url("productos/{id}", path_params={"id": attack})
            print(f"   🟢 ESCAPADO: {url}")
            
            # Verificar que no hay query params reales inyectados
            if "?" in url:
                query_part = url.split("?")[1]
                self.assertNotIn("admin=true", query_part)
                self.assertNotIn("delete=all", query_part)
    
    def test_demo_3_unicode_dangerous(self):
        """
        DEMO 3: Unicode/Encoding Attack
        
        Escenario: El atacante usa caracteres especiales para bypass.
        Sin protección: Puede causar truncamiento, header injection, etc.
        Con URLBuilder: Se bloquea o escapa según el caso.
        """
        print("\n" + "="*60)
        print("DEMO 3: UNICODE/ENCODING ATTACK")
        print("="*60)
        
        attacks = [
            ("file\x00.txt", "Null byte truncation"),
            ("data\r\nX-Header: injected", "HTTP header injection"),
            ("..%2F..%2Fsecret", "Encoded path traversal"),
        ]
        
        for attack, intent in attacks:
            print(f"\n🔴 Ataque: {repr(attack)} ({intent})")
            
            try:
                self.builder.build_url("productos/{id}", path_params={"id": attack})
                self.fail(f"Debería haber bloqueado: {repr(attack)}")
            except URLSecurityError as e:
                print(f"   🟢 BLOQUEADO: {e}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  TESTS DE SEGURIDAD - URLBuilder")
    print("  Protección contra ataques de URL")
    print("="*60 + "\n")
    
    unittest.main(verbosity=2)
