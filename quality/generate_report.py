#!/usr/bin/env python3
"""
Generador de Reporte Consolidado de Calidad
Genera un reporte HTML/PDF con todos los hallazgos del pipeline de calidad
"""

import json
import xml.etree.ElementTree as ET
import os
import sys
from datetime import datetime
from pathlib import Path
import argparse

def load_coverage_data(coverage_xml_path):
    """Cargar datos de cobertura desde coverage.xml"""
    try:
        tree = ET.parse(coverage_xml_path)
        root = tree.getroot()
        line_rate = float(root.get('line-rate', 0))
        branch_rate = float(root.get('branch-rate', 0))

        packages = []
        for package in root.findall('.//package'):
            pkg_name = package.get('name', 'unknown')
            pkg_line_rate = float(package.get('line-rate', 0))
            packages.append({
                'name': pkg_name,
                'coverage': pkg_line_rate * 100
            })

        return {
            'line_coverage': line_rate * 100,
            'branch_coverage': branch_rate * 100,
            'packages': packages
        }
    except Exception as e:
        print(f"⚠️ Error leyendo cobertura: {e}")
        return None

def load_test_results(junit_xml_path):
    """Cargar resultados de pruebas desde JUnit XML"""
    try:
        tree = ET.parse(junit_xml_path)
        root = tree.getroot()

        total_tests = int(root.get('tests', 0))
        failures = int(root.get('failures', 0))
        errors = int(root.get('errors', 0))
        skipped = int(root.get('skipped', 0))

        failed_tests = []
        for testcase in root.findall('.//testcase'):
            failure = testcase.find('failure')
            error = testcase.find('error')
            if failure is not None or error is not None:
                failed_tests.append({
                    'name': testcase.get('name', 'unknown'),
                    'classname': testcase.get('classname', 'unknown'),
                    'time': testcase.get('time', '0'),
                    'failure_message': failure.text if failure is not None else error.text
                })

        return {
            'total': total_tests,
            'passed': total_tests - failures - errors - skipped,
            'failures': failures,
            'errors': errors,
            'skipped': skipped,
            'failed_tests': failed_tests
        }
    except Exception as e:
        print(f"⚠️ Error leyendo resultados de pruebas: {e}")
        return None

def load_security_data(reports_dir):
    """Cargar datos de análisis de seguridad"""
    security_data = {
        'bandit': None,
        'safety': None,
        'owasp': None
    }

    # Bandit report
    bandit_path = Path(reports_dir) / 'security' / 'bandit-report.json'
    if bandit_path.exists():
        try:
            with open(bandit_path, 'r') as f:
                bandit_data = json.load(f)
                security_data['bandit'] = {
                    'issues_count': len(bandit_data.get('results', [])),
                    'high_severity': len([r for r in bandit_data.get('results', []) if r.get('issue_severity') == 'HIGH']),
                    'medium_severity': len([r for r in bandit_data.get('results', []) if r.get('issue_severity') == 'MEDIUM']),
                    'low_severity': len([r for r in bandit_data.get('results', []) if r.get('issue_severity') == 'LOW']),
                    'issues': bandit_data.get('results', [])
                }
        except Exception as e:
            print(f"⚠️ Error leyendo reporte Bandit: {e}")

    # Safety report
    safety_path = Path(reports_dir) / 'security' / 'safety-report.json'
    if safety_path.exists():
        try:
            with open(safety_path, 'r') as f:
                safety_data = json.load(f)
                security_data['safety'] = {
                    'vulnerabilities_count': len(safety_data) if isinstance(safety_data, list) else 0,
                    'vulnerabilities': safety_data if isinstance(safety_data, list) else []
                }
        except Exception as e:
            print(f"⚠️ Error leyendo reporte Safety: {e}")

    return security_data

def generate_html_report(data, output_path):
    """Generar reporte HTML consolidado"""

    html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Calidad - Simulación Therac-25</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            background: #f8f9fa;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            font-size: 1.8em;
            display: flex;
            align-items: center;
        }}
        .section h2 .emoji {{
            margin-right: 10px;
            font-size: 1.2em;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .info {{ color: #17a2b8; }}

        .test-list {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            margin-top: 20px;
        }}
        .test-item {{
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .test-item:last-child {{
            border-bottom: none;
        }}
        .test-name {{
            font-weight: 500;
        }}
        .test-status {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-pass {{
            background: #d4edda;
            color: #155724;
        }}
        .status-fail {{
            background: #f8d7da;
            color: #721c24;
        }}

        .security-issue {{
            background: white;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }}
        .security-issue.medium {{
            border-left-color: #ffc107;
        }}
        .security-issue.low {{
            border-left-color: #28a745;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #eee;
        }}

        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Reporte de Calidad - Simulación Therac-25</h1>
            <p>Análisis completo de calidad de software • {datetime.now().strftime('%d de %B de %Y, %H:%M')}</p>
        </div>

        <div class="content">
            <!-- Resumen Ejecutivo -->
            <div class="section">
                <h2><span class="emoji">📊</span>Resumen Ejecutivo</h2>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value {'success' if data.get('tests', {}).get('failures', 1) == 0 else 'danger'}">
                            {data.get('tests', {}).get('passed', 0)}/{data.get('tests', {}).get('total', 0)}
                        </div>
                        <div class="metric-label">Pruebas Exitosas</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value {'success' if data.get('coverage', {}).get('line_coverage', 0) >= 80 else 'warning'}">
                            {data.get('coverage', {}).get('line_coverage', 0):.1f}%
                        </div>
                        <div class="metric-label">Cobertura de Código</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value {'success' if data.get('security', {}).get('bandit', {}).get('high_severity', 1) == 0 else 'danger'}">
                            {data.get('security', {}).get('bandit', {}).get('issues_count', 0)}
                        </div>
                        <div class="metric-label">Issues de Seguridad</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value {'success' if data.get('security', {}).get('safety', {}).get('vulnerabilities_count', 1) == 0 else 'danger'}">
                            {data.get('security', {}).get('safety', {}).get('vulnerabilities_count', 0)}
                        </div>
                        <div class="metric-label">Vulnerabilidades</div>
                    </div>
                </div>
            </div>

            <!-- Resultados de Pruebas -->
            {generate_tests_section(data.get('tests'))}

            <!-- Cobertura de Código -->
            {generate_coverage_section(data.get('coverage'))}

            <!-- Análisis de Seguridad -->
            {generate_security_section(data.get('security'))}

            <!-- Conclusiones -->
            <div class="section">
                <h2><span class="emoji">🎯</span>Conclusiones y Recomendaciones</h2>
                <p><strong>Estado General:</strong> {get_overall_status(data)}</p>

                <h3>📋 Recomendaciones:</h3>
                <ul>
                    {generate_recommendations(data)}
                </ul>

                <h3>💡 Lecciones del Therac-25:</h3>
                <p>Este pipeline demuestra cómo las herramientas modernas de calidad habrían <strong>prevenido las 6+ muertes del Therac-25</strong>.
                Cada muerte era 100% prevenible con herramientas como las utilizadas en este análisis.</p>
            </div>
        </div>

        <div class="footer">
            <p>🤖 Generado automáticamente por el Pipeline de Calidad Therac-25</p>
            <p>Powered by GitHub Actions • {datetime.now().strftime('%Y')}</p>
        </div>
    </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

def generate_tests_section(tests_data):
    if not tests_data:
        return '<div class="section"><h2><span class="emoji">🧪</span>Resultados de Pruebas</h2><p>No se encontraron datos de pruebas.</p></div>'

    failed_tests_html = ""
    if tests_data.get('failed_tests'):
        for test in tests_data['failed_tests']:
            failed_tests_html += f"""
            <div class="test-item">
                <div>
                    <div class="test-name">{test['name']}</div>
                    <small style="color: #666;">{test['classname']}</small>
                </div>
                <div class="test-status status-fail">FALLO</div>
            </div>
            """

    return f"""
    <div class="section">
        <h2><span class="emoji">🧪</span>Resultados de Pruebas</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value success">{tests_data.get('passed', 0)}</div>
                <div class="metric-label">Exitosas</div>
            </div>
            <div class="metric">
                <div class="metric-value danger">{tests_data.get('failures', 0)}</div>
                <div class="metric-label">Fallidas</div>
            </div>
            <div class="metric">
                <div class="metric-value warning">{tests_data.get('skipped', 0)}</div>
                <div class="metric-label">Omitidas</div>
            </div>
            <div class="metric">
                <div class="metric-value info">{tests_data.get('total', 0)}</div>
                <div class="metric-label">Total</div>
            </div>
        </div>

        {f'<h3>❌ Pruebas Fallidas:</h3><div class="test-list">{failed_tests_html}</div>' if failed_tests_html else '<p class="success">✅ Todas las pruebas pasaron exitosamente.</p>'}
    </div>
    """

def generate_coverage_section(coverage_data):
    if not coverage_data:
        return '<div class="section"><h2><span class="emoji">📈</span>Cobertura de Código</h2><p>No se encontraron datos de cobertura.</p></div>'

    status_class = "success" if coverage_data.get('line_coverage', 0) >= 80 else "warning"

    return f"""
    <div class="section">
        <h2><span class="emoji">📈</span>Cobertura de Código</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value {status_class}">{coverage_data.get('line_coverage', 0):.1f}%</div>
                <div class="metric-label">Líneas</div>
            </div>
            <div class="metric">
                <div class="metric-value {status_class}">{coverage_data.get('branch_coverage', 0):.1f}%</div>
                <div class="metric-label">Ramas</div>
            </div>
        </div>
        <p class="{'success' if coverage_data.get('line_coverage', 0) >= 80 else 'warning'}">
            {'✅ Cobertura adecuada para sistemas de seguridad' if coverage_data.get('line_coverage', 0) >= 80 else '⚠️ Cobertura crítica para dispositivos médicos'}
        </p>
    </div>
    """

def generate_security_section(security_data):
    if not security_data:
        return '<div class="section"><h2><span class="emoji">🔒</span>Análisis de Seguridad</h2><p>No se encontraron datos de seguridad.</p></div>'

    bandit_issues = ""
    if security_data.get('bandit', {}).get('issues'):
        for issue in security_data['bandit']['issues'][:5]:  # Mostrar solo los primeros 5
            severity_class = issue.get('issue_severity', 'LOW').lower()
            bandit_issues += f"""
            <div class="security-issue {severity_class}">
                <strong>{issue.get('test_name', 'Unknown Issue')}</strong>
                <span class="test-status status-fail">{issue.get('issue_severity', 'UNKNOWN')}</span>
                <br>
                <small>{issue.get('filename', 'unknown')}:{issue.get('line_number', '?')}</small>
                <p>{issue.get('issue_text', 'No description available')}</p>
            </div>
            """

    return f"""
    <div class="section">
        <h2><span class="emoji">🔒</span>Análisis de Seguridad</h2>

        <h3>🛡️ Bandit (Análisis de Código)</h3>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value danger">{security_data.get('bandit', {}).get('high_severity', 0)}</div>
                <div class="metric-label">Alta Severidad</div>
            </div>
            <div class="metric">
                <div class="metric-value warning">{security_data.get('bandit', {}).get('medium_severity', 0)}</div>
                <div class="metric-label">Media Severidad</div>
            </div>
            <div class="metric">
                <div class="metric-value info">{security_data.get('bandit', {}).get('low_severity', 0)}</div>
                <div class="metric-label">Baja Severidad</div>
            </div>
        </div>

        {bandit_issues if bandit_issues else '<p class="success">✅ No se encontraron problemas de seguridad en el código.</p>'}

        <h3>🔍 Safety (Vulnerabilidades de Dependencias)</h3>
        <p class="{'danger' if security_data.get('safety', {}).get('vulnerabilities_count', 0) > 0 else 'success'}">
            {f"❌ Se encontraron {security_data.get('safety', {}).get('vulnerabilities_count', 0)} vulnerabilidades en las dependencias" if security_data.get('safety', {}).get('vulnerabilities_count', 0) > 0 else "✅ No se encontraron vulnerabilidades en las dependencias"}
        </p>
    </div>
    """

def get_overall_status(data):
    """Determinar el estado general del proyecto"""
    issues = []

    if data.get('tests', {}).get('failures', 0) > 0:
        issues.append("pruebas fallidas")

    if data.get('coverage', {}).get('line_coverage', 0) < 80:
        issues.append("cobertura insuficiente")

    if data.get('security', {}).get('bandit', {}).get('high_severity', 0) > 0:
        issues.append("problemas críticos de seguridad")

    if data.get('security', {}).get('safety', {}).get('vulnerabilities_count', 0) > 0:
        issues.append("vulnerabilidades en dependencias")

    if not issues:
        return "✅ Excelente - Todos los indicadores están en verde"
    elif len(issues) == 1:
        return f"⚠️ Requiere atención - Se detectaron {issues[0]}"
    else:
        return f"❌ Crítico - Se detectaron múltiples problemas: {', '.join(issues)}"

def generate_recommendations(data):
    """Generar recomendaciones basadas en los datos"""
    recommendations = []

    if data.get('tests', {}).get('failures', 0) > 0:
        recommendations.append("<li>🔧 <strong>Corregir pruebas fallidas</strong> - Las pruebas son fundamentales para prevenir accidentes como los del Therac-25</li>")

    if data.get('coverage', {}).get('line_coverage', 0) < 80:
        recommendations.append("<li>📈 <strong>Aumentar cobertura de código</strong> - Para sistemas críticos se recomienda >90% de cobertura</li>")

    if data.get('security', {}).get('bandit', {}).get('high_severity', 0) > 0:
        recommendations.append("<li>🔒 <strong>Resolver problemas críticos de seguridad</strong> - Los issues de alta severidad deben corregirse inmediatamente</li>")

    if data.get('security', {}).get('safety', {}).get('vulnerabilities_count', 0) > 0:
        recommendations.append("<li>🛡️ <strong>Actualizar dependencias vulnerables</strong> - Mantener las dependencias actualizadas es crucial</li>")

    if not recommendations:
        recommendations.append("<li>✅ <strong>Excelente trabajo</strong> - El código cumple con los estándares de calidad para sistemas críticos</li>")
        recommendations.append("<li>🔄 <strong>Mantener buenas prácticas</strong> - Continuar ejecutando el pipeline en cada cambio</li>")

    recommendations.append("<li>📚 <strong>Revisar caso Therac-25</strong> - Estudiar cómo estos análisis habrían prevenido las tragedias históricas</li>")

    return '\n'.join(recommendations)

def main():
    parser = argparse.ArgumentParser(description='Generar reporte consolidado de calidad')
    parser.add_argument('--reports-dir', default='reports', help='Directorio de reportes')
    parser.add_argument('--output', default='quality-report.html', help='Archivo de salida')
    parser.add_argument('--coverage-xml', default='coverage.xml', help='Archivo coverage.xml')
    parser.add_argument('--junit-xml', default='reports/static/test-results.xml', help='Archivo JUnit XML')

    args = parser.parse_args()

    print("🔍 Generando reporte consolidado de calidad...")

    # Cargar todos los datos
    data = {
        'coverage': load_coverage_data(args.coverage_xml),
        'tests': load_test_results(args.junit_xml),
        'security': load_security_data(args.reports_dir)
    }

    # Generar reporte HTML
    generate_html_report(data, args.output)

    print(f"✅ Reporte generado: {args.output}")
    print(f"📊 Estado: {get_overall_status(data)}")

if __name__ == "__main__":
    main()