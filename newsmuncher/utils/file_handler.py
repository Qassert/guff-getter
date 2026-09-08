import json

def load_json(file_path):
    """Loads JSON data from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
def load_prompt(filepath):
    """Load the prompt template from an external text file."""
    try:
        with open(filepath, "r") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {filepath}")
        return None  # Or raise the exception, depending on your needs

def save_json(data, file_path):
    """Saves JSON data to a file."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

