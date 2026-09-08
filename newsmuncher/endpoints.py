# urls_and_endpoints.py

# Base URLs
REUSABLE_API_BASE_URL = "http://127.0.0.1:8000/reusable"
MAIN_API_BASE_URL = "http://127.0.0.1:8000"  # ✅ Main API at root

# Reusable API Endpoints
REUSABLE_ENDPOINTS = {
    "get_all": f"{REUSABLE_API_BASE_URL}/get_all/",
    "add_single": f"{REUSABLE_API_BASE_URL}/add/",
    "add_bulk": f"{REUSABLE_API_BASE_URL}/add_bulk/",
    "get_one": f"{REUSABLE_API_BASE_URL}/get_one/",
    "increment_usage": lambda entry_id: f"{REUSABLE_API_BASE_URL}/increment_usage/{entry_id}"
}

# Main API Endpoints
MAIN_ENDPOINTS = {
    "create": f"{MAIN_API_BASE_URL}/create/",  # ✅ Adjusted to root
    "get_all": f"{MAIN_API_BASE_URL}/entries/",
    "get_entry": lambda entry_id: f"{MAIN_API_BASE_URL}/entry/{entry_id}",
    "update_entry": lambda entry_id: f"{MAIN_API_BASE_URL}/entry/{entry_id}",
    "delete_entry": lambda entry_id: f"{MAIN_API_BASE_URL}/entry/{entry_id}"
}

