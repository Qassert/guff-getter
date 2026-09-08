from newsmuncher.utils.source_preprocessing import log_overlap
from newsmuncher.config import PROJECT_ROOT, PROMPT_FILE, TEMP_FILE, TEMP_SHIZZ_FILE
from fastapi import APIRouter, HTTPException, Request, Cookie, Body
from pydantic import BaseModel
import json
import requests
import subprocess
import sys
import os
from newsmuncher.utils.clean_data import prepare_prompt, send_prompt, format_shizzalise_result
from newsmuncher.utils.file_handler import load_prompt


router = APIRouter()

ENTRIES_API_BASE_URL = os.getenv("ENTRIES_API_BASE_URL", "http://127.0.0.1:8000")


# ✅ 1. TEMP GET
@router.get("/temp_data")
def get_temp_data():
    if not os.path.exists(TEMP_FILE):
        raise HTTPException(status_code=404, detail="No temporary data available.")
    with open(TEMP_FILE, "r") as file:
        return json.load(file)

# ✅ 2. FINAL BANKING
@router.post("/confirm_data")
def confirm_temp_data(request: Request):
    if not os.path.exists(TEMP_SHIZZ_FILE):
        raise HTTPException(status_code=404, detail="No temporary shizzalised data available.")

    with open(TEMP_SHIZZ_FILE, "r") as file:
        data = json.load(file)

    active_pet = request.cookies.get("active_pet")
    if not active_pet:
        raise HTTPException(status_code=401, detail="No active pet selected.")

    try:
        print(data)
        response = requests.post(
            f"{ENTRIES_API_BASE_URL}/create/",
            json=data,
            cookies={"active_pet": active_pet}
        )
        print(response.status_code)
        response.raise_for_status()
        os.remove(TEMP_FILE)
        os.remove(TEMP_SHIZZ_FILE)
        return {"message": "Data banked successfully!"}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error posting data: {str(e)}")

# ✅ 3. SCRIPT TRIGGER
@router.get("/run_script/{script_name}")
def run_script(script_name: str):
    script_mapping = {
        "fetch_historicalFunny_from_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_historical_funny"],
        "fetch_wikipedia_into_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_wikipedia"],
        "fetch_poem_into_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_poem"],
        "fetch_people_into_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_people"],
        "process_data": [sys.executable, "-m", "newsmuncher.jobs.process_data"]
    }

    if script_name in script_mapping:
        result = subprocess.run(script_mapping[script_name], cwd=PROJECT_ROOT)
        if result.returncode == 0:
            return {"message": f"Script {script_name} executed successfully."}
        else:
            raise HTTPException(status_code=500, detail=f"Script {script_name} failed.")
    
    raise HTTPException(status_code=400, detail="Invalid script name.")

# ✅ 4. SHIZZALISE ENTRY TO TEMP + CALL OPENAI
class ShizzRequest(BaseModel):
    title: str
    description: str
    extract: str

@router.post("/shizzalise_data")
def shizzalise_data(payload: ShizzRequest, creationUser: str = Cookie(None)):
    with open(TEMP_FILE, "w") as f:
        json.dump({**payload.dict(), "creationUser": creationUser}, f)

    prompt_template = prepare_prompt(payload.dict(), 10, load_prompt(PROMPT_FILE))
    if not prompt_template:
        raise HTTPException(status_code=400, detail="Prompt preparation failed.")

    initial_response = send_prompt(prompt_template["full_prompt"])
    if not initial_response:
        raise HTTPException(status_code=500, detail="OpenAI generation failed.")

    log_overlap(prompt_template["preprocessing"], initial_response)

    result = format_shizzalise_result(initial_response)
    if not result:
        raise HTTPException(status_code=500, detail="Generated title or extract is invalid.")

    full_result = {
        **payload.dict(),
        **result,
        "creationUser": creationUser
    }

    with open(TEMP_SHIZZ_FILE, "w") as f:
        json.dump(full_result, f)

    return full_result

# ✅ 5. GET SHIZZALISED RESULT
@router.get("/get_shizz_data")
def get_shizz_data():
    if not os.path.exists(TEMP_SHIZZ_FILE):
        raise HTTPException(status_code=404, detail="No shizzalised data found.")
    with open(TEMP_SHIZZ_FILE, "r") as f:
        return json.load(f)
