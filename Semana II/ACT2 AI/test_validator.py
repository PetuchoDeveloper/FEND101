import unittest
from validadores import validar_producto

class TestValidator(unittest.TestCase):
    def setUp(self):
        # Base válida para modificar en los tests
        self.base_valid_product = {
            "id": 42,
            "nombre": "Miel orgánica",
            "precio": 150.00,
            "categoria": "miel",
            "productor": {
                "id": 7,
                "nombre": "Apiarios del Valle"
            },
            "disponible": true if 'true' == 'True' else True, # Python bool literal
            "creado_en": "2024-01-15T10:30:00Z"
        }

    def test_valid_json(self):
        """Prueba un JSON completamente válido"""
        self.assertTrue(validar_producto(self.base_valid_product))

    def test_missing_field(self):
        """Caso 1: Falta de Campo Requerido (id)"""
        data = self.base_valid_product.copy()
        del data["id"]
        with self.assertRaisesRegex(ValueError, "Falta el campo requerido: id"):
            validar_producto(data)

    def test_wrong_type(self):
        """Caso 2: Tipo de Dato Incorrecto (precio como string)"""
        data = self.base_valid_product.copy()
        data["precio"] = "150.00"
        with self.assertRaisesRegex(ValueError, "El campo 'precio' debe ser float o int"):
            validar_producto(data)

    def test_negative_price(self):
        """Caso 3: Violación de Regla de Negocio (Precio Negativo)"""
        data = self.base_valid_product.copy()
        data["precio"] = -50.00
        with self.assertRaisesRegex(ValueError, "El precio debe ser positivo"):
            validar_producto(data)

    def test_invalid_category(self):
        """Caso 4: Categoría Inválida"""
        data = self.base_valid_product.copy()
        data["categoria"] = "electrónica"
        with self.assertRaisesRegex(ValueError, "Categoría inválida"):
            validar_producto(data)

    def test_invalid_date(self):
        """Caso 5: Formato de Fecha Inválido"""
        data = self.base_valid_product.copy()
        data["creado_en"] = "2024/01/15"
        with self.assertRaisesRegex(ValueError, "Formato de fecha inválido"):
            validar_producto(data)

    def test_malformed_nested_object(self):
        """Caso 6: Objeto anidado malformado (falta id en productor)"""
        data = self.base_valid_product.copy()
        # Deep copy manual simple para modificar el dict anidado sin afectar self.base_valid_product
        data["productor"] = { "nombre": "Apiarios Sin ID" } 
        with self.assertRaisesRegex(ValueError, "El campo 'productor.id' es requerido"):
            validar_producto(data)

if __name__ == '__main__':
    unittest.main()
