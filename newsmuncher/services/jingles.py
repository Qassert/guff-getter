"""Permanent jingle claims and local files. No provider calls from status/playback."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
from uuid import NAMESPACE_URL, uuid5

import requests
from dotenv import load_dotenv

from newsmuncher.config import ENV_FILE, GENERATED_AUDIO_DIR, JINGLE_STATE_FILE
from newsmuncher.services.jingle_brief import create_jingle_brief

MODEL = "acestep-v15-turbo"
MAX_AUDIO_BYTES = 5_000_000


class JingleError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def configured():
    load_dotenv(ENV_FILE)
    return (os.getenv("NEWSMUNCHER_JINGLE_ENABLED", "true").lower() == "true"
            and os.getenv("MODAL_JINGLE_ENDPOINT", "").startswith("https://")
            and bool(os.getenv("MODAL_JINGLE_KEY")) and bool(os.getenv("MODAL_JINGLE_SECRET")))


def daily_limit():
    try:
        return max(0, int(os.getenv("NEWSMUNCHER_JINGLE_DAILY_LIMIT", "20")))
    except ValueError:
        return 0  # A bad configuration fails closed.


def modal_audio(brief, request_id):
    """One POST only. Any transport/provider failure is conservatively uncertain."""
    if not configured():
        raise JingleError(503, "Jingle provider is not configured.")
    with requests.post(
        os.environ["MODAL_JINGLE_ENDPOINT"],
        json={**brief.model_dump(), "request_id": request_id},
        headers={"Modal-Key": os.environ["MODAL_JINGLE_KEY"],
                 "Modal-Secret": os.environ["MODAL_JINGLE_SECRET"]},
        timeout=(15, 600), allow_redirects=False, stream=True,
    ) as response:
        response.raise_for_status()
        if response.status_code != 200 or response.headers.get("Content-Type", "").split(";")[0] != "audio/mpeg":
            raise ValueError("Provider did not return MP3.")
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_AUDIO_BYTES:
                raise ValueError("Audio exceeds the allowed size.")
            chunks.append(chunk)
        return b"".join(chunks)


def valid_mp3(data):
    return (1000 < len(data) <= MAX_AUDIO_BYTES
            and (data.startswith(b"ID3") or (data[0] == 255 and data[1] & 224 == 224)))


class LocalAudio:
    """Replace this adapter for object storage later; URLs contain no credentials."""
    def __init__(self, directory=GENERATED_AUDIO_DIR):
        self.directory = Path(directory)

    def path(self, key):
        if not re.fullmatch(r"[a-f0-9]{24}", key):
            raise ValueError("Invalid nomination identity.")
        return self.directory / (key + ".mp3")

    def exists(self, key):
        path = self.path(key)
        if not path.is_file() or path.is_symlink() or not 1000 < path.stat().st_size <= MAX_AUDIO_BYTES:
            return False
        return valid_mp3(path.read_bytes())

    def save(self, key, data):
        if not valid_mp3(data):
            raise ValueError("Invalid MP3 response.")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path(key)
        temporary = path.with_suffix(".mp3.part")
        with temporary.open("xb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)

    def url(self, key):
        return f"/generated-audio/{key}.mp3"


class Jingles:
    def __init__(self, database=JINGLE_STATE_FILE, audio=None, brief_factory=create_jingle_brief,
                 provider=modal_audio, enabled=configured, limit=daily_limit, now=None):
        self.database = Path(database)
        self.audio = audio or LocalAudio()
        self.brief_factory, self.provider = brief_factory, provider
        self.enabled, self.limit = enabled, limit
        self.now = now or (lambda: datetime.now(timezone.utc))

    @contextmanager
    def transaction(self):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database, timeout=15)) as db, db:
            db.execute("PRAGMA busy_timeout=15000")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS jingles (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS jingle_claims (id INTEGER PRIMARY KEY, day TEXT, nomination TEXT)")
            db.execute("CREATE INDEX IF NOT EXISTS jingle_claims_day ON jingle_claims(day)")
            yield db

    @staticmethod
    def read(db, key):
        row = db.execute("SELECT state FROM jingles WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def save(db, key, state):
        db.execute("INSERT INTO jingles VALUES (?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state",
                   (key, json.dumps(state)))

    @staticmethod
    def nomination(collection, rewrite_id, owner):
        if not owner:
            raise JingleError(401, "Select a pet first.")
        entry = collection.find_one({"rewrite_id": rewrite_id, "nominated": True,
                                     "$or": [{"image_owner": owner},
                                             {"image_owner": {"$exists": False}, "creationUser": owner}]})
        if not entry:
            raise JingleError(404, "No nominated entry belonging to this pet.")
        # Defend against incomplete adapters and legacy records too.
        if entry.get("nominated") is not True or (entry.get("image_owner") or entry.get("creationUser")) != owner:
            raise JingleError(403, "Only your nominated entry may generate a jingle.")
        return entry

    def remaining(self, db):
        day = self.now().date().isoformat()
        used = db.execute("SELECT COUNT(*) FROM jingle_claims WHERE day=?", (day,)).fetchone()[0]
        return max(0, self.limit() - used)

    def metadata(self, key, state):
        return {
            "jingle_status": "complete", "jingle_url": self.audio.url(key),
            "jingle_generated_at": state.get("generated_at") or
                datetime.fromtimestamp(self.audio.path(key).stat().st_mtime, timezone.utc).isoformat(),
            "jingle_provider": "modal", "jingle_model": MODEL,
            "jingle_prompt": state["brief"],
            "jingle_text_snapshot": state["snapshot"],
            "jingle_text_sha256": state["text_hash"],
            "jingle_brief_usage": state.get("brief_usage"),
        }

    def sync(self, collection, entry, metadata):
        result = collection.update_one({"_id": entry["_id"], "nominated": True},
                              {"$set": metadata})
        if result.matched_count == 0:
            self.try_retire_deleted(collection, entry)
            raise JingleError(404, "Nomination no longer exists; jingle was not attached.")

    def try_retire_deleted(self, collection, entry):
        # Cleanup must never hide an already confirmed missing-entry outcome.
        try:
            self.retire_deleted(collection, entry)
        except Exception:
            logging.getLogger(__name__).warning("Jingle retirement needs retry for %s", entry["_id"])

    def retire_deleted(self, collection, entry):
        """Remove only proven local ownership; retain a tombstone against late workers.

        Keep quota claims. Never glob audio, follow symlinks, or remove unknown files.
        A later call can retry cleanup if filesystem removal fails.
        """
        key = str(entry["_id"])
        if not re.fullmatch(r"[a-f0-9]{24}", key):
            return
        with self.transaction() as db:
            if collection.find_one({"_id": entry["_id"]}) is not None:
                return
            state = self.read(db, key)
            request_id = str(uuid5(NAMESPACE_URL, "newsmuncher-jingle:" + key))
            owned = (state and state.get("request_id") == request_id) or (
                entry.get("jingle_provider") == "modal"
                and entry.get("jingle_url") == self.audio.url(key))
            if not owned:
                return
            self.save(db, key, {"status": "retired", "request_id": request_id})
            path = self.audio.path(key)
            if path.is_file() and not path.is_symlink():
                try:
                    path.unlink()
                except OSError:
                    logging.getLogger(__name__).warning("Retired jingle %s needs file cleanup", key)

    def discover(self, collection, owner):
        """Persistent discovery also reconciles completed local files with Mongo.

        Uses the same ownership checks as MAKE; never calls a generation provider.
        """
        if not owner:
            raise JingleError(401, "Select a pet first.")
        entries = collection.find({"nominated": True, "$or": [
            {"image_owner": owner},
            {"image_owner": {"$exists": False}, "creationUser": owner}]}).sort(
                [("creationDate", -1), ("_id", -1)])
        saved = []
        for entry in entries:
            if not entry.get("rewrite_id"):
                continue
            try:
                result = self.entry_status(collection, entry, owner)
            except JingleError as exc:
                if exc.status in (403, 404):
                    continue  # Deleted or ownership changed during discovery.
                raise
            if result.get("jingle_url") or entry.get("jingle_url"):
                saved.append({"entry_id": str(entry["_id"]), "rewrite_id": entry["rewrite_id"],
                              "title": self.snapshot(entry)["title"], **result})
        return {"jingles": saved}

    def status(self, collection, rewrite_id, owner):
        entry = self.nomination(collection, rewrite_id, owner)
        return self.entry_status(collection, entry, owner)

    def entry_status(self, collection, entry, owner):
        # Discovery keeps the exact entry identity; never re-resolve a legacy rewrite ID.
        if not owner or entry.get("nominated") is not True or (
                entry.get("image_owner") or entry.get("creationUser")) != owner:
            raise JingleError(403, "Only your nominated entry may access a jingle.")
        key = str(entry["_id"])
        with self.transaction() as db:
            state = self.read(db, key)
            if state and state["status"] == "retired":
                return {"jingle_status": "retired", "can_generate": False,
                        "message": "Jingle retired; no automatic regeneration."}
            # File is durable before metadata; recover that gap without provider calls.
            if state and state.get("brief") and self.audio.exists(key):
                state["status"] = "complete"
                metadata = self.metadata(key, state)
                state["generated_at"] = metadata["jingle_generated_at"]
                self.save(db, key, state)
            else:
                metadata = None
            remaining = self.remaining(db)
        if metadata:
            pending = False
            try:
                self.sync(collection, entry, metadata)
            except JingleError:
                raise
            except Exception:
                pending = True  # Local audio remains usable, later GET retries only the sync.
            return {"jingle_status": "complete", "jingle_url": metadata["jingle_url"],
                    "metadata_pending": pending, "can_generate": False,
                    "text_changed": state["snapshot"] != self.snapshot(entry)}
        if not state and self.audio.exists(key) and not entry.get("jingle_url"):
            return {"jingle_status": "unavailable", "can_generate": False,
                    "message": "Audio exists but metadata needs recovery; no automatic regeneration."}
        # Mongo jingle metadata prevents another claim even if local state/file was lost.
        if entry.get("jingle_url"):
            return {"jingle_status": "complete" if self.audio.exists(key) else "unavailable",
                    "jingle_url": self.audio.url(key) if self.audio.exists(key) else None,
                    "can_generate": False,
                    "text_changed": bool(entry.get("jingle_text_snapshot")) and
                        entry["jingle_text_snapshot"] != self.snapshot(entry),
                    "message": "Stored jingle; no automatic regeneration."}
        status = state["status"] if state else "none"
        allowed = status in {"none", "brief_failed"} and remaining > 0 and bool(self.enabled())
        messages = {
            "submitted": "Outcome pending or uncertain. No automatic retry; restore later or inspect provider logs.",
            "started": "Preparing jingle. If interrupted, operator review is required.",
            "uncertain": "Outcome uncertain. No automatic retry; inspect provider logs.",
            "brief_failed": "Brief generation failed before music submission. You may explicitly try again.",
        }
        message = messages.get(status, "")
        if status in {"none", "brief_failed"} and not allowed:
            message = "Daily jingle limit reached (resets at UTC midnight)." if remaining == 0 else "Jingle generation is disabled or unconfigured."
        return {"jingle_status": status, "can_generate": allowed,
                "remaining_today": remaining, "message": message}

    @staticmethod
    def snapshot(entry):
        return {"title": entry.get("crazyReplacement1Title", ""),
                "body": entry.get("crazyReplacement1Extract", "")}

    def generate(self, collection, rewrite_id, owner):
        entry = self.nomination(collection, rewrite_id, owner)
        key = str(entry["_id"])
        self.audio.path(key)  # Validate identity before creating state or contacting providers.
        snapshot = self.snapshot(entry)
        if not all(isinstance(v, str) and v.strip() for v in snapshot.values()):
            raise JingleError(400, "Nominated title and body are required.")
        with self.transaction() as db:
            existing = self.read(db, key)
            if entry.get("jingle_url") or self.audio.exists(key) or (
                    existing and existing["status"] != "brief_failed"):
                claimed = False
            else:
                if not self.enabled():
                    raise JingleError(503, "Jingle generation is disabled or unconfigured.")
                if self.remaining(db) == 0:
                    raise JingleError(429, "Daily jingle limit reached; resets at UTC midnight.")
                state = {"status": "started", "snapshot": snapshot,
                         "text_hash": hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
                         "request_id": str(uuid5(NAMESPACE_URL, "newsmuncher-jingle:" + key))}
                db.execute("INSERT INTO jingle_claims(day,nomination) VALUES (?,?)",
                           (self.now().date().isoformat(), key))
                self.save(db, key, state)
                claimed = True
        if not claimed:
            return self.status(collection, rewrite_id, owner)
        try:
            brief, usage = self.brief_factory(entry)
        except Exception:
            with self.transaction() as db:
                if (self.read(db, key) or {}).get("status") == "retired":
                    raise JingleError(404, "Nomination was deleted during preparation.")
                state["status"] = "brief_failed"
                self.save(db, key, state)
            return self.status(collection, rewrite_id, owner)
        with self.transaction() as db:
            if (self.read(db, key) or {}).get("status") == "retired":
                raise JingleError(404, "Nomination was deleted during preparation.")
            state.update(status="submitted", brief=brief.model_dump(), brief_usage=usage)
            self.save(db, key, state)  # Commit before sending to a paid provider.
        try:
            data = self.provider(brief, state["request_id"])
            with self.transaction() as db:
                current = self.read(db, key)
                if current and current["status"] == "retired":
                    raise JingleError(404, "Nomination was deleted during generation.")
                self.audio.save(key, data)
        except JingleError:
            raise
        except Exception:
            with self.transaction() as db:
                if (self.read(db, key) or {}).get("status") == "retired":
                    raise JingleError(404, "Nomination was deleted during generation.")
                state["status"] = "uncertain"
                self.save(db, key, state)
            return self.status(collection, rewrite_id, owner)
        try:
            return self.status(collection, rewrite_id, owner)
        except JingleError as exc:
            if exc.status == 404:
                self.try_retire_deleted(collection, entry)
            raise


service = Jingles()
