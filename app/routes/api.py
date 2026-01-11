from flask import Blueprint, request, jsonify
import logging
from app.services.server_manager import (
    run_server_command, 
    perform_reset, 
    get_mod_data, 
    generate_ini_update_command,
    SERVER_CONFIG_PATH,
    SANDBOX_FILE_PATH,
    SERVER_USER
)
from app.services.file_manager import (
    read_sandbox_vars, 
    update_sandbox_vars_file,
    update_server_ini_file
)
from app.utils.parsers import parse_server_ini
import subprocess

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger('pzserver_api')

@api_bp.route('/reset', methods=['POST'])
def reset_server_data():
    data = request.get_json()
    reset_type = data.get('type')
    result, status_code = perform_reset(reset_type)
    return jsonify(result), status_code

@api_bp.route('/details', methods=['GET'])
def get_server_details():
    command_result = run_server_command('details')
    if command_result['status'] == 'success':
        parsed_data = command_result['details']
        return jsonify({
            "status": "success",
            "message": command_result['message'],
            "server_status": parsed_data.get('Status', 'UNKNOWN'),
            "details": parsed_data
        }), 200
    else:
        return jsonify(command_result), 500

@api_bp.route('/control', methods=['POST'])
def control_server():
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action not in ['start', 'stop', 'restart']:
            return jsonify({"status": "client_error", "message": "Invalid action"}), 400

        response_data = run_server_command(action)
        http_status = 200 if response_data['status'] == 'success' else 500
        return jsonify(response_data), http_status
        
    except Exception as e:
        logger.exception("Error processing control request")
        return jsonify({"status": "fatal_error", "message": str(e)}), 500

@api_bp.route('/mods', methods=['GET'])
def mods_list_endpoint():
    try:
        mod_data = get_mod_data()
        return jsonify({"status": "success", "data": mod_data}), 200
    except Exception as e:
        logger.exception("Error processing mods request")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/mods/update', methods=['POST'])
def update_mods_endpoint():
    try:
        data = request.get_json()
        active_mods = data.get('mods', [])
        
        full_command = generate_ini_update_command(active_mods)
        
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            timeout=10, 
            check=True
        )
        
        return jsonify({
            "status": "success",
            "message": "Configuration saved.",
            "details": result.stdout.strip()
        }), 200
        
    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "error", 
            "message": "Configuration save failed.",
            "details": e.stderr
        }), 500
    except Exception as e:
        logger.exception("Error processing mods update")
        return jsonify({"status": "fatal_error", "message": str(e)}), 500

@api_bp.route('/sandbox', methods=['GET'])
def get_sandbox_settings_endpoint():
    try:
        data = read_sandbox_vars(SANDBOX_FILE_PATH)
        # Check if empty (read error)
        if not data.get('values') and not data.get('descriptions'):
             # This might just mean the file is empty or parse failed, but we return success with empty data
             pass
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/sandbox', methods=['POST'])
def save_sandbox_settings_endpoint():
    try:
        new_data = request.get_json()
        if not new_data:
             return jsonify({"status": "error", "message": "No data provided"}), 400
             
        update_sandbox_vars_file(SANDBOX_FILE_PATH, new_data)
        return jsonify({"status": "success", "message": "Sandbox settings saved."}), 200
    except Exception as e:
        logger.exception("Failed to save sandbox settings")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/config', methods=['GET'])
def get_server_config_endpoint():
    try:
        with open(SERVER_CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        data = parse_server_ini(content)
        return jsonify({"status": "success", "data": data}), 200
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Server INI file not found."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/config', methods=['POST'])
def save_server_config_endpoint():
    try:
        new_data = request.get_json()
        if not new_data:
             return jsonify({"status": "error", "message": "No data provided"}), 400
             
        update_server_ini_file(SERVER_CONFIG_PATH, new_data)
        return jsonify({"status": "success", "message": "Configuration saved."}), 200
    except Exception as e:
        logger.exception("Failed to save config")
        return jsonify({"status": "error", "message": str(e)}), 500
