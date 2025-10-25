import re

def strip_ansi_codes(text):
    """Removes ANSI escape sequences (color codes) from a string."""
    # Pattern to match ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def parse_details_output(raw_output):
    """
    Parses the cleaned, multi-section output of the pzserver dt command
    into a structured dictionary and removes sensitive information.
    """
    # Keys to be REMOVED from the final JSON output for security reasons
    SENSITIVE_KEYS = [
        'serverpassword',
        'adminpassword',
        'password',
        'rconpassword',
        'master_password'
    ]

    lines = raw_output.strip().split('\n')
    parsed_data = {}
    current_section = None
    
    # --- CRITICAL: Find the main server status first ---
    server_status_match = re.search(r'status:\s+(STARTED|STOPPED|RESTARTING|STARTING|OFF|ONLINE|OFFLINE)', raw_output, re.IGNORECASE)
    
    if server_status_match:
        parsed_data['server_status'] = server_status_match.group(1).upper()
    else:
        parsed_data['server_status'] = 'UNKNOWN'
    # ----------------------------------------------------

    # Regex to find section headers and key-value pairs
    section_header_pattern = re.compile(r'^\s*([A-Za-z0-9_ -]+):\s*$')
    key_value_pattern = re.compile(r'^\s*([A-Za-z0-9_ -]+):\s*(.+?)\s*$')
    port_header_pattern = re.compile(r'DESCRIPTION\s+PORT\s+PROTOCOL\s+LISTEN')
    port_line_pattern = re.compile(r'^\s*(.+?)\s{2,}(\d+)\s{2,}(TCP|UDP)\s{2,}(.+?)\s*$')

    ports_list = []
    in_ports_section = False
    temp_nested_data = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for start of Ports table
        if port_header_pattern.search(line):
            current_section = 'ports'
            in_ports_section = True
            parsed_data[current_section] = ports_list
            continue
        
        # Handle Ports section
        if in_ports_section:
            port_match = port_line_pattern.match(line)
            if port_match:
                ports_list.append({
                    'description': port_match.group(1).strip(),
                    'port': port_match.group(2).strip(),
                    'protocol': port_match.group(3).strip(),
                    'listen': port_match.group(4).strip(),
                })
                continue
            elif section_header_pattern.match(line):
                in_ports_section = False
        
        # Check for new section headers
        section_match = section_header_pattern.match(line)
        if section_match:
            section_name = section_match.group(1).lower().replace(' ', '_')
            current_section = section_name
            if current_section not in parsed_data:
                parsed_data[current_section] = {}
                temp_nested_data = parsed_data[current_section]
            else:
                temp_nested_data = parsed_data[current_section]
            continue
            
        # Check for key-value pairs
        key_value_match = key_value_pattern.match(line)
        if key_value_match and current_section:
            key = key_value_match.group(1).lower().replace(' ', '_')
            value = key_value_match.group(2).strip()
            
            # --- SECURITY FILTERING ---
            if key in SENSITIVE_KEYS:
                # Replace the password with a masked value
                value = '****** (REDACTED)'
            # --------------------------

            # Add key-value pair to the current section
            temp_nested_data[key] = value

    return parsed_data