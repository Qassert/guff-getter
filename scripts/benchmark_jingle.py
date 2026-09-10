"""One explicit live proof. Never retries a POST, even after an uncertain timeout."""
import argparse
import json
import os
from pathlib import Path
import time
import subprocess
from email.parser import Parser
from uuid import uuid4

import requests
from dotenv import load_dotenv
from newsmuncher.config import ENV_FILE, DATA_DIR, PROJECT_ROOT

DUMMY_BRIEF = {
    "music_prompt": "A jaunty absurd news jingle, wonky brass, bouncy bass and cheerful English vocals, one short catchy hook.",
    "lyrics": "[Verse]\nThe mayor is a teapot, the buses run on cheese\n[Chorus]\nToot toot, teapot town! Put that biscuit down!",
    "duration_seconds": 25,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true", help="Consume Modal allowance for ONE test.")
    parser.add_argument("--endpoint", help="Deployed HTTPS URL (not a secret).")
    parser.add_argument("--modal-auth", action="store_true", help="Use existing Modal CLI login for the proof.")
    parser.add_argument("--resume-auth-failure", action="store_true", help="Resume same ID only after proven proxy 401 (no inference).")
    parser.add_argument("--attempt", choices=["benchmark", "l4-approved"], default="benchmark",
                        help="Separate explicitly approved proof; never overwrites prior attempts.")
    args = parser.parse_args()
    if not args.generate:
        print(json.dumps(DUMMY_BRIEF, indent=2))
        print("Dry run only. After deployment, --generate makes one real request.")
        return
    load_dotenv(ENV_FILE)
    endpoint = args.endpoint or os.environ.get("MODAL_JINGLE_ENDPOINT", "")
    key = os.environ.get("MODAL_JINGLE_KEY", "")
    secret = os.environ.get("MODAL_JINGLE_SECRET", "")
    if not endpoint.startswith("https://") or (not args.modal_auth and (not key or not secret)):
        raise SystemExit("Set MODAL_JINGLE_ENDPOINT, MODAL_JINGLE_KEY and MODAL_JINGLE_SECRET in root .env.")
    directory = DATA_DIR / "generated_audio"
    if args.attempt != "benchmark":
        directory = directory / args.attempt
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / "benchmark-attempt.json"
    payload = {**DUMMY_BRIEF, "request_id": str(uuid4())}
    try:
        with marker.open("x") as file:
            json.dump(payload, file, indent=2)
    except FileExistsError:
        rejected = directory / "benchmark-response.bin"
        if not args.resume_auth_failure or not rejected.exists() or rejected.read_bytes().strip() != b"modal-http: missing credentials for proxy authorization":
            raise SystemExit("A benchmark was already attempted. Inspect its outcome before any further generation.")
        payload = json.loads(marker.read_text())
        rejected.rename(directory / "benchmark-auth-rejected.txt")
    start = time.monotonic()
    if args.modal_auth:
        headers_file = directory / "benchmark-headers.txt"
        body_file = directory / "benchmark-response.bin"
        call = subprocess.run([
            str(PROJECT_ROOT / ".venv-modal/bin/modal"), "curl",
            "--silent", "--show-error", "--max-time", "600", "--request", "POST",
            "--header", "Content-Type: application/json", "--data-binary", "@" + str(marker),
            "--dump-header", str(headers_file), "--output", str(body_file),
            "--write-out", "%{http_code}", endpoint,
        ], check=True, capture_output=True, text=True)
        response = requests.Response()
        response.status_code = int(call.stdout.strip()[-3:])
        header_block = headers_file.read_text().strip().split("\n\n")[-1]
        response.headers.update(dict(Parser().parsestr(header_block.split("\n", 1)[1])))
        response._content = body_file.read_bytes()
    else:
        # No automatic POST retry and no redirects carrying credentials.
        response = requests.post(endpoint, json=payload, headers={
            "Modal-Key": key, "Modal-Secret": secret,
        }, timeout=(15, 600), allow_redirects=False)
    if response.status_code != 200:
        failure = {
            "status": "failed", "http_status": response.status_code,
            "wall_seconds": round(time.monotonic() - start, 3),
            "request_id": payload["request_id"], "audio_file": None,
            "detail": response.text[:1000],
        }
        (directory / "benchmark-report.json").write_text(json.dumps(failure, indent=2))
        print(json.dumps(failure, indent=2))
    response.raise_for_status()
    if response.status_code != 200 or response.headers.get("Content-Type", "").split(";")[0] != "audio/mpeg":
        raise SystemExit("No audio returned; retain attempt marker and inspect Modal logs.")
    if not 1000 < len(response.content) < 5_000_000:
        raise SystemExit("Unexpected audio size; retain marker and inspect Modal logs.")
    destination = directory / f"{payload['request_id']}.mp3"
    destination.write_bytes(response.content)
    report = {
        "wall_seconds": round(time.monotonic() - start, 3),
        "file_bytes": destination.stat().st_size,
        "audio_file": str(destination),
        "requested_duration_seconds": 25,
        "measurements": {k: v for k, v in response.headers.items() if k.lower().startswith("x-jingle-")},
        "cost": "Not measured. Inspect Modal billing including build, startup, CPU, RAM and idle time.",
    }
    (directory / "benchmark-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
