from newsmuncher.config import AVATARS_DIR, STATIC_DIR, TEMPLATES_DIR, GENERATED_IMAGES_DIR, GENERATED_AUDIO_DIR
from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore
from newsmuncher.api.reusable import app as reusable_app
from newsmuncher.api.entries import router as main_api_router
from newsmuncher.api.pets import router as pet_router
from newsmuncher.api.previews import router as temp_router

from newsmuncher.api.jingles import router as jingle_router

app = FastAPI()

# ✅ Serve avatars
app.mount("/avatars", StaticFiles(directory=AVATARS_DIR), name="avatars")

# ✅ Serve static files (CSS & JS) from the package static directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/generated-images", StaticFiles(directory=GENERATED_IMAGES_DIR), name="generated-images")

GENERATED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
class AudioFiles(StaticFiles):
    async def get_response(self, path, scope):
        if not path.endswith(".mp3"):
            raise HTTPException(404)
        return await super().get_response(path, scope)

app.mount("/generated-audio", AudioFiles(directory=GENERATED_AUDIO_DIR), name="generated-audio")
app.include_router(jingle_router)

# ✅ Include API routers properly
app.include_router(main_api_router)
app.include_router(pet_router, prefix="/pets", tags=["Pets"])
app.include_router(temp_router, prefix="/temp", tags=["Temp Data"])

# ✅ Mount reusable API
app.mount("/reusable", reusable_app)

# ✅ Set up Jinja2 templates (keeps template rendering working)
templates = Jinja2Templates(directory=TEMPLATES_DIR)
