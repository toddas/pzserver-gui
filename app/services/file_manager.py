import re
import logging
from app.utils.parsers import parse_lua_value

logger = logging.getLogger('pzserver_api')

def read_sandbox_vars(file_path):
    """
    Skaito SandboxVars.lua ir grąžina objektą su reikšmėmis IR aprašymais iš komentarų.
    Return structure: { "values": {...}, "descriptions": {...} }
    """
    values = {}
    descriptions = {}
    
    # Stack'ai sekimui, kurioje lentelėje esame
    val_stack = [values]
    desc_stack = [descriptions]
    
    current_comment = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            stripped = line.strip()
            
            # 1. Kaupiame komentarus (-- ...)
            if stripped.startswith('--'):
                comment_text = stripped[2:].strip()
                current_comment.append(comment_text)
                continue
            
            # 2. Jei tuščia eilutė, nuresetiname komentarus (paprastai komentarai yra tiesiai virš kintamojo)
            if not stripped:
                current_comment = []
                continue

            # 3. Lentelės pradžia (pvz., ZombieLore = {)
            if stripped.endswith('{'):
                key_part = stripped.split('=')[0].strip()
                # Atmetame 'SandboxVars' šakninį raktą, nes mes jau esame šaknyje
                if key_part == 'SandboxVars':
                    val_stack = [values]
                    desc_stack = [descriptions]
                else:
                    new_val_dict = {}
                    new_desc_dict = {}
                    
                    val_stack[-1][key_part] = new_val_dict
                    val_stack.append(new_val_dict)
                    
                    desc_stack[-1][key_part] = new_desc_dict
                    desc_stack.append(new_desc_dict)
                
                # Komentarai virš lentelės priskiriami pačiai lentelei (jei reiktų), bet kol kas išvalome
                current_comment = []
                continue
            
            # 4. Lentelės pabaiga (})
            if stripped.startswith('}'):
                if len(val_stack) > 1:
                    val_stack.pop()
                    desc_stack.pop()
                current_comment = []
                continue
            
            # 5. Kintamojo priskyrimas (Key = Value,)
            if '=' in stripped:
                parts = stripped.split('=', 1)
                key = parts[0].strip()
                val_str = parts[1].strip()
                
                # Išsaugome reikšmę
                val = parse_lua_value(val_str)
                val_stack[-1][key] = val
                
                # Išsaugome aprašymą, jei radome komentarų
                if current_comment:
                    desc_stack[-1][key] = "\n".join(current_comment)
                
                current_comment = [] # Reset
                
        return {"values": values, "descriptions": descriptions}
        
    except Exception as e:
        logger.error(f"Error parsing Lua file: {e}")
        return {"values": {}, "descriptions": {}}


def update_sandbox_vars_file(file_path, new_data):
    """
    Atnaujina Lua failo eilutes pakeisdamas reikšmes iš new_data.
    FIX: Pataisyta logika, kad nesugadintų eilučių su kableliais viduje (pvz. WorldItemRemovalList).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        output_lines = []
        path_stack = [] 
        
        # Regex raktui surasti: (Indentas)(Raktas)( = )
        # Mes nebebandome pagauti "Value" su regex, nes tai per sudėtinga su kableliais ir kabutėmis.
        # Vietoj to, mes tiesiog tikriname pradžią.
        key_pattern = re.compile(r'^(\s*)([a-zA-Z0-9_]+)(\s*=\s*)')

        for line in lines:
            clean_line = line.strip()
            
            # 1. Block start (Nested tables)
            match_block_start = re.match(r'^\s*([a-zA-Z0-9_]+)\s*=\s*\{', clean_line)
            if match_block_start:
                key = match_block_start.group(1)
                if key != 'SandboxVars':
                    path_stack.append(key)
                output_lines.append(line)
                continue
                
            # 2. Block end
            if clean_line.startswith('}'):
                if path_stack:
                    path_stack.pop()
                output_lines.append(line)
                continue
            
            # 3. Key = Value
            match_key = key_pattern.match(line)
            if match_key:
                indent = match_key.group(1)
                key = match_key.group(2)
                separator = match_key.group(3) # " = "
                
                # Nustatome dabartinį kontekstą (ar mes lentelės viduje?)
                current_context = new_data
                for path_key in path_stack:
                    current_context = current_context.get(path_key, {})
                
                # Jei turime naują reikšmę šiam raktui
                if key in current_context:
                    new_val = current_context[key]
                    
                    # Suformuojame naują Lua reikšmę
                    if isinstance(new_val, bool):
                        lua_val = 'true' if new_val else 'false'
                    elif isinstance(new_val, str):
                        # Dvigubos kabutės stringams
                        lua_val = f'"{new_val}"'
                    else:
                        lua_val = str(new_val)
                    
                    # Išsaugome originalų kablelį ir komentarą
                    # Randame, kur baigiasi senoji "Key = " dalis
                    rest_of_line = line[match_key.end():]
                    
                    # Tikriname, ar senoji eilutė turėjo kablelį gale (prieš komentarą)
                    # Paprastas būdas: pažiūrėti, ar yra kablelis prieš "--"
                    comment_start = rest_of_line.find('--')
                    has_comma = False
                    
                    content_part = rest_of_line if comment_start == -1 else rest_of_line[:comment_start]
                    if ',' in content_part:
                        # Dauguma eilučių PZ confige baigiasi kableliu
                        has_comma = True
                    
                    # Atkuriame komentarą, jei jis buvo
                    comment = ""
                    if comment_start != -1:
                        comment = rest_of_line[comment_start:].rstrip()
                    
                    # Konstruojame naują eilutę
                    comma_str = "," if has_comma else ""
                    # Jei yra komentaras, pridedame tarpą prieš jį
                    comment_str = f" {comment}" if comment else ""
                    
                    new_line = f"{indent}{key}{separator}{lua_val}{comma_str}{comment_str}\n"
                    output_lines.append(new_line)
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)
                
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
            
        return True
    except Exception as e:
        logger.error(f"Error writing Lua file: {e}")
        raise e


def update_server_ini_key(file_path, key_to_update, new_value):
    """
    Updates a specific key in a standard key=value INI file.
    Used for updating ResetID during Hard Reset.
    """
    try:
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        output_lines = []
        key_found = False
        
        for line in lines:
            stripped = line.strip()
            # Check if this line starts with our key
            if stripped.startswith(f"{key_to_update}=") or stripped.startswith(f"{key_to_update} ="):
                # Replace the line with the new value
                output_lines.append(f"{key_to_update}={new_value}\n")
                key_found = True
            else:
                output_lines.append(line)
        
        # If the key wasn't found, append it to the end (usually good practice for PZ ini)
        if not key_found:
            output_lines.append(f"\n{key_to_update}={new_value}\n")
            
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to update INI key {key_to_update}: {e}")
        # Don't raise, just log, so the reset can continue even if this fails
        return False


def update_server_ini_file(file_path, new_data):
    """
    Atnaujina serverio INI failą pagal pateiktą žodyną (new_data).
    Išlaiko komentarus ir failo struktūrą.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        output_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Praleidžiame tuščias eilutes ar komentarus (juos tiesiog įrašome atgal)
            if not stripped or stripped.startswith('#') or stripped.startswith('--'):
                output_lines.append(line)
                continue
            
            if '=' in stripped:
                # Atskiriame raktą nuo reikšmės
                parts = stripped.split('=', 1)
                key = parts[0].strip()
                
                # Jei šis raktas yra mūsų atnaujinimų sąraše, pakeičiame reikšmę
                if key in new_data:
                    new_val = new_data[key]
                    
                    # Konvertuojame tipus į string
                    if isinstance(new_val, bool):
                        val_str = 'true' if new_val else 'false'
                    else:
                        val_str = str(new_val)
                    
                    # Suformuojame naują eilutę
                    output_lines.append(f"{key}={val_str}\n")
                else:
                    # Jei rakto nėra pakeitimuose, paliekame seną
                    output_lines.append(line)
            else:
                output_lines.append(line)
                
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
            
        return True
    except Exception as e:
        logger.error(f"Error updating INI file: {e}")
        raise e
