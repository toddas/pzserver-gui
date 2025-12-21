import subprocess
import os
import logging
import random
import sys
from flask import Flask, request, jsonify, send_from_directory
from utils import read_sandbox_vars, update_sandbox_vars_file
from utils import update_server_ini_key

sys.path.append(os.path.dirname(os.path.abspath(__file__))) 

from utils import strip_ansi_codes, parse_details_output, parse_server_ini, parse_ini_mod_lists, read_sandbox_vars, update_sandbox_vars_file, update_server_ini_file, update_server_ini_key

logger = logging.getLogger('pzserver_api')
logger.setLevel(logging.INFO) 
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
if not logger.handlers: 
    logger.addHandler(ch)




app = Flask(__name__)


SERVER_SCRIPT = "/home/pzserver/server/pzserver"
SERVER_USER = "pzserver" # The user the script must run  as
APP_USER = "pzserver-runner" # The user running this Flask app
SERVER_CONFIG_PATH="/home/pzserver/Zomboid/Server/pzserver.ini"
SANDBOX_FILE_PATH = "/home/pzserver/Zomboid/Server/pzserver_SandboxVars.lua"


COMMAND_MAP = {
    'start': ['start'],
    'stop': ['stop'],
    'restart': ['restart'],
    'details': ['dt'], 
    'mod-list': ['mod-list'],
}

def run_server_command(action_key):
    """
    Executes the linuxgsm command using SUDO to run as the target user.
    Requires the NOPASSWD configuration for APP_USER to run as SERVER_USER.
    """
    action_args = COMMAND_MAP[action_key]
    
    # CRITICAL FIX: Use the sudo -u command to elevate to the pzserver user
    full_command = ['sudo', '-u', SERVER_USER, SERVER_SCRIPT, action_args[0]]
    
    logger.info(f"Executing command: {' '.join(full_command)}")

    if not os.path.exists(SERVER_SCRIPT):
        error_msg = f"Server script not found: {SERVER_SCRIPT}"
        logger.critical(error_msg)
        return {
            "status": "fatal_error", 
            "message": f"Server script not found: {os.path.basename(SERVER_SCRIPT)}",
            "details": error_msg
        }
    
    try:
        timeout = 15 if action_key == 'details' else 120
        
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            check=True
        )
        
        raw_output = result.stdout.strip()
      
        logger.debug("_________main.py______run_server_cmd_______________")
        logger.debug(f"Command '{action_key}' succeeded. Raw output length: {len(raw_output)}")
        logger.debug(raw_output)
        output = strip_ansi_codes(raw_output)
        output = parse_details_output(output)
        logger.debug("___________output_______________")
        logger.debug(output)
        return {
            "status": "success", 
            "message": f"'{action_key}' executed successfully.",
            "details": output}
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Command '{action_key}' failed (Exit Code {e.returncode}). Stderr: {e.stderr.strip()}"
        logger.error(error_msg)
        # Check output for the 'Permission denied' type of error
        error_details = strip_ansi_codes(e.stderr.strip() or e.stdout.strip() or "No output available.")
        return {
            "status": "error", 
            "message": f"Command failed (Exit Code {e.returncode}). Check script logic.",
            "details": error_details 
        }
    except subprocess.TimeoutExpired:
        error_msg = f"Command '{action_key}' execution timed out after {timeout} seconds."
        logger.error(error_msg)
        return {
            "status": "error", 
            "message": f"Command execution timed out after {timeout} seconds.",
            "details": "The command took too long to complete."
        }
    except Exception as e:
        error_msg = f"An unexpected system error occurred: {str(e)}"
        logger.exception(error_msg) 
        return {
            "status": "fatal_error", 
            "message": f"An unexpected system error occurred: {str(e)}",
            "details": error_msg
        }

def get_save_info():
    """
    Parses server.ini to find the SaveName and constructs the path.
    Default SaveName is usually 'servertest'.
    """
    try:
        with open(SERVER_CONFIG_PATH, 'r') as f:
            content = f.read()
        
        config = parse_server_ini(content)
        save_name = config.get('SaveName', 'pzserver') # Default fallback
        
        save_path = f"/home/pzserver/Zomboid/Saves/Multiplayer/{save_name}"
        
        return save_name, save_path
    except Exception as e:
        logger.error(f"Could not determine save path: {e}")
        return None, None

def generate_ini_update_command(mods_list):
    """
    Generates a secure shell command using sudo to update the Mods and 
    WorkshopItems lines in the server INI file as the SERVER_USER.
    """
    
    mod_ids_str = ';'.join([mod['internal_id'] for mod in mods_list])
    workshop_ids_str = ';'.join([mod['workshop_id'] for mod in mods_list])
    
    # Build the sed command to atomically replace both lines
    # -i: edit files in place
    sed_command = f"sed -i 's/^Mods=.*$/Mods={mod_ids_str}/' {SERVER_CONFIG_PATH} && "
    sed_command += f"sed -i 's/^WorkshopItems=.*$/WorkshopItems={workshop_ids_str}/' {SERVER_CONFIG_PATH}"
    
    # Execute the command via bash with sudo -u
    # FIX: Added -n flag to prevent the 'a terminal is required to read the password' error.
    full_command = ['sudo', '-n', '-u', SERVER_USER, 'bash', '-c', sed_command]
    
    return full_command

def get_mod_data():
    """ 
    Orchestrates reading the INI file and parsing active mods.
    Returns: List of active mod dictionaries.
    """
    
    try:
        # Read the file content.
        with open(SERVER_CONFIG_PATH, 'r') as f:
            ini_content = f.read()
    except FileNotFoundError:
        logger.error(f"Server INI file not found at: {SERVER_CONFIG_PATH}")
        # Return an empty list if file not found
        return []
    except Exception as e:
        logger.error(f"Error reading server INI file: {e}")
        # Raise an error for permission issues
        raise IOError(f"Permission or read error for INI file: {SERVER_CONFIG_PATH}")
    
    ini_config = parse_server_ini(ini_content)
    active_mods_list = parse_ini_mod_lists(ini_config)
    
    return active_mods_list

# --- app routes fe---
@app.route('/')
def serve_frontend():
    """Serves the index.html file from the current directory."""
    logger.info("Serving index.html frontend file.")
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.route('/favicon.ico')
def favicon():
    """Serves the favicon.ico file from the app directory."""
    # The file is in the current working directory /app
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/x-icon')

@app.route('/<path:filename>')
def serve_static_files(filename):
    """
    Serves static files (js, css) from the root directory.
    Security Note: In a real production app, use Nginx or a 'static' folder.
    """
    if filename in ['script.js', 'style.css', 'utils.py', 'favicon.ico']: # Whitelist files for security
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), filename)
    return "File not found", 404

@app.route('/mods')
def serve_mods_frontend():
    """Serves the separate Mod Management HTML page."""
    logger.info("GET /mods requested. Serving mods.html.")
    # Assuming mods.html is in the same directory as main.py
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'mods.html')

@app.route('/sandbox')
def serve_sandbox_frontend():
    """Serves the Sandbox Editor HTML page."""
    logger.info("Serving sandbox.html.")
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'sandbox.html')

@app.route('/api/reset', methods=['POST'])
def reset_server_data():
    """
    Handles Soft and Hard resets.
    Hard Reset now updates ResetID in server.ini to prevent client map corruption.
    """
    logger.info("API POST /api/reset requested.")
    
    data = request.get_json()
    reset_type = data.get('type') # 'soft' or 'hard'
    
    if reset_type not in ['soft', 'hard']:
        return jsonify({"status": "error", "message": "Invalid reset type"}), 400

    save_name, save_path = get_save_info()
    if not save_path:
         return jsonify({"status": "error", "message": "Could not determine Save Path from INI."}), 500

    command = []
    messages = []
    
    if reset_type == 'soft':
        # Soft Reset: 
        # 1. zpop_*.bin -> Zombių populiacija ir spawn vietos.
        # 2. map_t.bin -> Žaidimo laikas ir Loot respawn taimeriai. Ištrynus, loot sistema persiskaičiuoja.
        logger.info(f"Performing SOFT reset on: {save_path}")
        
        # Build 42 pastaba: failų struktūra gali keistis į 'chunkdata', bet zpop išlieka pagrindinis zombiams.
        cmd_str = f"rm -f {save_path}/zpop*.bin {save_path}/map_t.bin"
        command = ['sudo', '-u', SERVER_USER, 'sh', '-c', cmd_str]
        messages.append("Zombies and loot timers wiped.")
        
    elif reset_type == 'hard':
        # Hard Reset: 
        # 1. Update ResetID (CRITICAL for client sync)
        new_reset_id = random.randint(100000000, 999999999)
        if update_server_ini_key(SERVER_CONFIG_PATH, "ResetID", new_reset_id):
             logger.info(f"Updated ResetID to {new_reset_id}")
             messages.append(f"ResetID updated to {new_reset_id} (Clients forced to resync).")
        else:
             logger.warning("Could not update ResetID. Clients might see map glitches.")

        # 2. Nuke the Save Folder
        logger.warning(f"Performing HARD reset (WIPE) on: {save_path}")
        command = ['sudo', '-u', SERVER_USER, 'rm', '-rf', save_path]
        messages.append("World save folder deleted.")

    try:
        # Execute the deletion command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        return jsonify({
            "status": "success",
            "message": f"{reset_type.capitalize()} reset complete.",
            "details": " | ".join(messages) + f"\nOutput: {result.stdout}"
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "error", 
            "message": "Reset command failed.",
            "details": e.stderr
        }), 500
    except Exception as e:
        logger.exception("Reset exception")
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/api/details', methods=['GET'])
def get_server_details():
    """Triggers the 'pzserver dt' command and returns structured JSON."""
    logger.info("API GET /api/details requested.")
    command_result = run_server_command('details')
    logger.debug("______main.py____")
    if command_result['status'] == 'success':
        logger.debug("Details command successful. Starting output parsing.")
        
        parsed_data = command_result['details']
        logger.debug(parsed_data)
        
        # Prepare JSON response structure for the frontend
        return jsonify({
            "status": "success",
            "message": command_result['message'],
            "server_status": parsed_data['Status'], # Top-level key for the badge
            "details": parsed_data          # Nested details for the panel
        }), 200
    else:
        logger.error(f"Details command failed: {command_result['message']}")
        return jsonify(command_result), 500


@app.route('/api/control', methods=['POST'])
def control_server():
    """Receives an action ('start', 'stop', 'restart') and executes command."""
    try:
        data = request.get_json()
        action = data.get('action')
        logger.info(f"API POST /api/control requested with action: {action}")

        if action not in ['start', 'stop', 'restart']:
            logger.warning(f"Invalid control action requested: {action}")
            return jsonify({
                "status": "client_error", 
                "message": "Invalid control action.",
                "details": "Valid actions are: start, stop, restart."
            }), 400

        response_data = run_server_command(action)
        
        http_status = 200 if response_data['status'] == 'success' else 500
        logger.info(f"Control action '{action}' finished with status: {response_data['status']}")
        
        return jsonify(response_data), http_status

    except Exception as e:
        logger.exception("Error processing POST /api/control request.")
        return jsonify({
            "status": "fatal_error",
            "message": "Failed to process request.",
            "details": str(e)
        }), 500


@app.route('/api/mods', methods=['GET'])
def mods_list_endpoint():
    """
    API endpoint to retrieve the list of ACTIVE mods by parsing server.ini.
    """
    logger.info("API GET /api/mods requested.")
    try:
        mod_data = get_mod_data()
        
        return jsonify({
            "status": "success",
            "data": mod_data
        }), 200
        
    except Exception as e:
        logger.exception("Error processing GET /api/mods request.")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve mod data. Check server INI file path and permissions.",
            "details": str(e)
        }), 500


@app.route('/api/mods/update', methods=['POST'])
def update_mods_endpoint():
    """
    API endpoint to update the Mods and WorkshopItems lists in server.ini 
    by executing a sudo'd sed command.
    """
    logger.info("API POST /api/mods/update requested.")
    try:
        data = request.get_json()
        active_mods = data.get('mods', [])
        
        # 1. Generate the secure update command
        full_command = generate_ini_update_command(active_mods)
        
        # 2. Execute the command
        logger.info(f"Executing INI update command: {' '.join(full_command)}")
        
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            timeout=10, 
            check=True
        )
        
        logger.info("INI file updated successfully.")
        return jsonify({
            "status": "success",
            "message": "Configuration saved to server.ini. Restart server to apply changes.",
            "details": result.stdout.strip()
        }), 200

    except subprocess.CalledProcessError as e:
        error_details = strip_ansi_codes(e.stderr.strip() or e.stdout.strip() or "No output available.")
        logger.error(f"INI update failed (Exit Code {e.returncode}). Details: {error_details}")
        return jsonify({
            "status": "error", 
            "message": f"Configuration save failed (Exit Code {e.returncode}). Check file path and sudo permissions.",
            "details": error_details
        }), 500
        
    except Exception as e:
        logger.exception("Error processing POST /api/mods/update request.")
        return jsonify({
            "status": "fatal_error",
            "message": "Failed to process request.",
            "details": str(e)
        }), 500


@app.route('/status')
def get_api_status():
    """Returns a simple JSON response to confirm the API is working."""
    logger.info("API GET /status requested. Returning operational status.")
    return jsonify({
        "api_status": "Operational",
        "message": "Hello from Flask! Ready for PZ control."
    })



@app.route('/api/sandbox', methods=['GET'])
def get_sandbox_settings():
    try:
        data = read_sandbox_vars(SANDBOX_FILE_PATH)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sandbox', methods=['POST'])
def save_sandbox_settings():
    try:
        new_data = request.get_json()
        if not new_data:
             return jsonify({"status": "error", "message": "No data provided"}), 400
             
        update_sandbox_vars_file(SANDBOX_FILE_PATH, new_data)
        return jsonify({"status": "success", "message": "Sandbox settings saved."}), 200
    except Exception as e:
        logger.exception("Failed to save sandbox settings")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/config')
def serve_config_frontend():
    """Serves the Config Editor HTML page."""
    logger.info("Serving config.html.")
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'config.html')

@app.route('/api/config', methods=['GET'])
def get_server_config():
    """Reads the server.ini file and returns it as JSON."""
    try:
        with open(SERVER_CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Naudojame jau esamą parse_server_ini funkciją
        data = parse_server_ini(content)
        return jsonify({"status": "success", "data": data}), 200
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Server INI file not found."}), 404
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_server_config():
    """Updates the server.ini file."""
    try:
        new_data = request.get_json()
        if not new_data:
             return jsonify({"status": "error", "message": "No data provided"}), 400
             
        update_server_ini_file(SERVER_CONFIG_PATH, new_data)
        logger.info("Server INI configuration updated.")
        return jsonify({"status": "success", "message": "Configuration saved. Restart required."}), 200
    except Exception as e:
        logger.exception("Failed to save config")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting PZ Server Manager API...")
    app.run(host='0.0.0.0', port=5000, debug=True)