import re

def strip_ansi_codes(text):
    """
    Removes ANSI escape sequences (color codes) from a string.
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def parse_details_output(raw_output):
    """
    Parses the cleaned output and extracts key-value pairs from LinuxGSM details 
    into a flat dictionary.
    """
    parsed_data = {}
    lines = [strip_ansi_codes(line).strip() for line in raw_output.splitlines()]
    
    # List of keywords that indicate the entire line should be skipped
    SENSITIVE_LINE_KEYWORDS = ['password'] 

    for line in lines:
        if not line or ':' not in line:
            continue
            
        # Skip lines that contain sensitive keywords (like passwords)
        if any(keyword in line.lower() for keyword in SENSITIVE_LINE_KEYWORDS):
            continue

        try:
            # Use split(':', 1) to correctly separate key and value
            key, value = line.split(':', 1)
            
            # Key cleanup
            key = key.strip()
            # Clean up the status prefix if it exists, e.g., "[ OK ] Status" -> "Status"
            if key.startswith('[') and ']' in key:
                 key = key.split(']', 1)[-1].strip()

            # Value cleanup: FIX: Use simple strip() to PRESERVE internal spaces
            value = value.strip()
            
            # Normalize the Status key for main.py's consumption
            if key.lower() == 'status':
                key = 'Status'
            
            if key and value:
                parsed_data[key] = value

        except ValueError:
            continue

    # Ensure the required 'Status' key is present, even if unknown
    if 'Status' not in parsed_data:
        parsed_data['Status'] = 'UNKNOWN'
        
    return parsed_data


def parse_server_ini(ini_content):
    """
    Parses the INI content.
    Returns a dictionary with:
      - 'values': The key-value pairs of settings.
      - 'descriptions': The comments found above each key.
    """
    values = {}
    descriptions = {}
    current_comment = []
    
    for line in ini_content.splitlines():
        line = line.strip()
        
        # 1. Accumulate comments
        if line.startswith('#') or line.startswith(';'):
            # Remove the comment character and whitespace
            comment_text = line.lstrip('#; ').strip()
            current_comment.append(comment_text)
            continue
            
        # 2. Reset comments on empty lines (optional, but keeps descriptions tight)
        if not line:
            current_comment = []
            continue
            
        # 3. Parse Key=Value
        if '=' in line:
            try:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                values[key] = value
                
                # Assign collected comments to this key
                if current_comment:
                    descriptions[key] = "\n".join(current_comment)
                
                # Reset comments after assignment
                current_comment = []
            except ValueError:
                continue
                
    return {"values": values, "descriptions": descriptions}


def parse_ini_mod_lists(ini_config):
    """
    Extracts the list of ACTIVE (enabled) mods and their Workshop IDs from the 
    parsed server INI configuration. All mods returned are considered 'enabled'.
    
    Returns: A list of dicts, e.g., 
    [
        {"internal_id": "ModID1", "name": "Unknown Mod 1", "workshop_id": "12345", "enabled": True}, 
        ...
    ]
    """
    # Split the semicolon-separated strings into lists
    mod_ids = [m.strip() for m in ini_config.get('Mods', '').split(';') if m.strip()]
    workshop_ids = [w.strip() for w in ini_config.get('WorkshopItems', '').split(';') if w.strip()]
    
    active_mods_list = []
    
    # PZ requires Mods and WorkshopItems to be in the same order
    for i, mod_id in enumerate(mod_ids):
        workshop_id = workshop_ids[i] if i < len(workshop_ids) else "N/A"
        
        # We cannot know the actual Mod Name, only the Internal ID. 
        # We use the Internal ID as a placeholder name.
        active_mods_list.append({
            "internal_id": mod_id,
            "name": mod_id, # Placeholder Name: Using Internal ID
            "workshop_id": workshop_id,
            "enabled": True, # Source of truth is the INI, so they are active
        })
            
    return active_mods_list

# --- LUA PARSING ---
def parse_lua_value(val_str):
    val_str = val_str.strip().rstrip(',')
    if val_str == 'true': return True
    if val_str == 'false': return False
    if val_str.startswith('"') and val_str.endswith('"'): return val_str.strip('"')
    try:
        if '.' in val_str: return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str
