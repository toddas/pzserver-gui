import subprocess
import os
import logging
import json
from flask import Flask, request, jsonify, send_from_directory
import sys 
# Ensure utils.py is available if running outside a standard environment
sys.path.append(os.path.dirname(os.path.abspath(__file__))) 

# Import helper functions from utils.py
from utils import strip_ansi_codes, parse_details_output, parse_server_ini, parse_ini_mod_lists

# --- Setup Logging ---
logger = logging.getLogger('pzserver_api')
# Set to INFO for service/production, DEBUG for testing (as you had it)
logger.setLevel(logging.INFO) 
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
if not logger.handlers: 
    logger.addHandler(ch)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Configuration ---
# Your specified paths and user
SERVER_SCRIPT = "/home/pzserver/server/pzserver"
SERVER_USER = "pzserver" # The user the script must run as
APP_USER = "pzserver-runner" # The user running this Flask app
SERVER_CONFIG_PATH="/home/pzserver/Zomboid/Server/pzserver.ini"

COMMAND_MAP = {
    'start': ['start'],
    'stop': ['stop'],
    'restart': ['restart'],
    'details': ['dt'], 
    'mod-list': ['mod-list'],
}

# --- Function for Secure Command Execution ---
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

# --- Function to generate the shell command to update the INI file securely ---
def generate_ini_update_command(mods_list):
    """
    Generates a secure shell command using sudo to update the Mods and 
    WorkshopItems lines in the server INI file as the SERVER_USER.
    """
    
    # Extract the semicolon-separated strings for INI file
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
    
    # 1. Get ENABLED mods configuration from server.ini (The ACTIVE list)
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

# --- Serve the Frontend HTML File ---
@app.route('/')
def serve_frontend():
    """Serves the index.html file from the current directory."""
    logger.info("Serving index.html frontend file.")
    return send_from_directory(os.path.dirname(__file__), 'index.html')


# --- Serve the Mods Frontend HTML File ---
@app.route('/mods')
def serve_mods_frontend():
    """Serves the separate Mod Management HTML page."""
    logger.info("GET /mods requested. Serving mods.html.")
    # Assuming mods.html is in the same directory as main.py
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'mods.html')


# --- API Endpoint for Server Details (GET) ---
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


# --- API Endpoint for Server Control (POST) ---
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


# --- API Route: Get Active Mods List ---
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


# --- API Route: Update Active Mods List (CRITICAL FIX) ---
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


# --- Minimal Test Route ---
@app.route('/status')
def get_api_status():
    """Returns a simple JSON response to confirm the API is working."""
    logger.info("API GET /status requested. Returning operational status.")
    return jsonify({
        "api_status": "Operational",
        "message": "Hello from Flask! Ready for PZ control."
    })


# --- Server Startup ---
if __name__ == '__main__':
    # Start the application on a standard port for a service user
    logger.info("Starting PZ Server Manager API...")
    app.run(host='0.0.0.0', port=5000, debug=True)