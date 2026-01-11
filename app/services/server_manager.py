import subprocess
import os
import logging
import random
from app.utils.parsers import strip_ansi_codes, parse_details_output, parse_server_ini, parse_ini_mod_lists
from app.services.file_manager import update_server_ini_key

logger = logging.getLogger('pzserver_api')

#CONSTANTS
SERVER_SCRIPT = "/home/pzserver/server/pzserver"
SERVER_USER = "pzserver"
APP_USER = "pzserver-runner"
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
      
        logger.debug(f"Command '{action_key}' succeeded. Raw output length: {len(raw_output)}")
        output = strip_ansi_codes(raw_output)
        output = parse_details_output(output)
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
        save_name = config['values'].get('SaveName', 'pzserver') # Default fallback (config is {values:..., descriptions:...})
        
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
    
    parsed_data = parse_server_ini(ini_content)
    ini_config = parsed_data.get('values', {}) # Extract only the values for logic
    active_mods_list = parse_ini_mod_lists(ini_config)
    
    return active_mods_list

def perform_reset(reset_type):
    """
    Handles Soft and Hard resets.
    """
    if reset_type not in ['soft', 'hard']:
        return {"status": "error", "message": "Invalid reset type"}, 400

    save_name, save_path = get_save_info()
    if not save_path:
         return {"status": "error", "message": "Could not determine Save Path from INI."}, 500

    command = []
    messages = []
    
    if reset_type == 'soft':
        logger.info(f"Performing SOFT reset on: {save_path}")
        cmd_str = f"rm -f {save_path}/zpop*.bin {save_path}/map_t.bin"
        command = ['sudo', '-u', SERVER_USER, 'sh', '-c', cmd_str]
        messages.append("Zombies and loot timers wiped.")
        
    elif reset_type == 'hard':
        new_reset_id = random.randint(100000000, 999999999)
        if update_server_ini_key(SERVER_CONFIG_PATH, "ResetID", new_reset_id):
             logger.info(f"Updated ResetID to {new_reset_id}")
             messages.append(f"ResetID updated to {new_reset_id} (Clients forced to resync).")
        else:
             logger.warning("Could not update ResetID. Clients might see map glitches.")

        logger.warning(f"Performing HARD reset (WIPE) on: {save_path}")
        command = ['sudo', '-u', SERVER_USER, 'rm', '-rf', save_path]
        messages.append("World save folder deleted.")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return {
            "status": "success",
            "message": f"{reset_type.capitalize()} reset complete.",
            "details": " | ".join(messages) + f"\nOutput: {result.stdout}"
        }, 200

    except subprocess.CalledProcessError as e:
        return {
            "status": "error", 
            "message": "Reset command failed.",
            "details": e.stderr
        }, 500
    except Exception as e:
        logger.exception("Reset exception")
        return {"status": "error", "message": str(e)}, 500
