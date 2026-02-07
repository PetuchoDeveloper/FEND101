"""
Tests para validación de respuestas del cliente EcoMarket.
Estos tests verifican que el cliente detecta respuestas inválidas del servidor.
"""

import unittest
from validadores import (
    validar_producto,
    validar_lista_productos,
    ValidationError,
    CATEGORIAS_VALIDAS
)


class TestValidacionFallida(unittest.TestCase):
    """Tests que verifican que la validación falla correctamente."""
    
    def test_1_precio_negativo(self):
        """
        Test 1: Precio negativo debe lanzar ValidationError.
        Escenario: El servidor devuelve un producto con precio -5.00
        """
        producto_invalido = {
            "id": 1,
            "nombre": "Producto Corrupto",
            "precio": -5.00,  # ❌ Precio negativo
            "categoria": "frutas"
        }
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(producto_invalido)
        
        # Verificar que el mensaje es descriptivo
        self.assertIn("precio", str(ctx.exception).lower())
        self.assertIn("mayor a 0", str(ctx.exception))
        print(f"✅ Test 1 pasó: {ctx.exception}")
    
    
    def test_2_categoria_invalida(self):
        """
        Test 2: Categoría no permitida debe lanzar ValidationError.
        Escenario: El servidor devuelve categoría 'electronica' (no existe en EcoMarket)
        """
        producto_invalido = {
            "id": 2,
            "nombre": "iPhone Falso",
            "precio": 999.99,
            "categoria": "electronica"  # ❌ Categoría no válida
        }
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(producto_invalido)
        
        self.assertIn("categoria", str(ctx.exception).lower())
        self.assertIn("electronica", str(ctx.exception))
        print(f"✅ Test 2 pasó: {ctx.exception}")
    
    
    def test_3_campo_requerido_faltante(self):
        """
        Test 3: Campo requerido 'nombre' faltante debe lanzar ValidationError.
        Escenario: El servidor devuelve un producto sin nombre
        """
        producto_invalido = {
            "id": 3,
            # "nombre" falta ❌
            "precio": 15.00,
            "categoria": "verduras"
        }
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(producto_invalido)
        
        self.assertIn("nombre", str(ctx.exception).lower())
        self.assertIn("requerido", str(ctx.exception).lower())
        print(f"✅ Test 3 pasó: {ctx.exception}")
    
    
    def test_4_tipo_incorrecto_id_string(self):
        """
        Test 4: ID como string en lugar de int debe lanzar ValidationError.
        Escenario: El servidor devuelve id="abc" en lugar de id=123
        """
        producto_invalido = {
            "id": "abc",  # ❌ Debe ser int
            "nombre": "Producto X",
            "precio": 20.00,
            "categoria": "lacteos"
        }
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(producto_invalido)
        
        self.assertIn("id", str(ctx.exception).lower())
        self.assertIn("int", str(ctx.exception).lower())
        print(f"✅ Test 4 pasó: {ctx.exception}")
    
    
    def test_5_productor_estructura_invalida(self):
        """
        Test 5: Campo productor con estructura incompleta debe fallar.
        Escenario: El servidor devuelve productor sin 'nombre'
        """
        producto_invalido = {
            "id": 5,
            "nombre": "Miel Artesanal",
            "precio": 80.00,
            "categoria": "miel",
            "productor": {
                "id": 100
                # "nombre" falta ❌
            }
        }
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(producto_invalido)
        
        self.assertIn("productor.nombre", str(ctx.exception))
        self.assertIn("requerido", str(ctx.exception).lower())
        print(f"✅ Test 5 pasó: {ctx.exception}")


class TestValidacionExitosa(unittest.TestCase):
    """Tests que verifican que productos válidos pasan la validación."""
    
    def test_producto_minimo_valido(self):
        """Producto con solo campos requeridos debe pasar."""
        producto = {
            "id": 1,
            "nombre": "Tomates Cherry",
            "precio": 12.50,
            "categoria": "verduras"
        }
        
        resultado = validar_producto(producto)
        self.assertEqual(resultado, producto)
        print("✅ Producto mínimo válido pasó")
    
    
    def test_producto_completo_valido(self):
        """Producto con todos los campos opcionales debe pasar."""
        producto = {
            "id": 2,
            "nombre": "Miel Pura",
            "precio": 95.00,
            "categoria": "miel",
            "disponible": True,
            "descripcion": "Miel 100% natural de abeja",
            "productor": {
                "id": 10,
                "nombre": "Apiarios del Valle"
            },
            "creado_en": "2024-01-15T10:30:00-05:00"
        }
        
        resultado = validar_producto(producto)
        self.assertEqual(resultado, producto)
        print("✅ Producto completo válido pasó")


class TestValidacionLista(unittest.TestCase):
    """Tests para validación de listas de productos."""
    
    def test_lista_con_producto_invalido(self):
        """Una lista con un producto inválido debe fallar indicando el índice."""
        lista = [
            {"id": 1, "nombre": "OK", "precio": 10.0, "categoria": "frutas"},
            {"id": 2, "nombre": "OK", "precio": 20.0, "categoria": "lacteos"},
            {"id": 3, "nombre": "MALO", "precio": -1.0, "categoria": "miel"},  # ❌
        ]
        
        with self.assertRaises(ValidationError) as ctx:
            validar_lista_productos(lista)
        
        # Debe indicar que el producto[2] falló
        self.assertIn("Producto[2]", str(ctx.exception))
        print(f"✅ Test lista con error pasó: {ctx.exception}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  TESTS DE VALIDACIÓN - EcoMarket Client")
    print("="*60 + "\n")
    
    unittest.main(verbosity=2)
