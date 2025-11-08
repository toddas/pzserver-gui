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
    parsed_data = {}
    lines = [strip_ansi_codes(line).strip() for line in raw_output.split('\n')]

    for string in lines:
        if string.__contains__(":"):
      
            if string.__contains__("password"):
                continue
            elif string.split(':')[1].strip(" ") == "":
                continue
            else:
                parsed_data[string.split(':')[0].strip(" ")] = re.sub(r"[\n\t\s]*", "", string.split(':')[1].strip())

    
    
    current_section_key = None
    # Initialize server status and ports list
    return parsed_data


