"""Shared single-attempt WaveSpeed transport extracted from the offline smoke test.

No environment loading, app/database imports, SDK retries or implicit generation.
"""
import os
import re
import time
from urllib.parse import urlsplit

import requests

WAN_BASE = 'https://api.wavespeed.ai/api/v3'
MODEL = 'wavespeed-ai/wan-2.2/i2v-480p-ultra-fast'
KEYS = {'wan': 'WAVESPEED_API_KEY', 'svd': 'FAL_KEY'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


class SmokeError(Exception):
    """Only fixed, non-secret diagnostics may be placed in this exception."""


class Diagnostics:
    """Persist only selected, sanitized diagnostic fields; never raw HTTP objects."""

    def __init__(self, record, checkpoint):
        self.record, self.checkpoint = record, checkpoint
        self.secrets = [os.environ.get(k, '').strip() for k in KEYS.values()]
        self.current = None

    def safe(self, value):
        text = str(value)
        for secret in sorted((v for v in self.secrets if isinstance(v, str) and v), key=len, reverse=True):
            text = text.replace(secret, '[redacted]')
        # Omit credential/header dumps altogether, including unknown provider secrets.
        if re.search(r'authorization|bearer|api[_ -]?key|token|secret|signature|credential|password|headers', text, re.I):
            return '[sensitive diagnostic omitted]'
        text = re.sub(r'https?://[^\s<>"\']+', '[URL redacted]', text)
        text = re.sub(r'data:[^\s]+', '[data redacted]', text)
        return ''.join(c for c in text if c.isprintable())[:500]

    def start(self, stage):
        if self.current:
            self.current['state'] = 'complete'
        self.current = {'stage': stage, 'state': 'started', 'http_status': None,
                        'provider_message': None}
        self.record.setdefault('stages', []).append(self.current)
        self.checkpoint()

    def body(self, value):
        # Only diagnostic fields: do not serialize payloads, URLs, headers or inputs.
        if isinstance(value, dict):
            parts = [self.body(value[k]) for k in ('code', 'message', 'error', 'detail') if k in value]
            return '; '.join(filter(None, parts)) or None
        if isinstance(value, (str, int)):
            return self.safe(value)
        return None

    def response(self, response):
        self.current['http_status'] = response.status_code
        self.current['provider_message'] = None
        if not 200 <= response.status_code < 300:
            try:
                message = self.body(response.json())
            except ValueError:
                message = '[non-JSON response body omitted]'
            self.current['provider_message'] = message
            raise SmokeError('HTTP request rejected; no automatic retry.')

    def fail(self, exc):
        self.current.update(state='failed', exception_type=type(exc).__name__,
                            exception_message=self.safe(exc))
        self.record['error'] = dict(self.current)
        self.checkpoint()
        status = self.current['http_status']
        return (f"{self.current['stage']} (HTTP {status if status is not None else 'unavailable'}): "
                f"{self.current['exception_type']}: {self.current['exception_message']}"
                + (f" — {self.current['provider_message']}" if self.current['provider_message'] else ''))


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


def request_json(session, method, url, diagnostics, **kwargs):
    # No redirects or retries; only sanitized diagnostics may leave this function.
    diagnostics.current.update(http_status=None, provider_message=None)
    with session.request(method, url, timeout=(15, 60), allow_redirects=False, **kwargs) as response:
        diagnostics.response(response)
        result = response.json()
        if not isinstance(result, dict):
            raise SmokeError('Provider returned an invalid response.')
        diagnostics.current['provider_message'] = diagnostics.body(result)
        return result


def job_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
        raise SmokeError('Provider returned an invalid job ID; do not resubmit automatically.')
    return value


def generate_wan(session, key, image, mime, parameters, record, checkpoint, diagnostics,
                 poll_timeout=900, poll_seconds=5):
    headers = {'Authorization': f'Bearer {key}'}
    diagnostics.start('auth_upload_ticket')
    uploaded = request_json(session, 'POST', WAN_BASE + '/media/uploads', diagnostics,
        headers=headers, json={'filename': 'source-image.' + mime.split('/')[1],
                               'size': len(image), 'content_type': mime})
    ticket = uploaded['data']
    upload = ticket['upload']
    diagnostics.secrets.extend([upload['url'], ticket['download_url']])
    upload_headers = upload['headers']
    if not isinstance(upload_headers, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in upload_headers.items()):
        raise SmokeError('Invalid upload headers in ticket.')
    diagnostics.secrets.extend(upload_headers.values())
    upload_url = https_url(upload['url'])
    image_url = https_url(ticket['download_url'])
    diagnostics.start('image_upload')
    with session.request('PUT', upload_url, headers=upload_headers, data=image,
                         timeout=(15, 60), allow_redirects=False) as response:
        diagnostics.response(response)
    endpoint = WAN_BASE + '/' + MODEL
    payload = {**parameters, 'image': image_url}
    record['state'] = 'submission_started'
    checkpoint()  # Durable checkpoint before the single potentially billable POST.
    diagnostics.start('model_submission')
    submitted = request_json(session, 'POST', endpoint, diagnostics, headers=headers, json=payload)
    identifier = job_id(submitted['data']['id'])
    record.update(request_id=identifier, state='submitted')
    checkpoint()
    diagnostics.start('prediction_polling')
    deadline = time.monotonic() + poll_timeout
    while time.monotonic() < deadline:
        time.sleep(poll_seconds)
        response = request_json(session, 'GET', WAN_BASE + f'/predictions/{identifier}/result',
                                diagnostics, headers=headers)
        state = response['data']
        if state['status'] == 'completed':
            return https_url(state['outputs'][0])
        if state['status'] not in ('created', 'pending', 'processing', 'in_queue'):
            diagnostics.current['provider_message'] = diagnostics.body(state)
            raise SmokeError('Provider job failed or returned an unknown state; no regeneration.')
    raise SmokeError('Polling deadline reached; the remote job may still finish. Do not resubmit.')


def download(session, url, target, diagnostics):
    # This session has no provider Authorization header; output URLs are never persisted.
    diagnostics.secrets.append(url)
    diagnostics.start('output_download')
    part = target.with_suffix('.mp4.part')
    try:
        with session.get(https_url(url), timeout=(15, 60), allow_redirects=False, stream=True) as response:
            diagnostics.response(response)
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


def create_video(source, target, prompt, seed, record, checkpoint, key):
    diagnostics = Diagnostics(record, checkpoint)
    diagnostics.secrets.append(key)
    diagnostics.start('local_preparation')
    try:
        image, mime, _ = read_image(source)
        with requests.Session() as session:
            session.trust_env = False
            url = generate_wan(session, key, image, mime,
                {'prompt': prompt, 'duration': 5, 'seed': seed}, record, checkpoint, diagnostics)
            download(session, url, target, diagnostics)
        diagnostics.current['state'] = 'complete'
        checkpoint()
    except Exception as exc:
        diagnostics.fail(exc)
        raise SmokeError('Animation failed or uncertain; operator review required.') from None
