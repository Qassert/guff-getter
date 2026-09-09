"""Image providers and durable rewrite association; no paid-call retries."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import base64
import os
import tempfile
import json
import sqlite3
import time
from typing import Protocol
from uuid import uuid4, UUID

from openai import OpenAI
from dotenv import load_dotenv

from newsmuncher.config import PREVIEWS_DIR, GENERATED_IMAGES_DIR, ENV_FILE

# Image-only settings. Text generation settings are intentionally independent.
IMAGE_MODEL = "gpt-image-1.5"
IMAGE_QUALITY = "low"
IMAGE_SIZE = "1024x1024"
IMAGE_TIMEOUT = 180.0

IMAGE_FIELDS = ('image_url', 'image_prompt', 'image_model', 'image_provider', 'image_generated_at')
STYLE = ('Absurd editorial illustration, underground zine artwork, graffiti and stencil '
         'influences, screen-print texture, bold composition, strange surreal humour, '
         'visually chaotic but readable composition, no text, captions, logos or lettering in the image.')


def build_image_prompt(result):
    return (f'{STYLE}\nScene title: {result["crazyReplacement1Title"][:200]}\n'
            f'Scene: {result["crazyReplacement1Extract"][:1200]}')


class ImageProvider(Protocol):
    def generate_image(self, prompt: str, rewrite_id: str) -> dict: ...


class LocalStubProvider:
    """Retained for offline tests and legacy demonstrations only."""
    def generate_image(self, prompt: str, rewrite_id: str | None = None) -> dict:
        return dict(image_url='/static/image-stub.svg', image_prompt=prompt,
                    image_model='local-placeholder-v1', image_provider='local-stub',
                    image_generated_at=datetime.now(timezone.utc).isoformat())


def image_path(rewrite_id):
    return GENERATED_IMAGES_DIR / f'{UUID(rewrite_id)}.png'


def image_metadata(rewrite_id, prompt, model=IMAGE_MODEL, generated_at=None):
    return dict(image_url=f'/generated-images/{UUID(rewrite_id)}.png',
                image_prompt=prompt, image_model=model, image_provider='openai',
                image_generated_at=generated_at or datetime.now(timezone.utc).isoformat())


def recover_image(rewrite_id, attempt):
    path = image_path(rewrite_id)
    if not path.is_file():
        return None
    with path.open('rb') as file:
        if file.read(8) != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Existing generated image is invalid; refusing to regenerate.')
    return image_metadata(rewrite_id, attempt['prompt'], attempt['model'],
                          datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())


class OpenAIImageProvider:
    def generate_image(self, prompt: str, rewrite_id: str) -> dict:
        path = image_path(rewrite_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = recover_image(rewrite_id, {'prompt': prompt, 'model': IMAGE_MODEL})
        if existing:
            return existing
        load_dotenv(ENV_FILE)
        with OpenAI(max_retries=0, timeout=IMAGE_TIMEOUT) as client:
            response = client.images.generate(model=IMAGE_MODEL, quality=IMAGE_QUALITY,
                size=IMAGE_SIZE, n=1, output_format='png', prompt=prompt)
        if not response.data or len(response.data) != 1 or not response.data[0].b64_json:
            raise ValueError('Expected one generated image.')
        image = base64.b64decode(response.data[0].b64_json, validate=True)
        if not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Expected PNG image data.')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as file:
                temporary = file.name
                file.write(image)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return image_metadata(rewrite_id, prompt)


def get_provider() -> ImageProvider:
    return OpenAIImageProvider()


class RewriteStore:
    """SQLite sidecar survives reloads and coordinates image/banking completion.

    No image bytes are stored. Transactions serialize metadata and bank association;
    provider work happens outside the transaction.
    """
    def __init__(self, path=None):
        self.path = path or PREVIEWS_DIR / 'image_rewrites.sqlite3'

    @contextmanager
    def transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS rewrites (id TEXT PRIMARY KEY, state TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS draft_slots (owner TEXT, session TEXT, rewrite_id TEXT, PRIMARY KEY(owner, session))')
            db.execute('BEGIN IMMEDIATE')
            yield db

    def create(self, result, owner):
        rewrite_id = str(uuid4())
        result = {**result, 'rewrite_id': rewrite_id}
        with self.transaction() as db:
            self.save(db, rewrite_id, dict(result=result, owner=owner, entry_id=None))
        return result

    def discard(self, db, rewrite_id, state):
        # A nomination with an uncertain HTTP outcome may already exist in Mongo.
        # Never delete its file until that association can be reconciled.
        if state.get('entry_id') or state.get('nomination_pending'):
            return
        image_path(rewrite_id).unlink(missing_ok=True)
        # Retain only a tombstone: late workers cannot resurrect the draft or pay again.
        self.save(db, rewrite_id, dict(owner=state['owner'], entry_id=None, discarded=True,
                                      result={'rewrite_id': rewrite_id}))

    def begin_draft(self, source, owner, session):
        rewrite_id = str(uuid4())
        with self.transaction() as db:
            # Opportunistic expiry of new-style abandoned drafts; legacy rows without
            # expiry and uncertain nominations are intentionally not bulk-deleted.
            for old_id, encoded in db.execute('SELECT id, state FROM rewrites').fetchall():
                old_state = json.loads(encoded)
                if old_state.get('discarded'):
                    image_path(old_id).unlink(missing_ok=True)
                elif old_state.get('expires_at', float('inf')) < time.time():
                    self.discard(db, old_id, old_state)
            previous = db.execute('SELECT rewrite_id FROM draft_slots WHERE owner=? AND session=?',
                                  (owner, session)).fetchone()
            if previous:
                old = self.read(db, previous[0], owner)
                self.discard(db, previous[0], old)
            result = {**source, 'rewrite_id': rewrite_id, 'nominated': False}
            self.save(db, rewrite_id, dict(result=result, owner=owner, entry_id=None, generating=True, expires_at=time.time() + 86400))
            db.execute('INSERT OR REPLACE INTO draft_slots VALUES (?, ?, ?)', (owner, session, rewrite_id))
        return rewrite_id

    def complete_draft(self, rewrite_id, owner, result):
        with self.transaction() as db:
            state = self.read(db, rewrite_id, owner)
            if state.get('discarded'):
                return None
            state['result'] = {**result, 'rewrite_id': rewrite_id, 'nominated': False}
            state['generating'] = False
            self.save(db, rewrite_id, state)
            return state['result']

    def read(self, db, rewrite_id, owner):
        row = db.execute('SELECT state FROM rewrites WHERE id=?', (rewrite_id,)).fetchone()
        if not row:
            raise LookupError('Rewrite not found.')
        state = json.loads(row[0])
        if not owner or state['owner'] != owner:
            raise PermissionError('Rewrite belongs to another active pet.')
        return state

    def save(self, db, rewrite_id, state):
        db.execute('INSERT OR REPLACE INTO rewrites VALUES (?, ?)',
                   (rewrite_id, json.dumps(state)))


store = RewriteStore()
