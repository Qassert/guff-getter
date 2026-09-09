"""Private proof endpoint. Deploy only after Modal login; no local ML installation."""
import json
import os
from pathlib import Path
import tempfile
import time

import modal

from jingle_service.contract import GenerationRequest

ACE_REVISION = "ca1e85fe9430179831e6bc6be790c332190a3866"
MODEL = "acestep-v15-turbo"
GPU = "T4"

app = modal.App("newsmuncher-jingles")
outputs = modal.Volume.from_name("newsmuncher-jingle-results", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1")
    .pip_install("uv>=0.9,<1")
    .run_commands(
        "git clone https://github.com/ace-step/ACE-Step-1.5.git /opt/acestep",
        f"git -C /opt/acestep checkout {ACE_REVISION}",
        "cd /opt/acestep && uv sync --frozen --no-dev",
        # Download only the DiT, VAE and text encoder during CPU image build.
        'cd /opt/acestep && .venv/bin/python -c "from huggingface_hub import snapshot_download; '
        "snapshot_download('ACE-Step/Ace-Step1.5', local_dir='checkpoints', "
        "allow_patterns=['acestep-v15-turbo/*','vae/*','Qwen3-Embedding-0.6B/*'])\"",
    )
    .env({"PYTHONPATH": "/opt/acestep:/opt/acestep/.venv/lib/python3.11/site-packages"})
    .add_local_python_source("jingle_service")
)


@app.cls(image=image, gpu=GPU, cpu=2, memory=16384, min_containers=0,
         max_containers=1, buffer_containers=0, scaledown_window=2,
         timeout=180, startup_timeout=600, retries=0,
         volumes={"/results": outputs})
@modal.concurrent(max_inputs=1)
class JingleGenerator:
    @modal.enter()
    def load(self):
        from acestep.handler import AceStepHandler
        start = time.monotonic()
        self.handler = AceStepHandler()
        message, ok = self.handler.initialize_service(
            project_root="/opt/acestep", config_path=MODEL, device="cuda",
            use_flash_attention=False, compile_model=False,
            offload_to_cpu=True, offload_dit_to_cpu=False,
        )
        if not ok:
            raise RuntimeError(message)
        self.load_seconds = time.monotonic() - start

    @modal.fastapi_endpoint(method="POST", requires_proxy_auth=True)
    def generate(self, payload: dict):
        from fastapi import HTTPException
        from fastapi.responses import Response
        from acestep.inference import GenerationParams, GenerationConfig, generate_music
        import subprocess

        request = GenerationRequest.model_validate(payload)
        identifier = str(request.request_id)
        audio = Path("/results") / f"{identifier}.mp3"
        marker = audio.with_suffix(".json")
        outputs.reload()
        brief = request.model_dump(mode="json")
        if marker.exists():
            prior = json.loads(marker.read_text())
            if prior["request"] != brief:
                raise HTTPException(409, "Request ID already belongs to another brief.")
            if audio.exists() and prior.get("status") == "complete":
                return Response(audio.read_bytes(), media_type="audio/mpeg",
                                headers={"X-Jingle-Cached": "true"})
            raise HTTPException(409, "Previous outcome uncertain; inspect Modal logs. Do not resubmit with a new ID.")

        # Durable marker before inference: interrupted attempts never silently regenerate.
        with marker.open("x") as stream:
            json.dump({"request": brief, "status": "started"}, stream)
        outputs.commit()
        start = time.monotonic()
        with tempfile.TemporaryDirectory() as temporary:
            result = generate_music(
                self.handler, None,
                GenerationParams(caption=request.music_prompt, lyrics=request.lyrics,
                                 duration=request.duration_seconds, vocal_language="en",
                                 thinking=False, use_cot_metas=False, use_cot_caption=False,
                                 use_cot_language=False, inference_steps=8),
                GenerationConfig(batch_size=1, audio_format="wav"),
                save_dir=temporary,
            )
            if not result.success or len(result.audios) != 1:
                raise HTTPException(502, "Music generation failed; attempt retained for inspection.")
            destination = audio.with_suffix(".tmp.mp3")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", result.audios[0]["path"],
                            "-t", str(request.duration_seconds), "-codec:a", "libmp3lame",
                            "-b:a", "128k", str(destination)], check=True, timeout=30)
            os.replace(destination, audio)
        measured_duration = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
            text=True, timeout=10,
        ).strip())
        elapsed = time.monotonic() - start
        metadata = {"request": brief, "status": "complete", "gpu": GPU, "model": MODEL,
                    "revision": ACE_REVISION, "generation_seconds": elapsed,
                    "model_load_seconds": self.load_seconds, "duration_seconds": measured_duration,
                    "bytes": audio.stat().st_size}
        temporary_marker = marker.with_suffix(".tmp.json")
        temporary_marker.write_text(json.dumps(metadata))
        os.replace(temporary_marker, marker)
        outputs.commit()
        return Response(audio.read_bytes(), media_type="audio/mpeg", headers={
            "X-Jingle-GPU": GPU, "X-Jingle-Model": MODEL,
            "X-Jingle-Generation-Seconds": str(round(elapsed, 3)),
            "X-Jingle-Load-Seconds": str(round(self.load_seconds, 3)),
            "X-Jingle-Duration-Seconds": str(round(measured_duration, 3)),
        })
