#!/usr/bin/env python3
"""
Interfaz Web del Simulador Therac-25
====================================

ATENCIÓN: Esta interfaz reproduce los errores mortales del Therac-25 original.
Propósito educativo para demostrar la importancia de la calidad del software.

© 2024 - Proyecto de Calidad de Software
"""

from flask import Flask, render_template, request, jsonify, session
import threading
import time
import os
import sys
import uuid
from datetime import datetime

# Añadir el directorio padre al path para importar módulos del simulador
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from simulator.control_module import ControlModule, BeamMode, MachineState

app = Flask(__name__)
app.secret_key = 'therac25-simulator-secret-key'

# Instancia global del módulo de control
control_module = None
session_lock = threading.Lock()

def get_control_module():
    """Obtiene o crea una instancia del módulo de control para la sesión actual"""
    global control_module

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    with session_lock:
        if control_module is None:
            control_module = ControlModule(version="buggy")

    return control_module

@app.route('/')
def index():
    """Página principal del simulador"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Obtiene el estado actual de la máquina"""
    try:
        cm = get_control_module()
        status = {
            'estado': cm.state.value,
            'modo_haz': cm.beam_mode.value,
            'dosis': cm.dose_value,
            'posicion_x': cm.position_x,
            'posicion_y': cm.position_y,
            'contador_configuracion': cm.setup_counter,
            'posicion_mesa': getattr(cm, 'turntable_position', 'xray'),
            'mesa_moviendo': getattr(cm, 'turntable_moving', False),
            'version': 'buggy',
            'timestamp': datetime.now().isoformat(),
            'peligros_detectados': []
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': f'Error al obtener estado: {str(e)}'}), 500

@app.route('/api/setup', methods=['POST'])
def setup_treatment():
    """Configura los parámetros del tratamiento"""
    try:
        data = request.json
        dosis = int(data.get('dosis', 0))
        pos_x = int(data.get('posicion_x', 0))
        pos_y = int(data.get('posicion_y', 0))

        cm = get_control_module()
        result = cm.setup_treatment(dosis, pos_x, pos_y)

        return jsonify({
            'exito': True,
            'mensaje': f'Tratamiento configurado: {dosis} cGy en posición ({pos_x}, {pos_y})',
            'configuracion': {
                'dosis': dosis,
                'posicion_x': pos_x,
                'posicion_y': pos_y
            }
        })
    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error en configuración: {str(e)}'
        }), 400

@app.route('/api/mode', methods=['POST'])
def change_mode():
    """Cambia el modo del haz (rayos X o electrones)"""
    try:
        data = request.json
        modo = data.get('modo', '').lower()

        if modo not in ['xray', 'electron']:
            return jsonify({
                'exito': False,
                'error': 'Modo inválido. Use "xray" o "electron"'
            }), 400

        cm = get_control_module()
        beam_mode = BeamMode.XRAY if modo == 'xray' else BeamMode.ELECTRON

        # ADVERTENCIA: Este cambio de modo reproduce el bug mortal del Therac-25
        result = cm.change_mode(beam_mode)

        return jsonify({
            'exito': True,
            'mensaje': f'Modo cambiado a: {modo.upper()}',
            'modo_anterior': cm.beam_mode.value,
            'modo_nuevo': modo,
            'advertencia': 'PELIGRO: Posible desincronización de hardware detectada' if not result else None
        })
    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error al cambiar modo: {str(e)}'
        }), 500

@app.route('/api/fire', methods=['POST'])
def fire_beam():
    """Dispara el haz de radiación - REPRODUCIR EL BUG MORTAL"""
    try:
        cm = get_control_module()

        # ADVERTENCIA CRÍTICA: Esta función puede reproducir sobredosis mortales
        if cm.dose_value == 0:
            return jsonify({
                'exito': False,
                'error': 'PELIGRO: Intento de disparo con dosis 0. En el Therac-25 real esto causó sobredosis.',
                'nivel_peligro': 'CRÍTICO'
            }), 400

        if cm.state != MachineState.READY:
            return jsonify({
                'exito': False,
                'error': f'Máquina no lista. Estado actual: {cm.state.value}',
                'nivel_peligro': 'ALTO'
            }), 400

        result = cm.fire_beam()

        # Simular el bug del contador de 8 bits
        if cm.setup_counter >= 256:
            return jsonify({
                'exito': False,
                'error': 'BUG REPRODUCIDO: Desbordamiento del contador (8-bit overflow). ¡Controles de seguridad deshabilitados!',
                'nivel_peligro': 'MORTAL',
                'bug_historico': 'Este es el bug que causó muertes en el Therac-25 real.',
                'dosis_real_aplicada': cm.dose_value * 100  # Simular sobredosis masiva
            }), 500

        return jsonify({
            'exito': True,
            'mensaje': 'Haz disparado exitosamente',
            'dosis_aplicada': cm.dose_value,
            'modo': cm.beam_mode.value,
            'posicion': f'({cm.position_x}, {cm.position_y})',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error crítico durante disparo: {str(e)}',
            'nivel_peligro': 'CRÍTICO'
        }), 500

@app.route('/api/edit', methods=['POST'])
def edit_field():
    """Edita un campo durante la operación - REPRODUCE RACE CONDITION"""
    try:
        data = request.json
        campo = data.get('campo', '')
        valor = data.get('valor', '')

        cm = get_control_module()

        # SIMULAR EL RACE CONDITION DE EDICIÓN
        if cm.state == MachineState.FIRING:
            return jsonify({
                'exito': False,
                'error': 'BUG REPRODUCIDO: Edición durante disparo detectada. ¡Race condition crítico!',
                'nivel_peligro': 'MORTAL',
                'bug_historico': 'Los operadores del Therac-25 editaban mientras la máquina operaba, causando configuraciones parciales mortales.'
            }), 500

        # Simular edición con posible corrupción de datos
        if campo == 'dosis':
            try:
                nueva_dosis = int(valor)
                # Simular el bug de edición rápida
                time.sleep(0.1)  # Simular delay que causa race condition
                cm.dose_value = nueva_dosis

                return jsonify({
                    'exito': True,
                    'mensaje': f'Dosis editada a: {nueva_dosis} cGy',
                    'advertencia': 'ATENCIÓN: Edición realizada sin verificación completa de seguridad',
                    'campo_editado': campo,
                    'valor_nuevo': nueva_dosis
                })
            except ValueError:
                return jsonify({
                    'exito': False,
                    'error': 'Valor de dosis inválido'
                }), 400

        elif campo == 'posicion_x':
            try:
                nueva_pos_x = int(valor)
                cm.position_x = nueva_pos_x
                return jsonify({
                    'exito': True,
                    'mensaje': f'Posición X editada a: {nueva_pos_x}',
                    'posicion_nueva': (cm.position_x, cm.position_y)
                })
            except ValueError:
                return jsonify({'exito': False, 'error': 'Valor de posición X inválido'}), 400

        elif campo == 'posicion_y':
            try:
                nueva_pos_y = int(valor)
                cm.position_y = nueva_pos_y
                return jsonify({
                    'exito': True,
                    'mensaje': f'Posición Y editada a: {nueva_pos_y}',
                    'posicion_nueva': (cm.position_x, cm.position_y)
                })
            except ValueError:
                return jsonify({'exito': False, 'error': 'Valor de posición Y inválido'}), 400

        else:
            return jsonify({
                'exito': False,
                'error': f'Campo desconocido: {campo}'
            }), 400

    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error durante edición: {str(e)}'
        }), 500

@app.route('/api/reset')
def reset_machine():
    """Reinicia la máquina al estado inicial"""
    try:
        global control_module
        with session_lock:
            control_module = ControlModule(version="buggy")

        return jsonify({
            'exito': True,
            'mensaje': 'Máquina reiniciada al estado inicial',
            'advertencia': 'MODO BUGGY: Todos los errores históricos están activos'
        })
    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error al reiniciar: {str(e)}'
        }), 500

@app.route('/api/emergency_stop', methods=['POST'])
def emergency_stop():
    """Parada de emergencia"""
    try:
        cm = get_control_module()
        cm.state = MachineState.ERROR

        return jsonify({
            'exito': True,
            'mensaje': 'PARADA DE EMERGENCIA ACTIVADA',
            'estado': 'ERROR'
        })
    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error en parada de emergencia: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🚨 INICIANDO SIMULADOR THERAC-25 CON INTERFAZ WEB")
    print("⚠️  ADVERTENCIA: Esta versión reproduce los errores mortales del Therac-25 original")
    print("📚 Propósito educativo: Demostrar la importancia de la calidad del software")
    print("🌐 Acceder en: http://localhost:8080")
    print()

    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        threaded=True
    )