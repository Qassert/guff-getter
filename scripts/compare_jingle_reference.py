"""Isolated, dry-run-by-default A/B experiment. No OpenAI/TTS or production writes.

Use --entry-id <Mongo nomination ID> to read its existing narration MP3 and stored
SQLite jingle brief. Optional --brief-json accepts an already exported MusicBrief.
--run explicitly authorizes up to two single-attempt Modal requests for this pair.
"""
import argparse
from contextlib import closing
import base64
import hashlib
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


def fetch_audio(request, endpoint, key, secret):
    with requests.post(endpoint, json=request.model_dump(mode='json', exclude_none=True),
                       headers={'Modal-Key': key, 'Modal-Secret': secret},
                       timeout=(15, 600), allow_redirects=False, stream=True) as response:
        response.raise_for_status()
        if response.status_code != 200 or response.headers.get('Content-Type', '').split(';')[0] != 'audio/mpeg':
            raise ValueError('Expected MP3 response')
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 5_000_000:
                raise ValueError('Output MP3 too large')
            chunks.append(chunk)
        audio = b''.join(chunks)
        if len(audio) < 3 or not (audio.startswith(b'ID3') or audio[0] == 255 and audio[1] & 224 == 224):
            raise ValueError('Invalid output MP3')
        return audio


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry-id', required=True)
    parser.add_argument('--brief-json', type=Path)
    parser.add_argument('--seed', type=int, default=1729)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    try:
        brief, reference = load_inputs(args.entry_id, args.brief_json)
        identity, manifest, pair = make_pair(args.entry_id, brief, reference, args.seed)
        destination = OUTPUT_ROOT / identity
        print(json.dumps({'output': str(destination), 'inputs': manifest,
                          'requests': {label: r.marker_request() for label, r in pair.items()}}, indent=2))
        if not args.run:
            print('DRY RUN: no files written, no provider calls. A/B use identical inputs/settings except reference audio.')
            return 0
        load_dotenv(ENV_FILE, override=False)
        endpoint = os.environ.get('MODAL_JINGLE_ENDPOINT', '')
        key, secret = os.environ.get('MODAL_JINGLE_KEY'), os.environ.get('MODAL_JINGLE_SECRET')
        if not endpoint.startswith('https://') or not key or not secret:
            raise ValueError('Configure HTTPS MODAL_JINGLE_ENDPOINT, MODAL_JINGLE_KEY and MODAL_JINGLE_SECRET')
        # Exclusive directory reserves this entire pair before any paid call. No resume/retry guessing.
        destination.mkdir(parents=True, exist_ok=False)
        with (destination / 'attempt.json').open('x') as output:
            json.dump(manifest, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        for label, request in pair.items():
            audio = fetch_audio(request, endpoint, key, secret)
            with (destination / f'{label}.mp3').open('xb') as output:
                output.write(audio)
            print(f'Saved {label}: {destination / (label + ".mp3")}')
        print('A/B complete: two requests; no production files or metadata changed.')
        return 0
    except Exception as exc:
        # Do not echo HTTP bodies/headers or arbitrary exception messages containing credentials.
        print(f'Experiment stopped ({type(exc).__name__}). Check inputs/configuration/output directory. '
              'No automatic retry; retain any attempt files and inspect before another run.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
