from newsmuncher.utils.source_preprocessing import log_overlap
from newsmuncher.config import (PROJECT_ROOT, PROMPT_FILE, TEMP_FILE, TEMP_SHIZZ_FILE,
    GENERATED_NARRATION_DIR)
from fastapi import APIRouter, HTTPException, Request, Cookie
from pydantic import BaseModel, Field
from openai import BadRequestError
import json
import requests
import subprocess
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4, UUID
from bson import ObjectId
from newsmuncher.utils.clean_data import prepare_prompt, send_prompt, format_shizzalise_result, copy_edit_pass, claim_used_words
from newsmuncher.utils.file_handler import load_prompt
from newsmuncher.services.word_shuffle import WordClaimConflict
from newsmuncher.services.rewrite_title import final_title


from newsmuncher.services.image_generation import store, choose_image_style, get_provider, build_image_prompt, IMAGE_FIELDS, recover_image, IMAGE_MODEL, IMAGE_QUALITY, IMAGE_SIZE, image_path, DefinitiveImageFailure

router = APIRouter()

ENTRIES_API_BASE_URL = os.getenv("ENTRIES_API_BASE_URL", "http://127.0.0.1:8000")


def safe_provider_failure(exc):
    """Small diagnostic subset only; never persist request/auth/full response data."""
    body = getattr(exc, 'body', None)
    error = body.get('error', body) if isinstance(body, dict) else {}
    def text(value, limit):
        if not isinstance(value, str):
            return None
        return ' '.join(value.split())[:limit]
    return {
        'failure_category': type(exc).__name__,
        'failure_http_status': getattr(exc, 'status_code', None),
        'failure_code': text(error.get('code') if isinstance(error, dict) else None, 80),
        'failure_param': text(error.get('param') if isinstance(error, dict) else None, 80),
        'failure_message': text(error.get('message') if isinstance(error, dict) else None, 240)
                           or 'Provider rejected the image request.',
    }

def entries_collection():
    from newsmuncher.api.entries import collection
    return collection


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
        "fetch_dating_from_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_historical_funny", "dating"],
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

    result = dict(result)
    result['crazyReplacement1Title'] = final_title(
        result['crazyReplacement1Extract'],
        result['crazyReplacement1Title'],
    )

    full_result = {
        **source,
        **result,
        "creationUser": creationUser,
        "contenders": prompt_template.get("contenders", {})
    }

    try:
        full_result = store.complete_draft(
            rewrite_id,
            active_pet,
            full_result,
            before_save=lambda: claim_used_words(prompt_template.get('contenders', {}), result),
        )
    except WordClaimConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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


def _owned_image_ids(rewrite_id, state):
    """Return only UUID image keys recorded in this server-owned rewrite state."""
    owned = {rewrite_id}
    def add(value):
        try:
            owned.add(str(UUID(str(value))))
        except (ValueError, TypeError, AttributeError):
            pass
    result = state.get('result') or {}
    url = result.get('image_url', '')
    if isinstance(url, str) and url.startswith('/generated-images/') and url.endswith('.png'):
        add(url.removeprefix('/generated-images/').removesuffix('.png'))
    for field in ('image_attempt', 'image_redo'):
        add((state.get(field) or {}).get('image_id'))
    for field in ('image_attempt_history', 'image_redo_history'):
        for attempt in state.get(field) or []:
            add((attempt or {}).get('image_id'))
    for video in [state.get('video'), *(state.get('video_history') or [])]:
        add(((video or {}).get('end_frame') or {}).get('image_id'))
    return owned


@router.delete('/creation/{rewrite_id}')
def delete_creation(rewrite_id: str, active_pet: str = Cookie(None)):
    """Delete one owner-checked rewrite and only its deterministically owned media."""
    if not active_pet:
        raise HTTPException(401, 'No active pet selected.')
    try:
        key = str(UUID(rewrite_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(404, 'Creation unavailable.') from None
    if key != rewrite_id:
        raise HTTPException(404, 'Creation unavailable.')

    collection = entries_collection()
    entry = None
    with store.transaction() as db:
        state = read_image_rewrite(db, key, active_pet, allow_discarded=True)
        if state.get('deleted'):
            raise HTTPException(410, 'Creation already deleted.')
        ownership = {'rewrite_id': key, '$or': [
            {'image_owner': active_pet},
            {'image_owner': {'$exists': False}, 'creationUser': active_pet},
        ]}
        entry_id = state.get('entry_id')
        if entry_id:
            if not ObjectId.is_valid(entry_id):
                raise HTTPException(409, 'Creation identity is invalid; nothing was deleted.')
        entries = list(collection.find(ownership).limit(2))
        if len(entries) > 1:
            raise HTTPException(409, 'Creation identity is ambiguous; nothing was deleted.')
        entry = entries[0] if entries else None
        if entry and entry_id and entry['_id'] != ObjectId(entry_id):
            raise HTTPException(409, 'Creation identity does not match; nothing was deleted.')
        image_ids = _owned_image_ids(key, state)
        if entry:
            result = collection.delete_one({'_id': entry['_id'], **ownership})
            if result.deleted_count != 1:
                raise HTTPException(409, 'Creation changed while deletion was requested.')
        # A tombstone prevents late image/video workers from resurrecting this UUID.
        store.save(db, key, {'owner': active_pet, 'entry_id': None, 'discarded': True,
                             'deleted': True, 'result': {'rewrite_id': key}})
        db.execute('DELETE FROM draft_slots WHERE owner=? AND rewrite_id=?', (active_pet, key))

    failures = []
    if entry:
        try:
            from newsmuncher.services.jingles import service as jingles
            jingles.retire_deleted(collection, entry)
        except Exception:
            failures.append('jingle')
        narration = GENERATED_NARRATION_DIR / f"{entry['_id']}.mp3"
        try:
            if narration.is_file() and not narration.is_symlink():
                narration.unlink()
        except OSError:
            failures.append('narration')
    for image_id in image_ids:
        path = image_path(image_id)
        try:
            if path.is_file() and not path.is_symlink():
                path.unlink()
        except OSError:
            failures.append(f'image:{image_id}')
    try:
        from newsmuncher.services.video import service as videos
        videos.remove_local_media(key)
    except (OSError, ValueError):
        failures.append('video')
    if os.path.exists(TEMP_SHIZZ_FILE):
        try:
            with open(TEMP_SHIZZ_FILE) as file:
                current = json.load(file)
            if current.get('rewrite_id') == key:
                os.remove(TEMP_SHIZZ_FILE)
        except (OSError, ValueError, TypeError):
            failures.append('temporary state')
    if failures:
        raise HTTPException(500, 'Creation deleted, but some local media needs operator cleanup: '
                            + ', '.join(failures))
    return {'deleted': True, 'rewrite_id': key}


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
                persist_banked_image(state, {key: state['result'].get(key) for key in IMAGE_FIELDS})
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
                            image_provider='unknown', image_generated_at=None, image_style=None)
            cached = {key: state['result'].get(key, defaults.get(key)) for key in IMAGE_FIELDS}
            state['result'].update(cached)
            store.save(db, payload.rewrite_id, state)
        else:
            prompt = build_image_prompt(state['result'])
            attempt = {**dict(image_id=payload.rewrite_id, prompt=prompt, model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE),
                       **(state.get('image_attempt') or {})}
            try:
                cached = recover_image(attempt.get('image_id', payload.rewrite_id), attempt)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if cached:
                state['result'].update(cached)
                state['image_attempt'] = {**attempt, 'status': 'complete'}
                store.save(db, payload.rewrite_id, state)
            elif state.get('image_attempt'):
                raise HTTPException(status_code=409, detail={
                    'code': 'image_outcome_uncertain',
                    'message': 'Previous image generation had an uncertain outcome.',
                    'attempt_id': state['image_attempt'].get('image_id'),
                    'rewrite_id': payload.rewrite_id,
                })
            else:
                # Commit before contacting OpenAI. Never clear this marker on failure.
                image_style = choose_image_style()
                prompt = build_image_prompt(state['result'], image_style)
                attempt.update(prompt=prompt, image_style=image_style, stage='main',
                               created_at=datetime.now(timezone.utc).isoformat())
                state['image_attempt'] = {**attempt, 'status': 'started'}
                store.save(db, payload.rewrite_id, state)
    if cached:
        sync_image_metadata(payload.rewrite_id, active_pet)
        return cached
    while True:
        try:
            attempt['provider_call_entered_at'] = datetime.now(timezone.utc).isoformat()
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                if (state.get('image_attempt') or {}).get('image_id') == attempt['image_id']:
                    state['image_attempt'].update(attempt)
                    store.save(db, payload.rewrite_id, state)
            metadata = get_provider().generate_image(attempt['prompt'], attempt['image_id'])
            attempt['provider_response_received_at'] = datetime.now(timezone.utc).isoformat()
            metadata['image_style'] = attempt['image_style']
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                if state.get('discarded'):
                    image_path(attempt['image_id']).unlink(missing_ok=True)
                    raise HTTPException(status_code=410, detail='Draft discarded; generated file removed.')
                state['result'].update(metadata)
                state['image_attempt'].update(attempt, status='complete',
                    persistence_completed_at=datetime.now(timezone.utc).isoformat())
                store.save(db, payload.rewrite_id, state)
            break
        except DefinitiveImageFailure as exc:
            terminal = False
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                current = state.get('image_attempt') or {}
                if current.get('image_id', payload.rewrite_id) != attempt['image_id']:
                    raise HTTPException(409, 'Image attempt changed; no automatic paid retry.') from exc
                current['status'] = 'definitive_failed'
                if current.get('retry_count', 0) >= 1:
                    state['image_attempt'] = current
                    store.save(db, payload.rewrite_id, state)
                    terminal = True
                else:
                    state.setdefault('image_attempt_history', []).append(current)
                    attempt = {**current, 'image_id': str(uuid4()), 'status': 'started', 'retry_count': 1,
                               'stage': 'main', 'created_at': datetime.now(timezone.utc).isoformat()}
                    for field in ('provider_call_entered_at', 'provider_response_received_at',
                                  'persistence_completed_at', 'failure_category', 'failure_message'):
                        attempt.pop(field, None)
                    state['image_attempt'] = attempt
                    store.save(db, payload.rewrite_id, state)  # Retry claim precedes the second paid call.
            if terminal:
                raise HTTPException(422, 'Image generation failed twice. Use REDO IMAGE to try again.') from exc
        except BadRequestError as exc:
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                current = state.get('image_attempt') or {}
                if current.get('image_id') == attempt['image_id']:
                    current.update(status='definitive_failed', **safe_provider_failure(exc))
                    store.save(db, payload.rewrite_id, state)
            raise HTTPException(422, 'Image request was rejected by the provider; no automatic retry.') from exc
        except Exception as exc:
            with store.transaction() as db:
                state = read_image_rewrite(db, payload.rewrite_id, active_pet, allow_discarded=True)
                if state.get('discarded'):
                    image_path(attempt['image_id']).unlink(missing_ok=True)
                current = state.get('image_attempt') or {}
                if current.get('image_id') == attempt['image_id']:
                    current.update(status='uncertain', failure_category=type(exc).__name__,
                                   failure_message=f'Image provider or local persistence raised {type(exc).__name__}.')
                    store.save(db, payload.rewrite_id, state)
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(status_code=502, detail='Image outcome uncertain. Use REDO IMAGE only if you choose to make another paid attempt.') from exc
    sync_image_metadata(payload.rewrite_id, active_pet)
    return metadata


class RedoImageRequest(ImageRequest):
    previous_image_url: str | None = Field(default=None, max_length=300)
    replace_nomination: bool = False


class UncertainImageRetryRequest(ImageRequest):
    attempt_id: UUID
    confirmed: bool


@router.post('/retry_uncertain_image')
def retry_uncertain_image(payload: UncertainImageRetryRequest, active_pet: str = Cookie(None)):
    """Spend once only after an owner explicitly accepts an uncertain prior outcome."""
    if not payload.confirmed:
        raise HTTPException(400, 'Explicit retry confirmation is required.')
    with store.transaction() as db:
        state = read_image_rewrite(db, payload.rewrite_id, active_pet)
        if state['result'].get('image_url'):
            return {key: state['result'].get(key) for key in IMAGE_FIELDS}
        unresolved_redo = state.get('image_redo') or {}
        if unresolved_redo and unresolved_redo.get('status') != 'complete':
            raise HTTPException(409, 'A separate image replacement attempt is unresolved; operator review is required.')
        previous = state.get('image_attempt') or {}
        if str(previous.get('image_id')) != str(payload.attempt_id):
            raise HTTPException(409, 'Image attempt changed; retry authorisation was not used.')
        if previous.get('status') not in ('started', 'uncertain'):
            raise HTTPException(409, 'This image attempt is not eligible for uncertain-outcome recovery.')
        try:
            recovered = recover_image(previous['image_id'], previous)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        if recovered:
            state['result'].update(recovered)
            state['image_attempt'] = {**previous, 'status': 'complete'}
            store.save(db, payload.rewrite_id, state)
            return recovered
        state.setdefault('image_attempt_history', []).append({
            **previous, 'status': 'superseded_by_confirmed_retry'
        })
        style = choose_image_style()
        attempt = dict(image_id=str(uuid4()), image_style=style,
                       prompt=build_image_prompt(state['result'], style),
                       model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE,
                       status='started', stage='main', retry_of=previous['image_id'],
                       created_at=datetime.now(timezone.utc).isoformat(),
                       confirmed_at=datetime.now(timezone.utc).isoformat())
        # This transaction is the single-use claim. A concurrent/replayed request
        # can no longer match payload.attempt_id and therefore cannot spend again.
        state['image_attempt'] = attempt
        store.save(db, payload.rewrite_id, state)
    try:
        attempt['provider_call_entered_at'] = datetime.now(timezone.utc).isoformat()
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            if (state.get('image_attempt') or {}).get('image_id') == attempt['image_id']:
                state['image_attempt'].update(attempt)
                store.save(db, payload.rewrite_id, state)
        metadata = get_provider().generate_image(attempt['prompt'], attempt['image_id'])
        attempt['provider_response_received_at'] = datetime.now(timezone.utc).isoformat()
        metadata['image_style'] = attempt['image_style']
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') != attempt['image_id']:
                raise HTTPException(409, 'Image attempt changed; generated result was not attached.')
            state['result'].update(metadata)
            current.update(attempt, status='complete',
                           persistence_completed_at=datetime.now(timezone.utc).isoformat())
            store.save(db, payload.rewrite_id, state)
    except DefinitiveImageFailure as exc:
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='definitive_failed', failure_category=type(exc).__name__,
                               failure_message='Provider returned no usable image.')
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(422, 'Confirmed image retry failed definitively; no further retry was submitted.') from exc
    except BadRequestError as exc:
        # An HTTP 400 is a definite provider response, not an ambiguous transport
        # outcome. Preserve the claim and require a fresh explicit user decision.
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='definitive_failed', **safe_provider_failure(exc))
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(422, 'Confirmed image retry was rejected by the provider; no automatic retry.') from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_attempt') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='uncertain', failure_category=type(exc).__name__,
                               failure_message=f'Image provider or local persistence raised {type(exc).__name__}.')
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(502, 'Confirmed image retry outcome is uncertain; no automatic retry.') from exc
    sync_image_metadata(payload.rewrite_id, active_pet)
    return metadata


def finish_image_redo(db, rewrite_id, state, metadata):
    state['result'].update(metadata)
    state['image_redo']['status'] = 'complete'
    state['image_synced'] = False
    # Keep historical claims/files as evidence, but never pair old video with new image.
    if state.get('video'):
        state['video_detached'] = True
    store.save(db, rewrite_id, state)


@router.post('/redo_image')
def redo_image(payload: RedoImageRequest, active_pet: str = Cookie(None)):
    with store.transaction() as db:
        state = read_image_rewrite(db, payload.rewrite_id, active_pet)
        nominated = bool(state.get('entry_id') or state.get('nomination_pending') or state['result'].get('nominated'))
        if nominated and not payload.replace_nomination:
            raise HTTPException(409, 'Nominated images cannot be replaced.')
        previous = state.get('image_redo')
        if previous and previous['previous_image_url'] == payload.previous_image_url:
            if previous['status'] == 'complete':
                return {key: state['result'].get(key) for key in IMAGE_FIELDS}
            raise HTTPException(409, 'Replacement attempt already started; no paid retry.')
        if previous and previous['status'] != 'complete':
            raise HTTPException(409, 'Replacement needs operator review; no paid retry.')
        current_url = state['result'].get('image_url')
        main_attempt = state.get('image_attempt') or {}
        if not current_url and main_attempt.get('status') in ('started', 'uncertain'):
            raise HTTPException(409, 'Main image outcome is uncertain; use the explicit confirmed recovery flow.')
        if state.get('generating') or (current_url and current_url != payload.previous_image_url):
            raise HTTPException(409, 'Current saved image required.')
        if not current_url and (payload.previous_image_url is not None or not state.get('image_attempt')):
            raise HTTPException(409, 'A terminal image attempt is required.')
        style = choose_image_style(exclude=state['result'].get('image_style'))
        attempt = dict(image_id=str(uuid4()), previous_image_url=payload.previous_image_url,
                       image_style=style, prompt=build_image_prompt(state['result'], style),
                       model=IMAGE_MODEL, quality=IMAGE_QUALITY, size=IMAGE_SIZE, status='started')
        if previous:
            state.setdefault('image_redo_history', []).append(previous)
        state['image_redo'] = attempt
        store.save(db, payload.rewrite_id, state)  # Permanent claim before the paid call.
    try:
        metadata = get_provider().generate_image(attempt['prompt'], attempt['image_id'])
        metadata['image_style'] = attempt['image_style']
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            # A GET can recover this file before the worker returns. Never overwrite
            # a newer replacement (or a nomination) after such recovery.
            if state['image_redo']['image_id'] != attempt['image_id'] or state['image_redo']['status'] == 'complete':
                return {key: state['result'].get(key) for key in IMAGE_FIELDS}
            finish_image_redo(db, payload.rewrite_id, state, metadata)
        if nominated:
            sync_image_metadata(payload.rewrite_id, active_pet)
            from newsmuncher.services.video import service as videos
            videos.replace(entries_collection(), payload.rewrite_id, active_pet)
        return metadata
    except BadRequestError as exc:
        with store.transaction() as db:
            state = read_image_rewrite(db, payload.rewrite_id, active_pet)
            current = state.get('image_redo') or {}
            if current.get('image_id') == attempt['image_id']:
                current.update(status='definitive_failed', **safe_provider_failure(exc))
                store.save(db, payload.rewrite_id, state)
        raise HTTPException(422, 'Replacement image was rejected by the provider; no automatic retry.') from exc
    except Exception as exc:
        # Preserve the old image and permanent attempt, including uncertain outcomes.
        raise HTTPException(502, 'Replacement unavailable; old image retained. No automatic paid retry.') from exc


@router.get('/loading_images')
def loading_images(active_pet: str = Cookie(None)):
    """Owner-scoped current images only; no generation or metadata mutation."""
    if not active_pet:
        raise HTTPException(401, 'No active pet selected.')
    import random
    urls = {}
    with store.transaction() as db:
        for (encoded,) in db.execute('SELECT state FROM rewrites'):
            state = json.loads(encoded)
            if state.get('owner') != active_pet or state.get('discarded'):
                continue
            url = state.get('result', {}).get('image_url', '')
            try:
                path = image_path(url.removeprefix('/generated-images/').removesuffix('.png'))
                if url == f'/generated-images/{path.name}' and not path.is_symlink() and path.is_file():
                    urls[url] = state.get('entry_id')
            except (ValueError, TypeError, AttributeError):
                continue
    from newsmuncher.services.jingles import service as jingles
    return {'images': [{'image_url': url, 'jingle_url': jingles.saved_url(urls[url])}
                       for url in random.sample(sorted(urls), min(5, len(urls)))]}


@router.get('/image_result/{rewrite_id}')
def get_image_result(rewrite_id: str, active_pet: str = Cookie(None)):
    # Read-only restoration: refreshing never calls a paid provider.
    with store.transaction() as db:
        state = read_image_rewrite(db, rewrite_id, active_pet)
        redo = state.get('image_redo')
        if redo and redo['status'] != 'complete' and not state.get('entry_id'):
            try:
                recovered = recover_image(redo['image_id'], redo)
            except ValueError:
                recovered = None
            if recovered:
                finish_image_redo(db, rewrite_id, state, recovered)
        if not state['result'].get('image_url') or not all(k in state['result'] for k in IMAGE_FIELDS if k != 'image_style'):
            attempt = {**dict(prompt=build_image_prompt(state['result']), model=IMAGE_MODEL),
                       **(state.get('image_attempt') or {})}
            try:
                recovered = recover_image(attempt.get('image_id', rewrite_id), attempt)
            except ValueError:
                recovered = None
            if recovered:
                state['result'].update(recovered)
                store.save(db, rewrite_id, state)
        if state['result'].get('image_url'):
            defaults = dict(image_prompt=build_image_prompt(state['result']), image_model='unknown',
                            image_provider='unknown', image_generated_at=None, image_style=None)
            for key, value in defaults.items():
                state['result'].setdefault(key, value)
            store.save(db, rewrite_id, state)
        result = state['result'].copy()
        result['nominated'] = bool(state.get('entry_id') or result.get('nominated'))
        result['image_redo_pending'] = bool(state.get('image_redo') and state['image_redo']['status'] != 'complete')
        result['image_generation_failed'] = bool(not result.get('image_url') and state.get('image_attempt'))
        uncertain = state.get('image_attempt') or {}
        result['image_outcome_uncertain'] = bool(
            not result.get('image_url') and uncertain.get('status') in ('started', 'uncertain'))
        result['image_attempt_id'] = uncertain.get('image_id') if result['image_outcome_uncertain'] else None
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
        if state.get('image_redo') and state['image_redo']['status'] != 'complete':
            raise HTTPException(409, 'Image replacement unresolved; restore status before nomination.')
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
    if state.get('video'):
        from newsmuncher.api.entries import collection
        from newsmuncher.services.video import service as videos
        videos.sync(collection, rewrite_id, owner)
    # Only clear the matching shared preview, never a newer rewrite.
    if os.path.exists(TEMP_SHIZZ_FILE):
        with open(TEMP_SHIZZ_FILE) as f:
            current = json.load(f)
        if current.get('rewrite_id') == rewrite_id:
            os.remove(TEMP_SHIZZ_FILE)
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)
    return {'message': 'Data banked successfully!', 'nominated': True, 'rewrite_id': rewrite_id}
