"""Isolated, dry-run-by-default A/B experiment. No OpenAI/TTS or production writes.

Use --entry-id <Mongo nomination ID> to read its existing narration MP3 and stored
SQLite jingle brief. Optional --brief-json accepts an already exported MusicBrief.
--run explicitly authorizes up to two single-attempt Modal requests for this pair.
--resume DIRECTORY verifies recovered A and permits only an unattempted B POST.
"""
import argparse
from contextlib import closing
import base64
import hashlib
import fcntl
import tempfile
import json
import os
from pathlib import Path
import sqlite3
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
import requests

from jingle_service.contract import GenerationRequest, MusicBrief
from newsmuncher.config import DATA_DIR, ENV_FILE, GENERATED_NARRATION_DIR, JINGLE_STATE_FILE

OUTPUT_ROOT = DATA_DIR / 'jingle-reference-comparison'


def load_inputs(entry_id, brief_file=None):
    if len(entry_id) != 24 or any(c not in '0123456789abcdef' for c in entry_id):
        raise ValueError('Expected lowercase Mongo nomination ID')
    path = GENERATED_NARRATION_DIR / f'{entry_id}.mp3'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('Existing narration MP3 missing, unsafe or larger than 2 MB')
    reference = path.read_bytes()
    if brief_file:
        brief = MusicBrief.model_validate_json(Path(brief_file).read_text())
    else:
        # No new DB, schema, checkpoint or application startup side effects.
        with closing(sqlite3.connect(JINGLE_STATE_FILE.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT state FROM jingles WHERE id=?', (entry_id,)).fetchone()
        if not row:
            raise ValueError('No stored jingle brief; provide an existing exported --brief-json')
        brief = MusicBrief.model_validate(json.loads(row[0])['brief'])
    return brief, reference


def make_pair(entry_id, brief, reference, seed):
    digest = hashlib.sha256(reference).hexdigest()
    manifest = {'entry_id': entry_id, 'brief': brief.model_dump(), 'seed': seed,
                'reference_sha256': digest, 'experiment': 'narration-reference-v1'}
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    common = {**brief.model_dump(), 'seed': seed, 'experiment': manifest['experiment']}
    pair = {
        label: GenerationRequest(**common,
            request_id=uuid5(NAMESPACE_URL, f'newsmuncher-reference-ab:{identity}:{label}'),
            **({'reference_audio_b64': base64.b64encode(reference).decode(),
                'reference_sha256': digest} if label == 'B' else {}))
        for label in ('A', 'B')
    }
    return identity, manifest, pair


class SafeError(ValueError):
    """Only fixed, credential-free diagnostic messages may use this exception."""


def validate_audio(audio):
    if not 3 <= len(audio) <= 5_000_000:
        raise SafeError('Output MP3 empty or outside allowed size')
    if not (audio.startswith(b'ID3') or audio[0] == 255 and audio[1] & 224 == 224):
        raise SafeError('Invalid output MP3 signature')


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)


def save_state(path, state):
    atomic_write(path, json.dumps(state, indent=2).encode())


def fetch_audio(request, endpoint, key, secret, observe=lambda **kw: None):
    with requests.post(endpoint, json=request.model_dump(mode='json', exclude_none=True),
                       headers={'Modal-Key': key, 'Modal-Secret': secret},
                       timeout=(15, 600), allow_redirects=False, stream=True) as response:
        # Never persist arbitrary headers, response bodies or transport exception text.
        content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
        observe(status_code=response.status_code,
                content_type=content_type if content_type in {'audio/mpeg', 'application/json', 'text/html', 'text/plain'} else 'other')
        if response.status_code != 200:
            raise SafeError('Unexpected HTTP status (see variant state); outcome uncertain')
        if content_type != 'audio/mpeg':
            raise SafeError('Expected audio/mpeg response; outcome uncertain')
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            observe(byte_count=size)
            if size > 5_000_000:
                raise SafeError('Output MP3 too large')
            chunks.append(chunk)
        audio = b''.join(chunks)
        validate_audio(audio)
        return audio


def recovered(destination, label, request):
    audio, marker = destination / f'{label}.mp3', destination / f'{label}.json'
    if not audio.exists() and not marker.exists():
        return False
    if audio.is_symlink() or marker.is_symlink() or not audio.is_file() or not marker.is_file():
        raise SafeError('Incomplete or unsafe recovered audio/marker pair')
    metadata = json.loads(marker.read_text())
    if metadata.get('status') != 'complete' or metadata.get('request') != request.marker_request():
        raise SafeError('Recovered marker does not match canonical request/completion')
    if not 3 <= audio.stat().st_size <= 5_000_000:
        raise SafeError('Recovered MP3 outside allowed size')
    validate_audio(audio.read_bytes())
    if metadata.get('bytes') != audio.stat().st_size:
        raise SafeError('Recovered MP3 size differs from marker')
    return True


def run_pair(destination, pair, endpoint, key, secret, resume=False):
    # One process owns this directory; stale submitted states remain blocked after crashes.
    with (destination / '.resume.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if resume and not recovered(destination, 'A', pair['A']):
            raise SafeError('Resume requires verified recovered A; A will never be submitted')
        for label, request in pair.items():
            path = destination / f'{label}.state.json'
            state = {'variant': label, 'request_uuid': str(request.request_id),
                     'canonical_request': request.marker_request(),
                     'expected_modal_volume_path': str(request.output_path('/results')),
                     'volume': 'newsmuncher-jingle-results', 'stage': 'pending',
                     'status_code': None, 'content_type': None, 'byte_count': 0,
                     'safe_error_category': None}
            if recovered(destination, label, request):
                if path.exists():
                    prior = json.loads(path.read_text())
                    if prior.get('canonical_request') != request.marker_request():
                        raise SafeError('Stored variant state disagrees with recovered request')
                    state.update(prior)
                state.update(stage='completed', recovered=True,
                             byte_count=(destination / f'{label}.mp3').stat().st_size)
                save_state(path, state)
                print(f'{label}: recovered/completed; skipping POST')
                continue
            if path.exists():
                prior = json.loads(path.read_text())
                if any(prior.get(k) != state[k] for k in ('variant', 'request_uuid', 'canonical_request')) or prior.get('stage') != 'pending':
                    raise SafeError('Prior variant outcome requires artifact recovery; refusing another POST')
            save_state(path, state)
            state['stage'] = 'submitted'
            save_state(path, state)  # durable BEFORE a potentially paid call
            def observe(**fields):
                state.update(fields)
                save_state(path, state)
            try:
                audio = fetch_audio(request, endpoint, key, secret, observe=observe)
                validate_audio(audio)
                atomic_write(destination / f'{label}.mp3', audio)
                save_state(destination / f'{label}.json',
                           {'request': request.marker_request(), 'status': 'complete', 'bytes': len(audio)})
                observe(stage='completed', byte_count=len(audio))
            except Exception as exc:
                observe(stage='ambiguous', safe_error_category=str(exc) if isinstance(exc, SafeError) else type(exc).__name__)
                raise
            print(f'Saved {label}: {destination / (label + ".mp3")}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry-id')
    parser.add_argument('--brief-json', type=Path)
    parser.add_argument('--seed', type=int, default=1729)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--resume', type=Path, help='Existing experiment directory; verify A and submit only unattempted B')
    args = parser.parse_args(argv)
    try:
        if args.resume:
            destination = args.resume.resolve()
            manifest = json.loads((destination / 'attempt.json').read_text())
            reference = (GENERATED_NARRATION_DIR / f"{manifest['entry_id']}.mp3").read_bytes()
            identity, intended, pair = make_pair(manifest['entry_id'], MusicBrief.model_validate(manifest['brief']), reference, manifest['seed'])
            if intended != manifest or destination != (OUTPUT_ROOT / identity).resolve():
                raise SafeError('Resume manifest/reference/experiment identity mismatch')
        else:
            if not args.entry_id:
                raise SafeError('--entry-id required unless using --resume')
            brief, reference = load_inputs(args.entry_id, args.brief_json)
            identity, manifest, pair = make_pair(args.entry_id, brief, reference, args.seed)
            destination = OUTPUT_ROOT / identity
        print(json.dumps({'output': str(destination), 'inputs': manifest,
                          'requests': {label: r.marker_request() for label, r in pair.items()}}, indent=2))
        if not args.run and not args.resume:
            print('DRY RUN: no files written, no provider calls. A/B use identical inputs/settings except reference audio.')
            return 0
        load_dotenv(ENV_FILE, override=False)
        endpoint = os.environ.get('MODAL_JINGLE_ENDPOINT', '')
        key, secret = os.environ.get('MODAL_JINGLE_KEY'), os.environ.get('MODAL_JINGLE_SECRET')
        if not endpoint.startswith('https://') or not key or not secret:
            raise SafeError('Configure HTTPS MODAL_JINGLE_ENDPOINT, MODAL_JINGLE_KEY and MODAL_JINGLE_SECRET')
        if not args.resume:
            destination.mkdir(parents=True, exist_ok=False)
            save_state(destination / 'attempt.json', manifest)
        run_pair(destination, pair, endpoint, key, secret, resume=bool(args.resume))
        print('A/B complete; no production files or metadata changed.')
        return 0
    except Exception as exc:
        # Do not echo HTTP bodies/headers or arbitrary exception messages containing credentials.
        reason = str(exc) if isinstance(exc, SafeError) else type(exc).__name__
        print(f'Experiment stopped ({reason}). Check inputs/configuration/output directory. '
              'No automatic retry; retain any attempt files and inspect before another run.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
