import subprocess
import os
import re 
from flask import Flask, request, jsonify

# This defines the core Flask application object
app = Flask(__name__)

# --- Configuration (Define your Zomboid paths here) ---
# NOTE: This directory is crucial. It must be updated to where your control scripts live!
SERVER_DIR = "/home/pzserver/server/" 

# Define the single Zomboid executable that accepts commands
SERVER_EXECUTABLE = os.path.join(SERVER_DIR, "pzserver")

# Map the frontend command to the actual argument passed to the pzserver executable.
COMMAND_MAP = {
    # Control Actions (for POST /api/control)
    'start': ['start'],
    'stop': ['stop'],
    'restart': ['restart'],
    
    # Status/Detail Action (for GET /api/details)
    'details': ['dt'], 
}


# --- Helper to Clean Terminal Output ---
# Regular expression to match common ANSI color/format codes
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

def strip_ansi_codes(text):
    """Removes all ANSI escape sequences from a string."""
    return ANSI_ESCAPE.sub('', text)
# ----------------------------------------


# --- Helper to Parse Server Details Text into JSON Structure ---
def parse_details_output(text):
    """
    Parses the multi-line, clean output of 'pzserver dt' into a structured dictionary.
    """
    parsed_data = {}
    current_section_name = None
    lines = text.split('\n')
    
    # Helper to convert "Server name" to "server_name"
    def slugify(key):
        return key.lower().replace(' ', '_').replace('/', '_').replace('.', '_')
    
    # Helper to process a line that looks like 'Key: Value'
    def process_key_value(line, target_dict):
        # Look for the first colon that separates the key from the value
        if ':' in line and len(line) > 1:
            try:
                key, value = line.split(':', 1)
                key = slugify(key.strip())
                value = value.strip()
                if key and value:
                    # Clean up common LinuxGSM artifacts like trailing tabs
                    if "\t" in value:
                        value = value.split("\t")[0].strip()
                        
                    target_dict[key] = value
            except ValueError:
                # Ignore lines that don't split correctly
                pass

    # The main parsing loop
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 1. Identify Section Headers (usually capitalized and on their own line)
        if line.isupper() and len(line.split()) < 5:
            current_section_name = slugify(line)
            parsed_data[current_section_name] = {}
        
        # 2. Identify Sub-Headers (like CPU, Memory, Storage within Server Resource)
        elif current_section_name == 'server_resource' and len(line.split()) < 3 and line.isalpha():
            sub_section_name = slugify(line)
            parsed_data[current_section_name][sub_section_name] = {}
        
        # 3. Process Key-Value Pairs
        elif current_section_name:
            # Check for sub-section keys (CPU, Memory, etc. under Server Resource)
            if current_section_name == 'server_resource':
                # Try to process the line within the last created sub-section
                last_sub_section_key = next(reversed(parsed_data[current_section_name]), None)
                if last_sub_section_key:
                     process_key_value(line, parsed_data[current_section_name][last_sub_section_key])
            else:
                # Process lines in top-level sections
                process_key_value(line, parsed_data[current_section_name])

        # 4. Handle ports separately as it has unique output structure
        elif line.startswith('Game') or line.startswith('Query'):
            if 'ports' not in parsed_data:
                parsed_data['ports'] = []
            
            # Simple space splitting for the structured port list
            parts = [p.strip() for p in line.split('  ') if p.strip()]
            if len(parts) >= 4:
                parsed_data['ports'].append({
                    'description': parts[0],
                    'port': parts[1],
                    'protocol': parts[2],
                    'listen': parts[3],
                })
        
        # 5. Extract the final single 'Status' line which is often separate
        elif line.startswith('Status:'):
             process_key_value(line, parsed_data)
             
    return parsed_data
# ----------------------------------------


# --- Function for Secure Command Execution ---
def run_server_command(action_key):
    """
    Executes a pzserver command (e.g., pzserver start) securely.
    The action_key is used to look up the arguments in COMMAND_MAP.
    Returns a dictionary with status and details.
    """
    if action_key not in COMMAND_MAP:
         return {
            "status": "client_error", 
            "message": "Invalid command action requested.",
            "details": f"Valid commands are: {', '.join(COMMAND_MAP.keys())}"
        }

    # Construct the full command: [pzserver_path, command_arg1, command_arg2, ...]
    command_args = [SERVER_EXECUTABLE] + COMMAND_MAP[action_key]
    
    # Check if the executable exists before trying to run it
    if not os.path.exists(SERVER_EXECUTABLE):
        return {
            "status": "fatal_error", 
            "message": f"Server executable not found: {os.path.basename(SERVER_EXECUTABLE)}",
            "details": f"Expected executable at {SERVER_EXECUTABLE}"
        }
    
    try:
        # Running the command as a list is the most secure method (prevents shell injection).
        # We use a short timeout (15s) for status checks but keep 120s for start/stop.
        timeout = 15 if action_key == 'details' else 120
        
        result = subprocess.run(
            command_args, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            check=True    # Raises CalledProcessError if the command exits non-zero
        )
        
        raw_output = result.stdout.strip()
        
        # Logic: Clean up terminal coloring
        cleaned_output = strip_ansi_codes(raw_output)

        return {
            "status": "success", 
            "message": f"'{action_key}' executed successfully.",
            "details": cleaned_output # Returns the cleaned output
        }
        
    except subprocess.CalledProcessError as e:
        # Command failed (e.g., pzserver returned an error code)
        return {
            "status": "error", 
            "message": f"Command failed (Exit Code {e.returncode}). Check script logic.",
            "details": e.stderr.strip() 
        }
    except subprocess.TimeoutExpired:
        # Command took too long to finish
        return {
            "status": "error", 
            "message": f"Command execution timed out after {timeout} seconds.",
            "details": "The command took too long to complete."
        }
    except Exception as e:
        # Other system errors (e.g., permission denied to execute the file)
        return {
            "status": "fatal_error", 
            "message": f"An unexpected system error occurred: {str(e)}",
            "details": f"Check permissions for executable: {SERVER_EXECUTABLE}"
        }


# --- API Endpoint for Server Details (GET) ---
@app.route('/api/details', methods=['GET'])
def get_server_details():
    """
    Triggers the 'pzserver dt' command, parses the raw output, and returns 
    structured JSON for the front-end.
    """
    command_result = run_server_command('details')
    
    if command_result['status'] == 'success':
        # If the command succeeded, parse the raw text in 'details'
        parsed_data = parse_details_output(command_result['details'])
        return jsonify({
            "status": "success",
            "message": command_result['message'],
            "details": parsed_data # Return the structured dictionary
        }), 200
    else:
        # If the command failed (error, timeout, not found), return the raw error object
        return jsonify(command_result), 500


# --- API Endpoint for Server Control (POST) ---
@app.route('/api/control', methods=['POST'])
def control_server():
    """
    Receives an action ('start', 'stop', 'restart') from the web client, 
    executes the corresponding pzserver command, and returns the result.
    """
    try:
        data = request.get_json()
        action = data.get('action')

        if action not in ['start', 'stop', 'restart']:
            return jsonify({
                "status": "client_error", 
                "message": "Invalid control action.",
                "details": "Valid actions are: start, stop, restart."
            }), 400  # HTTP 400 Bad Request

        response_data = run_server_command(action)
        
        # Determine the appropriate HTTP status code based on the command result
        http_status = 200 if response_data['status'] == 'success' else 500
        
        return jsonify(response_data), http_status

    except Exception as e:
        # Handles errors if the request body is not valid JSON
        return jsonify({
            "status": "fatal_error",
            "message": "Failed to process request.",
            "details": str(e)
        }), 500


# --- Minimal Test Route (Access this in your browser: http://<your-server-ip>:5000/status) ---
@app.route('/status')
def get_api_status():
    """Returns a simple JSON response to confirm the API is working."""
    return jsonify({
        "api_status": "Operational",
        "message": "Hello from Flask! Ready for PZ control."
    })


# --- Server Startup ---
if __name__ == '__main__':
    # 'host=0.0.0.0' allows external access (required for your web GUI)
    app.run(host='0.0.0.0', port=5000, debug=True)
