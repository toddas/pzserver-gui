import subprocess
import os
import logging
from flask import Flask, request, jsonify, send_from_directory
import sys 
# Ensure utils.py is available if running outside a standard environment
sys.path.append(os.path.dirname(os.path.abspath(__file__))) 

# Import helper functions from utils.py
from utils import strip_ansi_codes, parse_details_output

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

COMMAND_MAP = {
    'start': ['start'],
    'stop': ['stop'],
    'restart': ['restart'],
    'details': ['dt'], 
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
        cleaned_output = strip_ansi_codes(raw_output)

        logger.debug(f"Command '{action_key}' succeeded. Raw output length: {len(raw_output)}")

        return {
            "status": "success", 
            "message": f"'{action_key}' executed successfully.",
            "details": cleaned_output
        }
        
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


# --- Serve the Frontend HTML File ---
@app.route('/')
def serve_frontend():
    """Serves the index.html file from the current directory."""
    logger.info("Serving index.html frontend file.")
    return send_from_directory(os.path.dirname(__file__), 'index.html')


# --- API Endpoint for Server Details (GET) ---
@app.route('/api/details', methods=['GET'])
def get_server_details():
    """Triggers the 'pzserver dt' command and returns structured JSON."""
    logger.info("API GET /api/details requested.")
    command_result = run_server_command('details')
    
    if command_result['status'] == 'success':
        logger.debug("Details command successful. Starting output parsing.")
        
        parsed_data = parse_details_output(command_result['details'])
        
        # CORRECTED: Retrieve status from the top-level 'server_status' key
        server_status = parsed_data.get('server_status', 'UNKNOWN')
        logger.info(f"Details parsed successfully. Server Status: {server_status}")
        
        # Prepare JSON response structure for the frontend
        if 'server_status' in parsed_data:
            del parsed_data['server_status'] 

        return jsonify({
            "status": "success",
            "message": command_result['message'],
            "server_status": server_status, # Top-level key for the badge
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
    app.run(host='0.0.0.0', port=5000, debug=False)