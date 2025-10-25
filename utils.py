import re
import json

def strip_ansi_codes(text):
    """
    Removes ANSI escape sequences (color codes) from a string.
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def parse_details_output(raw_output):
    """
    Parses the cleaned output and extracts the main port from display_ip
    instead of relying on the complex ports table.
    """
    
    SENSITIVE_KEYS = [
        'user', 'admin_password', 'rcon_password', 'rconpassword', 
        'server_password', 'steamkey', 'steamapi', 
    ]
    
    lines = [strip_ansi_codes(line).strip() for line in raw_output.split('\n')]
    
    parsed_data = {}
    current_section_key = None
    
    # Initialize server status and ports list
    parsed_data['server_status'] = 'UNKNOWN'
    # Initialize with the main port and protocol for simple frontend rendering
    parsed_data['ports'] = [] 
    main_port = None
    main_protocol = "UDP/TCP" # Assume common protocols for main PZ port

    # --- 1. Pass: Extract Status and Key-Value Pairs ---
    for line in lines:
        if not line:
            continue
            
        line_lower = line.lower()

        # A. Status Extraction
        if line.lstrip().lower().startswith("status:"):
            status_word = line.split(':', 1)[1].strip().upper()
            if status_word:
                parsed_data['server_status'] = status_word
            continue 

        # B. Detect New Section Headers
        # Only interested in 'INTERNET IP' and similar main blocks
        if line.endswith(':') and not ':' in line[:-1]:
            section_name = line[:-1].strip().lower().replace(' ', '_')
            # Exclude headers that are just instructions
            if 'change_ports' not in section_name and 'useful_port' not in section_name:
                current_section_key = section_name
                if current_section_key not in parsed_data:
                    parsed_data[current_section_key] = {}
            continue
        
        # C. Detect Key-Value Pairs
        if ':' in line and current_section_key and current_section_key != 'ports':

            try:
                key, value = line.split(':', 1)
                
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # --- Security Filtering ---
                if key in SENSITIVE_KEYS:
                    value = '****** (REDACTED)'
                
                parsed_data[current_section_key][key] = value

                # --- Extract Port Directly ---
                if key == 'display_ip' and ':' in value:
                    try:
                        # Split by ':' and take the last part (the port)
                        main_port = value.split(':')[-1]
                    except Exception:
                        main_port = None # Handle errors gracefully

            except ValueError:
                pass

    # --- 2. Final Step: Populate Simple Ports List ---
    # Use the extracted port to populate the simple 'ports' list for the frontend
    if main_port and main_port.isdigit():
        parsed_data['ports'].append({
            'description': 'Game/Query Port',
            'port': main_port,
            'protocol': main_protocol,
            # We don't have the LISTEN status from the 'display_ip' line, so use a placeholder
            'listen': 'N/A' 
        })
    
    # --- 3. Final Cleanup: Remove empty sections ---
    for key in list(parsed_data.keys()):
        if isinstance(parsed_data[key], dict) and not parsed_data[key]:
            del parsed_data[key]
                
    return parsed_data