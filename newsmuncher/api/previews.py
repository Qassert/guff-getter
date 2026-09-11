from newsmuncher.utils.source_preprocessing import log_overlap
from newsmuncher.config import PROJECT_ROOT, PROMPT_FILE, TEMP_FILE, TEMP_SHIZZ_FILE
from fastapi import APIRouter, HTTPException, Request, Cookie, Body
from pydantic import BaseModel, Field
import json
import requests
import subprocess
import sys
import os
from uuid import uuid4
from newsmuncher.utils.clean_data import prepare_prompt, send_prompt, format_shizzalise_result, copy_edit_pass
from newsmuncher.utils.file_handler import load_prompt


from newsmuncher.services.image_generation import store, get_provider, build_image_prompt, IMAGE_FIELDS, recover_image, IMAGE_MODEL, IMAGE_QUALITY, IMAGE_SIZE, image_path

router = APIRouter()

ENTRIES_API_BASE_URL = os.getenv("ENTRIES_API_BASE_URL", "http://127.0.0.1:8000")


# ✅ 1. TEMP GET
@router.get("/temp_data")
def get_temp_data():
    if not os.path.exists(TEMP_FILE):
        raise HTTPException(status_code=404, detail="No temporary data available.")
    with open(TEMP_FILE, "r") as file:
        return json.load(file)

class NominationResponse(BaseModel):
    crazyReplacement1Title: str
    crazyReplacement1Extract: str


# ✅ 2. FINAL BANKING
@router.post("/confirm_data")
def confirm_temp_data(request: Request, rewrite_id: str | None = None, payload: NominationResponse | None = None):
    if rewrite_id:
        return bank_image_rewrite(request, rewrite_id, payload)
    owner = request.cookies.get('active_pet')
    if not owner:
        raise HTTPException(status_code=401, detail='No active pet selected.')
    # Compatibility for a pre-upgrade JSON preview: assign its stable identity
    # before any persistence call, then use the same nomination lifecycle.
    with store.transaction() as db:
        if not os.path.exists(TEMP_SHIZZ_FILE):
            raise HTTPException(status_code=404, detail='No temporary shizzalised data available.')
        with open(TEMP_SHIZZ_FILE) as file:
            data = json.load(file)
        rewrite_id = data.get('rewrite_id') or str(uuid4())
        row = db.execute('SELECT state FROM rewrites WHERE id=?', (rewrite_id,)).fetchone()
        if row:
            read_image_rewrite(db, rewrite_id, owner)
        else:
            data['rewrite_id'] = rewrite_id
            store.save(db, rewrite_id, dict(result=data, owner=owner, entry_id=None))
        with open(TEMP_SHIZZ_FILE, 'w') as file:
            json.dump(data, file)
    return bank_image_rewrite(request, rewrite_id, payload)

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
    generate_images: bool = False
    draft_session: str = Field(default="legacy", min_length=1, max_length=100)

@router.post("/shizzalise_data")
def shizzalise_data(payload: ShizzRequest, creationUser: str = Cookie(None), active_pet: str = Cookie(None)):
    if not active_pet:
        raise HTTPException(status_code=401, detail="No active pet selected.")
    source = payload.model_dump(exclude={'generate_images', 'draft_session'})
    rewrite_id = store.begin_draft({**source, 'creationUser': creationUser}, active_pet, payload.draft_session)
    with open(TEMP_FILE, "w") as f:
        json.dump({**source, "creationUser": creationUser}, f)

    prompt_template = prepare_prompt(source, 10, load_prompt(PROMPT_FILE))
    if not prompt_template:
        raise HTTPException(status_code=400, detail="Prompt preparation failed.")

    initial_response = send_prompt(prompt_template["full_prompt"])
    if not initial_response:
        raise HTTPException(status_code=500, detail="OpenAI generation failed.")

    log_overlap(prompt_template["preprocessing"], initial_response)

    result = format_shizzalise_result(initial_response)
    if not result:
        raise HTTPException(status_code=500, detail="Generated title or extract is invalid.")

    # Pass 2: copy-editing.  Receives only pass-1 output — never source text.
    # Falls back to the pass-1 result on any failure.
    polished = copy_edit_pass(result)
    if polished:
        result = polished

    full_result = {
        **source,
        **result,
        "creationUser": creationUser,
        "contenders": prompt_template.get("contenders", {})
    }

    full_result = store.complete_draft(rewrite_id, active_pet, full_result)
    if full_result is None:
        raise HTTPException(status_code=409, detail='Draft superseded by a newer rewrite.')
    # New drafts live only in the session's SQLite slot. Legacy JSON is not an archive.

    return full_result

# ✅ 5. GET SHIZZALISED RESULT
@router.get("/get_shizz_data")
def get_shizz_data():
    if not os.path.exists(TEMP_SHIZZ_FILE):
        raise HTTPException(status_code=404, detail="No shizzalised data found.")
    with open(TEMP_SHIZZ_FILE, "r") as f:
        return json.load(f)


class ImageRequest(BaseModel):
    rewrite_id: str


def read_image_rewrite(db, rewrite_id, owner, allow_discarded=False):
    try:
        state = store.read(db, rewrite_id, owner)
        if state.get('discarded') and not allow_discarded:
            raise HTTPException(status_code=410, detail='Draft discarded.')
        return state
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def persist_banked_image(state, metadata):
    response = requests.patch(
        f"{ENTRIES_API_BASE_URL}/entry/{state['entry_id']}/image",
        json={**metadata, 'rewrite_id': state['result']['rewrite_id']},
        cookies={'active_pet': state['owner']}, timeout=15)
    response.raise_for_status()


def sync_image_metadata(rewrite_id, owner):
    # Local success is already durable. DB synchronization must not lose the image.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, owner)
        if state['entry_id'] and not state.get('image_synced'):
            try:
                persist_banked_image(state, {key: state['result'][key] for key in IMAGE_FIELDS})
                state['image_synced'] = True
                store.save(db, rewrite_id, state)
            except requests.RequestException:
                # A subsequent image/status/bank request can retry metadata sync only.
                pass


@router.post('/generate_image')
def generate_image(payload: ImageRequest, active_pet: str = Cookie(None)):
    cached = None
    with store.transaction() as db:
        state = read_image_rewrite(db, payload.rewrite_id, active_pet)
        if state.get('generating'):
            raise HTTPException(status_code=409, detail='Rewrite is not ready.')
        if state['result'].get('image_url'):
            # Even partial legacy metadata must not trigger another paid image.
            defaults = dict(image_prompt=build_image_prompt(state['result']), image_model='unknown',
                            image_provider='unknown', image_generated_at=None)
            cached = {key: state['result'].get(key, defaults.get(key)) for key in IMAGE_FIELDS}
            state['result'].update(cached)
            store.save(db, payload.rewrite_id, state)
        else:
            prompt = build_image_prompt(state['result'])
            attempt = {**dict(prompt=prompt, model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE),
                       **(state.get('image_attempt') or {})}
            try:
                cached = recover_image(payload.rewrite_id, attempt)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if cached:
                state['result'].update(cached)
                state['image_attempt'] = {**attempt, 'status': 'complete'}
                store.save(db, payload.rewrite_id, state)
            elif state.get('image_attempt'):
                raise HTTPException(status_code=409, detail='Image attempt already started; no automatic paid retry.')
            else:
                # Commit before contacting OpenAI. Never clear this marker on failure.
                state['image_attempt'] = {**attempt, 'status': 'started'}
                store.save(db, payload.rewrite_id, state)
    if cached:
        sync_image_metadata(payload.rewrite_id, active_pet)
        return cached
    try:
        metadata = get_provider().generate_image(prompt, payload.rewrite_id)
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
            if state.get('discarded'):
                image_path(payload.rewrite_id).unlink(missing_ok=True)
                raise HTTPException(status_code=410, detail='Draft discarded; generated file removed.')
            state['result'].update(metadata)
            state['image_attempt']['status'] = 'complete'
            store.save(db, payload.rewrite_id, state)
    except Exception as exc:
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
            if state.get('discarded'):
                image_path(payload.rewrite_id).unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=502, detail='Image unavailable; your rewrite is unchanged. No automatic paid retry.') from exc
    sync_image_metadata(payload.rewrite_id, active_pet)
    return metadata


@router.get('/image_result/{rewrite_id}')
def get_image_result(rewrite_id: str, active_pet: str = Cookie(None)):
    # Read-only restoration: refreshing never calls a paid provider.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, active_pet)
        if not state['result'].get('image_url') or not all(k in state['result'] for k in IMAGE_FIELDS):
            attempt = {**dict(prompt=build_image_prompt(state['result']), model=IMAGE_MODEL),
                       **(state.get('image_attempt') or {})}
            try:
                recovered = recover_image(rewrite_id, attempt)
            except ValueError:
                recovered = None
            if recovered:
                state['result'].update(recovered)
                store.save(db, rewrite_id, state)
        if state['result'].get('image_url'):
            defaults = dict(image_prompt=build_image_prompt(state['result']), image_model='unknown',
                            image_provider='unknown', image_generated_at=None)
            for key, value in defaults.items():
                state['result'].setdefault(key, value)
            store.save(db, rewrite_id, state)
        result = state['result'].copy()
    if result.get('image_url'):
        sync_image_metadata(rewrite_id, active_pet)
    return result


def bank_image_rewrite(request, rewrite_id, payload=None):
    owner = request.cookies.get('active_pet')
    # Persist before HTTP: a timeout may mean Mongo committed successfully.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, owner)
        if state.get('generating'):
            raise HTTPException(status_code=409, detail='Rewrite is not ready.')
        if not state['entry_id']:
            state['nomination_pending'] = True
            store.save(db, rewrite_id, state)
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, owner)
        if state['entry_id'] and payload is not None and any(
                state['result'].get(key) != value for key, value in payload.model_dump().items()):
            try:
                response = requests.put(f"{ENTRIES_API_BASE_URL}/entry/{state['entry_id']}",
                    params=payload.model_dump(), cookies={'active_pet': owner}, timeout=15)
                response.raise_for_status()
                state['result'].update(payload.model_dump())
                store.save(db, rewrite_id, state)
            except requests.RequestException as exc:
                raise HTTPException(status_code=502, detail='Could not update nominated response.') from exc
        if not state['entry_id']:
            if payload is not None:
                state['result'].update(payload.model_dump())
            try:
                response = requests.post(f'{ENTRIES_API_BASE_URL}/create/',
                    json={**state['result'], 'image_owner': owner},
                    cookies={'active_pet': owner}, timeout=15)
                response.raise_for_status()
                state['entry_id'] = response.json()['id']
                state['result']['nominated'] = True
                state['result']['gallery_status'] = 'pending'
                state.pop('nomination_pending', None)
                state['image_synced'] = bool(state['result'].get('image_url'))
                store.save(db, rewrite_id, state)
            except requests.RequestException as exc:
                raise HTTPException(status_code=502, detail='Could not bank rewrite.') from exc
    if state['result'].get('image_url'):
        sync_image_metadata(rewrite_id, owner)
    # Only clear the matching shared preview, never a newer rewrite.
    if os.path.exists(TEMP_SHIZZ_FILE):
        with open(TEMP_SHIZZ_FILE) as f:
            current = json.load(f)
        if current.get('rewrite_id') == rewrite_id:
            os.remove(TEMP_SHIZZ_FILE)
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)
    return {'message': 'Data banked successfully!', 'nominated': True, 'rewrite_id': rewrite_id}
