#!/usr/bin/env python3
"""
Auditor de Contrato OpenAPI para Cliente EcoMarket

Este script analiza el contrato OpenAPI y verifica que el cliente Python
cumple con todos los requisitos del contrato.

Genera un reporte con:
- ✅ Conformidad: función cumple con endpoint
- ⚠️ Parcial: función no maneja algún código de respuesta
- ❌ Faltante: no hay función para endpoint

Uso:
    python auditar_contrato.py

Requisitos:
    pip install pyyaml
"""

import yaml
import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EndpointInfo:
    """Información de un endpoint del contrato OpenAPI."""
    path: str
    method: str
    operation_id: str
    summary: str
    description: str
    response_codes: Set[str]
    required_headers: Set[str]
    parameters: List[Dict]
    request_body: Optional[Dict]
    tags: List[str]


@dataclass
class FunctionInfo:
    """Información de una función del cliente."""
    name: str
    docstring: str
    http_method: Optional[str]
    endpoint_pattern: Optional[str]
    handled_codes: Set[str]
    has_json_header: bool
    has_schema_validation: bool
    line_number: int


@dataclass
class ConformityResult:
    """Resultado de verificación de conformidad."""
    status: str  # 'ok', 'partial', 'missing'
    endpoint: EndpointInfo
    function: Optional[FunctionInfo]
    missing_codes: Set[str]
    issues: List[str]


class OpenAPIParser:
    """Parser para archivos OpenAPI 3.x."""
    
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.spec: Dict = {}
        
    def parse(self) -> List[EndpointInfo]:
        """Parsea el archivo OpenAPI y extrae información de endpoints."""
        with open(self.spec_path, 'r', encoding='utf-8') as f:
            self.spec = yaml.safe_load(f)
        
        endpoints = []
        paths = self.spec.get('paths', {})
        
        for path, path_item in paths.items():
            # Obtener parámetros comunes del path
            common_params = path_item.get('parameters', [])
            
            for method in ['get', 'post', 'put', 'patch', 'delete']:
                if method not in path_item:
                    continue
                    
                operation = path_item[method]
                
                # Extraer códigos de respuesta
                response_codes = set(operation.get('responses', {}).keys())
                
                # Extraer headers requeridos
                required_headers = set()
                if operation.get('requestBody'):
                    content = operation['requestBody'].get('content', {})
                    if 'application/json' in content:
                        required_headers.add('Content-Type: application/json')
                
                # Combinar parámetros
                params = common_params + operation.get('parameters', [])
                
                endpoint = EndpointInfo(
                    path=path,
                    method=method.upper(),
                    operation_id=operation.get('operationId', ''),
                    summary=operation.get('summary', ''),
                    description=operation.get('description', ''),
                    response_codes=response_codes,
                    required_headers=required_headers,
                    parameters=params,
                    request_body=operation.get('requestBody'),
                    tags=operation.get('tags', [])
                )
                endpoints.append(endpoint)
        
        return endpoints


class ClientAnalyzer:
    """Analizador de código del cliente Python."""
    
    # Mapeo de métodos HTTP a patrones en docstrings
    HTTP_PATTERNS = {
        'GET': r'GET\s+(/\S+)',
        'POST': r'POST\s+(/\S+)',
        'PUT': r'PUT\s+(/\S+)',
        'PATCH': r'PATCH\s+(/\S+)',
        'DELETE': r'DELETE\s+(/\S+)',
    }
    
    def __init__(self, client_path: str):
        self.client_path = client_path
        self.source_code = ""
        self.tree: Optional[ast.AST] = None
        
    def parse(self) -> List[FunctionInfo]:
        """Parsea el archivo del cliente y extrae información de funciones."""
        with open(self.client_path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        
        self.tree = ast.parse(self.source_code)
        functions = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._analyze_function(node)
                if func_info:
                    functions.append(func_info)
        
        return functions
    
    def _analyze_function(self, node: ast.FunctionDef) -> Optional[FunctionInfo]:
        """Analiza una función y extrae su información."""
        # Ignorar funciones privadas/auxiliares
        if node.name.startswith('_'):
            return None
        
        docstring = ast.get_docstring(node) or ""
        
        # Detectar método HTTP y endpoint
        http_method = None
        endpoint_pattern = None
        
        for method, pattern in self.HTTP_PATTERNS.items():
            match = re.search(pattern, docstring)
            if match:
                http_method = method
                endpoint_pattern = match.group(1)
                break
        
        # Si no hay docstring con HTTP, no es una función de API
        if not http_method:
            return None
        
        # Analizar el cuerpo de la función
        handled_codes = self._find_handled_status_codes(node)
        has_json_header = self._check_json_header(node)
        has_schema_validation = self._check_schema_validation(node)
        
        return FunctionInfo(
            name=node.name,
            docstring=docstring,
            http_method=http_method,
            endpoint_pattern=endpoint_pattern,
            handled_codes=handled_codes,
            has_json_header=has_json_header,
            has_schema_validation=has_schema_validation,
            line_number=node.lineno
        )
    
    def _find_handled_status_codes(self, node: ast.FunctionDef) -> Set[str]:
        """Encuentra códigos de estado manejados en la función."""
        handled = set()
        source = ast.get_source_segment(self.source_code, node) or ""
        
        # Buscar comparaciones con status_code
        status_code_patterns = [
            r'status_code\s*==\s*(\d+)',
            r'status_code\s*!=\s*(\d+)',
            r'status_code\s*>=\s*(\d+)',
            r'== (\d{3})',
        ]
        
        for pattern in status_code_patterns:
            for match in re.finditer(pattern, source):
                code = match.group(1)
                handled.add(code)
                
                # Inferir rangos
                if code == '500':
                    handled.update(['500', '501', '502', '503', '504'])
                elif code == '400':
                    handled.update(['400', '401', '403', '404', '409'])
        
        # Buscar excepciones específicas lanzadas
        exception_patterns = {
            'ProductoNoEncontrado': '404',
            'ProductoDuplicado': '409',
            'HTTPValidationError': '400',
            'ServerError': '500',
        }
        
        for exc_name, code in exception_patterns.items():
            if exc_name in source:
                handled.add(code)
        
        return handled
    
    def _check_json_header(self, node: ast.FunctionDef) -> bool:
        """Verifica si la función envía Content-Type: application/json."""
        source = ast.get_source_segment(self.source_code, node) or ""
        return 'headers=HEADERS_JSON' in source or 'json=' in source
    
    def _check_schema_validation(self, node: ast.FunctionDef) -> bool:
        """Verifica si la función valida esquemas de respuesta."""
        source = ast.get_source_segment(self.source_code, node) or ""
        return '_validar_y_retornar' in source or 'validar_producto' in source


class ContractAuditor:
    """Auditor principal que compara contrato con implementación."""
    
    # Mapeo manual de operationId a nombres de función esperados
    OPERATION_TO_FUNCTION = {
        'listarProductos': 'listar_productos',
        'crearProducto': 'crear_producto',
        'obtenerProducto': 'obtener_producto',
        'actualizarProductoTotal': 'actualizar_producto_total',
        'actualizarProductoParcial': 'actualizar_producto_parcial',
        'eliminarProducto': 'eliminar_producto',
        'buscarProductos': 'buscar_productos',
        'listarProductosProductor': 'listar_productos_productor',
    }
    
    def __init__(self, spec_path: str, client_path: str):
        self.spec_parser = OpenAPIParser(spec_path)
        self.client_analyzer = ClientAnalyzer(client_path)
        self.endpoints: List[EndpointInfo] = []
        self.functions: List[FunctionInfo] = []
        
    def audit(self) -> List[ConformityResult]:
        """Ejecuta la auditoría completa."""
        self.endpoints = self.spec_parser.parse()
        self.functions = self.client_analyzer.parse()
        
        results = []
        
        for endpoint in self.endpoints:
            result = self._check_endpoint_conformity(endpoint)
            results.append(result)
        
        return results
    
    def _check_endpoint_conformity(self, endpoint: EndpointInfo) -> ConformityResult:
        """Verifica conformidad de un endpoint específico."""
        # Buscar función correspondiente
        expected_func = self.OPERATION_TO_FUNCTION.get(endpoint.operation_id)
        func = self._find_function(endpoint, expected_func)
        
        if not func:
            return ConformityResult(
                status='missing',
                endpoint=endpoint,
                function=None,
                missing_codes=endpoint.response_codes,
                issues=[f"No existe función para {endpoint.method} {endpoint.path}"]
            )
        
        # Verificar manejo de códigos de respuesta
        missing_codes = set()
        issues = []
        
        for code in endpoint.response_codes:
            if not self._code_is_handled(code, func.handled_codes):
                missing_codes.add(code)
        
        # Verificar headers para operaciones con body
        if endpoint.request_body and not func.has_json_header:
            issues.append("No envía header Content-Type: application/json")
        
        # Verificar validación de esquema
        if not func.has_schema_validation:
            issues.append("No valida esquema de respuesta")
        
        # Determinar estado
        if missing_codes or issues:
            return ConformityResult(
                status='partial',
                endpoint=endpoint,
                function=func,
                missing_codes=missing_codes,
                issues=issues
            )
        
        return ConformityResult(
            status='ok',
            endpoint=endpoint,
            function=func,
            missing_codes=set(),
            issues=[]
        )
    
    def _find_function(self, endpoint: EndpointInfo, expected_name: Optional[str]) -> Optional[FunctionInfo]:
        """Busca la función correspondiente a un endpoint."""
        if expected_name:
            for func in self.functions:
                if func.name == expected_name:
                    return func
        
        # Buscar por método y patrón de endpoint
        for func in self.functions:
            if func.http_method == endpoint.method:
                if self._endpoint_matches(endpoint.path, func.endpoint_pattern):
                    return func
        
        return None
    
    def _endpoint_matches(self, spec_path: str, func_pattern: Optional[str]) -> bool:
        """Verifica si un patrón de endpoint coincide."""
        if not func_pattern:
            return False
        
        # Normalizar paths
        spec_normalized = re.sub(r'\{[^}]+\}', '{id}', spec_path)
        func_normalized = re.sub(r'\{[^}]+\}', '{id}', func_pattern)
        
        return spec_normalized == func_normalized
    
    def _code_is_handled(self, code: str, handled: Set[str]) -> bool:
        """Verifica si un código está manejado."""
        if code in handled:
            return True
        
        # Verificar si se manejan rangos
        code_int = int(code)
        if code_int >= 500 and '500' in handled:
            return True
        if code_int >= 400 and code_int < 500:
            if '400' in handled and code not in ['401', '404', '409']:
                return True
        
        return False


class ReportGenerator:
    """Generador de reportes de auditoría."""
    
    def __init__(self, results: List[ConformityResult], output_path: str):
        self.results = results
        self.output_path = output_path
    
    def generate_markdown(self) -> str:
        """Genera reporte en formato Markdown."""
        lines = [
            "# Reporte de Auditoría de Contrato API",
            "",
            f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Resumen",
            "",
        ]
        
        # Contar por estado
        ok_count = sum(1 for r in self.results if r.status == 'ok')
        partial_count = sum(1 for r in self.results if r.status == 'partial')
        missing_count = sum(1 for r in self.results if r.status == 'missing')
        total = len(self.results)
        
        lines.extend([
            f"| Estado | Cantidad | Porcentaje |",
            f"|--------|----------|------------|",
            f"| ✅ Conformidad | {ok_count} | {ok_count/total*100:.1f}% |",
            f"| ⚠️ Parcial | {partial_count} | {partial_count/total*100:.1f}% |",
            f"| ❌ Faltante | {missing_count} | {missing_count/total*100:.1f}% |",
            f"| **Total** | **{total}** | **100%** |",
            "",
            "---",
            "",
            "## Detalle por Endpoint",
            "",
        ])
        
        # Ordenar: faltantes primero, luego parciales, luego ok
        sorted_results = sorted(self.results, 
            key=lambda r: {'missing': 0, 'partial': 1, 'ok': 2}[r.status])
        
        for result in sorted_results:
            lines.extend(self._format_result(result))
            lines.append("")
        
        # Sección de acciones requeridas
        lines.extend([
            "---",
            "",
            "## Acciones Requeridas",
            "",
        ])
        
        if missing_count > 0:
            lines.append("### Funciones Faltantes")
            lines.append("")
            for r in self.results:
                if r.status == 'missing':
                    func_name = self._suggest_function_name(r.endpoint)
                    lines.append(f"- [ ] Implementar `{func_name}()` para `{r.endpoint.method} {r.endpoint.path}`")
            lines.append("")
        
        if partial_count > 0:
            lines.append("### Mejoras Requeridas")
            lines.append("")
            for r in self.results:
                if r.status == 'partial':
                    for issue in r.issues:
                        lines.append(f"- [ ] `{r.function.name}()`: {issue}")
                    if r.missing_codes:
                        codes = ', '.join(sorted(r.missing_codes))
                        lines.append(f"- [ ] `{r.function.name}()`: Manejar códigos {codes}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _format_result(self, result: ConformityResult) -> List[str]:
        """Formatea un resultado individual."""
        status_emoji = {'ok': '✅', 'partial': '⚠️', 'missing': '❌'}[result.status]
        status_text = {'ok': 'Conformidad', 'partial': 'Parcial', 'missing': 'Faltante'}[result.status]
        
        lines = [
            f"### {status_emoji} {result.endpoint.method} {result.endpoint.path}",
            "",
            f"**operationId:** `{result.endpoint.operation_id}`",
            f"**Estado:** {status_text}",
        ]
        
        if result.function:
            lines.append(f"**Función:** `{result.function.name}()` (línea {result.function.line_number})")
        
        # Códigos de respuesta esperados
        codes = ', '.join(sorted(result.endpoint.response_codes))
        lines.append(f"**Códigos esperados:** {codes}")
        
        if result.missing_codes:
            missing = ', '.join(sorted(result.missing_codes))
            lines.append(f"**Códigos no manejados:** {missing}")
        
        if result.issues:
            lines.append("")
            lines.append("**Problemas:**")
            for issue in result.issues:
                lines.append(f"- {issue}")
        
        return lines
    
    def _suggest_function_name(self, endpoint: EndpointInfo) -> str:
        """Sugiere un nombre de función basado en el endpoint."""
        # Usar operationId convertido a snake_case
        op_id = endpoint.operation_id
        # Convertir camelCase a snake_case
        name = re.sub(r'([A-Z])', r'_\1', op_id).lower().lstrip('_')
        return name
    
    def save(self):
        """Guarda el reporte en un archivo."""
        content = self.generate_markdown()
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📝 Reporte guardado en: {self.output_path}")


def main():
    """Función principal del auditor."""
    # Determinar rutas
    script_dir = Path(__file__).parent
    spec_path = script_dir / "openapi.yaml"
    client_path = script_dir / "cliente_ecomarket.py"
    report_path = script_dir / "reporte_contrato.md"
    
    print("🔍 Auditor de Contrato OpenAPI")
    print("=" * 50)
    
    # Verificar archivos
    if not spec_path.exists():
        print(f"❌ Error: No se encontró {spec_path}")
        return 1
    
    if not client_path.exists():
        print(f"❌ Error: No se encontró {client_path}")
        return 1
    
    print(f"📄 Contrato: {spec_path}")
    print(f"🐍 Cliente: {client_path}")
    print()
    
    # Ejecutar auditoría
    auditor = ContractAuditor(str(spec_path), str(client_path))
    results = auditor.audit()
    
    # Mostrar resumen en consola
    print("📊 Resultados:")
    print("-" * 40)
    
    for result in results:
        emoji = {'ok': '✅', 'partial': '⚠️', 'missing': '❌'}[result.status]
        func_name = result.function.name if result.function else "N/A"
        print(f"{emoji} {result.endpoint.method:6} {result.endpoint.path:35} → {func_name}")
        
        if result.issues or result.missing_codes:
            for issue in result.issues[:2]:  # Limitar a 2 issues
                print(f"   └─ {issue}")
            if result.missing_codes:
                codes = ', '.join(sorted(result.missing_codes))
                print(f"   └─ Códigos faltantes: {codes}")
    
    print()
    
    # Generar reporte
    generator = ReportGenerator(results, str(report_path))
    generator.save()
    
    # Estadísticas finales
    ok = sum(1 for r in results if r.status == 'ok')
    partial = sum(1 for r in results if r.status == 'partial')
    missing = sum(1 for r in results if r.status == 'missing')
    
    print()
    print("📈 Estadísticas:")
    print(f"   ✅ Conformidad: {ok}")
    print(f"   ⚠️ Parcial: {partial}")
    print(f"   ❌ Faltante: {missing}")
    
    if ok == len(results):
        print()
        print("🎉 ¡Cliente 100% conforme con el contrato!")
        return 0
    else:
        print()
        print("⚠️ Se requieren correcciones. Ver reporte para detalles.")
        return 1


if __name__ == "__main__":
    exit(main())
