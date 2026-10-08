def load_prompt(filepath):
    """Load the prompt template from an external text file."""
    try:
        with open(filepath, "r") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {filepath}")
        return None  # Or raise the exception, depending on your needs
