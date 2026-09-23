"""Standalone, opt-in image-to-video comparison; see video_smoke_test.md.

No NewsMuncher imports, dotenv loading, SDK retries or application integration.
"""
import argparse
import base64
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / 'tmp/video-smoke-test'
WAN_BASE = 'https://api.wavespeed.ai/api/v3'
FAL_BASE = 'https://queue.fal.run/fal-ai/stable-video'
MODELS = {'wan': 'wavespeed-ai/wan-2.2/i2v-480p-ultra-fast', 'svd': 'fal-ai/stable-video'}
KEYS = {'wan': 'WAVESPEED_API_KEY', 'svd': 'FAL_KEY'}
COSTS = {'wan': Decimal('0.05'), 'svd': Decimal('0.075')}
DEFAULT_PROMPT = (
    'Preserve the original image, characters, composition and surreal style. '
    'Animate the existing scene with absurd but coherent movement. '
    'Characters and visible objects may move naturally according to what is already present in the image. '
    'Use restrained but noticeable movement, subtle environmental motion and a gentle cinematic camera drift. '
    'Do not radically redesign the image. Do not introduce unrelated characters or objects. '
    'Do not add text. Do not significantly change faces.'
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
POLL_SECONDS = 5
POLL_TIMEOUT = 900


class SmokeError(Exception):
    """Only fixed, non-secret diagnostics may be placed in this exception."""


def read_image(path):
    try:
        with path.open('rb') as source:
            data = source.read(MAX_IMAGE_BYTES + 1)
    except OSError:
        raise SmokeError('Source image is missing or unreadable.') from None
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise SmokeError('Source image must be nonempty and at most 10 MiB.')
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return data, 'image/png', '.png'
    if data.startswith(b'\xff\xd8\xff'):
        return data, 'image/jpeg', '.jpg'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return data, 'image/webp', '.webp'
    raise SmokeError('Use a PNG, JPEG or WebP image.')


def https_url(url):
    if not isinstance(url, str):
        raise SmokeError('Provider returned an invalid media URL.')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise SmokeError('Provider returned an invalid media URL.')
    return url


def request_json(session, method, url, **kwargs):
    # No redirects, no retries. Never print provider bodies, headers, URLs or exceptions.
    with session.request(method, url, timeout=(15, 60), allow_redirects=False, **kwargs) as response:
        if not 200 <= response.status_code < 300:
            raise SmokeError('Provider HTTP request failed; no automatic retry.')
        result = response.json()
        if not isinstance(result, dict):
            raise SmokeError('Provider returned an invalid response.')
        return result


def job_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
        raise SmokeError('Provider returned an invalid job ID; do not resubmit automatically.')
    return value


def persist(directory, metadata):
    temporary = directory / 'results.json.part'
    with temporary.open('w', encoding='utf-8') as out:
        json.dump(metadata, out, indent=2, ensure_ascii=False)
        out.flush()
        os.fsync(out.fileno())
    temporary.replace(directory / 'results.json')
    cards = []
    for name, result in metadata['providers'].items():
        video = (f'<video controls loop muted playsinline src="{name}.mp4"></video>'
                 if result.get('output_file') else '<p>No successful video saved.</p>')
        cards.append(f'<section><h2>{"WAN 2.2 ULTRA FAST" if name == "wan" else "STABLE VIDEO DIFFUSION 1.1"}</h2>'
            f'<p>{html.escape(result["model"])}</p>{video}'
            f'<p>Estimated cost: ${result["estimated_cost_usd"]} · {html.escape(result["state"])}</p>'
            f'<pre>{html.escape(json.dumps(result["parameters"], indent=2))}</pre></section>')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Video smoke test</title>
<style>body{{font:16px system-ui;margin:24px auto;padding:0 16px;max-width:1200px;background:#faf8f2;color:#222}}
img,video{{width:100%;max-height:65vh;object-fit:contain}}img{{max-width:600px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:24px}}
section{{padding:16px;border:1px solid #aaa}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<h1>Source image</h1><img src="{metadata['source_image']}" alt="Shared input image">
<p>Wan motion prompt (not sent to SVD):</p><pre>{html.escape(metadata['prompt'])}</pre>
<div class="grid">{''.join(cards)}</div></html>'''
    (directory / 'compare.html').write_text(page, encoding='utf-8')


def generate(session, name, key, image, mime, parameters, record, checkpoint):
    if name == 'wan':
        headers = {'Authorization': f'Bearer {key}'}
        uploaded = request_json(session, 'POST', WAN_BASE + '/media/upload/binary', headers=headers,
            files={'file': ('source-image', image, mime)})
        image_url = https_url(uploaded['data']['download_url'])
        endpoint = WAN_BASE + '/' + MODELS[name]
        payload = {**parameters, 'image': image_url}
    else:
        headers = {'Authorization': f'Key {key}', 'X-Fal-No-Retry': '1'}
        endpoint = FAL_BASE
        payload = {**parameters, 'image_url': f'data:{mime};base64,' + base64.b64encode(image).decode('ascii')}
    record['state'] = 'submission_started'  # Save before the single potentially billable POST.
    checkpoint()
    submitted = request_json(session, 'POST', endpoint, headers=headers, json=payload)
    identifier = job_id(submitted['data']['id'] if name == 'wan' else submitted['request_id'])
    record.update(request_id=identifier, state='submitted')
    checkpoint()
    result_url = (WAN_BASE + f'/predictions/{identifier}/result' if name == 'wan'
                  else FAL_BASE + f'/requests/{identifier}')
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        response = request_json(session, 'GET', result_url if name == 'wan' else result_url + '/status', headers=headers)
        state = response['data'] if name == 'wan' else response
        status = state['status']
        if status == ('completed' if name == 'wan' else 'COMPLETED'):
            if name == 'wan':
                return https_url(state['outputs'][0])
            result = request_json(session, 'GET', result_url, headers=headers)
            if type(result.get('seed')) is int:
                record['returned_seed'] = result['seed']
            return https_url(result['video']['url'])
        if status not in ('created', 'pending', 'processing', 'in_queue', 'IN_QUEUE', 'IN_PROGRESS'):
            raise SmokeError('Provider job failed or returned an unknown state; no regeneration.')
    raise SmokeError('Polling deadline reached; the remote job may still finish. Do not resubmit.')


def download(session, url, target):
    # This session has no provider Authorization header; output URLs are never persisted.
    part = target.with_suffix('.mp4.part')
    try:
        with session.get(https_url(url), timeout=(15, 60), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise SmokeError('Video download failed; no regeneration.')
            size = 0
            with part.open('xb') as out:
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_VIDEO_BYTES:
                        raise SmokeError('Video exceeds the 100 MiB download limit.')
                    out.write(chunk)
        with part.open('rb') as downloaded:
            header = downloaded.read(12)
        if len(header) < 12 or header[4:8] != b'ftyp':
            raise SmokeError('Downloaded output is not an MP4 container.')
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--prompt', default=DEFAULT_PROMPT)
    parser.add_argument('--providers', choices=['wan', 'svd', 'wan,svd'], default='')
    parser.add_argument('--confirm-spend', action='store_true')
    args = parser.parse_args(argv)
    directory = None
    try:
        image, mime, suffix = read_image(args.image)
        selected = args.providers.split(',') if args.providers else []
        if 'wan' in selected and not args.prompt.strip():
            raise SmokeError('Wan requires a nonempty motion prompt.')
        records = {}
        for name in selected:
            seed = secrets.randbelow(2**31)
            parameters = ({'duration': 5, 'seed': seed, 'prompt': args.prompt} if name == 'wan' else
                          {'motion_bucket_id': 127, 'cond_aug': 0.02, 'fps': 25, 'seed': seed})
            records[name] = {'model': MODELS[name], 'parameters': parameters,
                'estimated_cost_usd': float(COSTS[name]), 'state': 'not_started'}
        print('Planned paid generations:')
        for name, record in records.items():
            print(f"  {name}: {record['model']} — estimated ${COSTS[name]}")
            print('    ' + json.dumps(record['parameters'], ensure_ascii=False))
        print(f'Estimated maximum total: ${sum((COSTS[n] for n in selected), Decimal(0))}')
        print('Estimates only; provider billing applies. Wan: 480p/5 seconds. SVD: image-only, no motion prompt.')
        if not args.confirm_spend or not selected:
            print('Dry run: zero provider calls. Supply --providers and --confirm-spend to run.')
            return 0
        missing = [KEYS[n] for n in selected if not os.environ.get(KEYS[n], '').strip()]
        if missing:
            raise SmokeError('Missing environment key(s): ' + ', '.join(missing) + '. Zero provider calls.')
        directory = OUTPUT_ROOT / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid4().hex[:8])
        directory.mkdir(parents=True, exist_ok=False)
        (directory / ('source-image' + suffix)).write_bytes(image)
        metadata = {'source_image': 'source-image' + suffix, 'source_sha256': hashlib.sha256(image).hexdigest(),
                    'prompt': args.prompt, 'providers': records}
        checkpoint = lambda: persist(directory, metadata)
        checkpoint()
        with requests.Session() as session:
            # Disable implicit .netrc credentials/environment proxies and all library retries.
            session.trust_env = False
            for name in selected:
                record = records[name]
                try:
                    record['state'] = 'preparing_input'
                    checkpoint()
                    url = generate(session, name, os.environ[KEYS[name]].strip(), image, mime,
                                   record['parameters'], record, checkpoint)
                    record['state'] = 'generated'
                    checkpoint()
                    download(session, url, directory / f'{name}.mp4')
                    record.update(state='complete', output_file=f'{name}.mp4')
                    checkpoint()
                except (Exception, KeyboardInterrupt):
                    record['state'] = 'failed_or_uncertain'
                    checkpoint()
                    raise SmokeError('Stopped without retry. Inspect results.json and provider job history before any new run.') from None
        print(f'Comparison saved: {directory / "compare.html"}')
        return 0
    except SmokeError as exc:
        print(str(exc), file=sys.stderr)
        if directory:
            print(f'Attempt metadata: {directory / "results.json"}', file=sys.stderr)
        return 1
    except Exception:
        print('Local setup or output write failed. No automatic retry.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
