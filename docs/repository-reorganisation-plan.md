# Repository reorganisation plan

This plan was prepared from checkpoint `309aa54` on `feature/video-animation`. It maps every tracked file before structural work. `MOVE` means a planned location, not permission to execute every move in this run. `OBSOLETE` records audit findings only; nothing in that class is deleted. Runtime data and stored public URLs remain in place.

## Target structure

```text
.
├── AGENTS.md, CURRENT_WORK.md, README.md
├── docs/
│   ├── status/                 # feature handovers and implementation records
│   └── diagnostics/            # operator-facing diagnostic guides
├── newsmuncher/
│   ├── api/                    # FastAPI route modules and HTTP boundaries
│   ├── services/               # application/domain orchestration and persistence
│   ├── integrations/           # narrowly scoped external-provider transports
│   ├── jobs/                   # application ingestion/background jobs
│   ├── utils/                  # shared pure utilities
│   ├── resources/              # prompts and word banks
│   ├── templates/              # Jinja templates
│   └── static/
│       ├── js/
│       ├── css/
│       ├── images/(buttons, udders, backgrounds)/
│       └── audio/(voices, effects/(ui, munge, udder))/
├── scripts/
│   ├── maintenance/            # database/account/word-bank administration
│   └── diagnostics/            # opt-in benchmarks and provider diagnostics
├── tests/(python, frontend)/
├── jingle_service/             # active shared contracts plus retained legacy Modal source
├── data/                       # unchanged seeds, avatars, state and generated media roots
└── requirements.txt
```

No empty `models`, `repositories`, or `migrations` package is proposed. Current persistence is coupled to existing services/routes; separating it would be a later functional refactor. If database migrations are introduced, use `scripts/migrations/`, but do not manufacture that directory now.

## Batch boundaries

1. **Batch A (this run):** move feature/status and diagnostic Markdown into `docs/`; update documentation-only references.
2. **Batch B:** static media directories, with every Jinja/JS/CSS URL updated and historical URL compatibility assessed first.
3. **Batch C:** JavaScript/CSS folders and all template/test references.
4. **Batch D:** only clearly isolated backend provider transport modules; retain public imports or add compatibility re-exports where needed.
5. **Batch E:** split Python and Node tests and update collection/fixture paths.
6. **Batch F:** organize maintenance/diagnostic scripts and reassess dependency placement. Scripts are deferred because tests, docs and operational invocations rely on their current module paths.

## Compatibility constraints

- Never move `data/` runtime roots or generated/user media. Stored MongoDB/SQLite paths and authenticated media routes depend on them.
- Static moves change public URLs. Batch B requires exhaustive template, JavaScript and CSS updates plus a decision on aliases for any stored URL.
- Python moves affect patches/import strings in tests and scripts. Batch D must preserve import compatibility.
- The narration API, saved jingle lookup, WaveSpeed claims, ping-pong sidecars, word claims and recovery tooling are compatibility surfaces, not cleanup targets.
- `gallery-back.png` is referenced but missing; resolve that defect separately rather than treating the reference as dead.
- `jingle_service.contract` and `jingle_service.genres` are active production imports, so the package remains top-level.

## Batch B implementation

- Active source-udder artwork moved from `images/udder/` to `images/udders/source/`.
- Active six-teat MUNGE artwork moved from `images/munge button/` to `images/udders/munge/`.
- The parchment moved to `images/backgrounds/`; its CSS references remain relative to the same `/static` mount.
- Seven spoken controls moved to `audio/voices/`. Interaction sounds moved to `audio/effects/ui/`, `audio/effects/munge/`, and `audio/effects/udder/`.
- `image-stub.svg` remains at `/static/image-stub.svg` because that URL is persisted in rewrite state. Gallery button artwork remains in `images/buttons/` because it is already correctly grouped.
- All audit-classified obsolete/reference artwork remains at its original path. The missing `images/buttons/gallery-back.png` remains a separately recorded defect; no replacement was invented.
- Existing stylesheet and affected JavaScript cache tokens were advanced to `static-assets-b1` so browsers fetch references to the new paths.
- Batch B changes paths and references only. Image/audio bytes, generated media, animations, playback logic, API contracts, database paths and provider code remain unchanged.

## Batch C implementation

- Eleven Creation scripts moved unchanged to `static/js/creation/`; Gallery JavaScript moved to `static/js/gallery/`; shared mode navigation moved to `static/js/shared/`.
- Shared/base CSS moved to `static/css/shared/`; Gallery CSS moved to `static/css/gallery/`.
- Script tag order is unchanged. Templates now load the new URLs with the common `frontend-c1` cache token.
- CSS parchment references use `../../images/backgrounds/parchment.png`, preserving the resolved `/static/images/backgrounds/parchment.png` URL after the stylesheets moved two levels deeper.
- Inactive historical `static/narration.js` and obsolete `static/profile-editing.js` remain at their existing paths pending a separate compatibility/deletion decision.
- No JavaScript or CSS content was refactored beyond the required CSS-relative asset path correction.

## Batch D implementation

- Moved the isolated WaveSpeed HTTP transport to `newsmuncher/integrations/wavespeed.py` and added the integrations package.
- Production video orchestration and the opt-in smoke-test utility now import the transport from its responsibility-based location.
- Retained `newsmuncher/services/wavespeed.py` as a compatibility import for external callers; provider payloads, polling, retries, diagnostics and persistence behavior are unchanged.
- Updated direct tests and documentation references. No other backend service, API route, database path or historical-media boundary was moved.

## Batch E implementation

- Moved all 16 Node tests to `tests/frontend/` and all 26 Python tests to `tests/python/`.
- Updated Node module paths, Python repository-root calculations, cross-runner invocations and documented test commands for the additional directory level.
- Pytest discovery and Node's test runner retain the exact Batch D baseline; test behavior and assertions were not changed in this structural batch.

## Batch F implementation

- Moved database, password and word-bank administration into `scripts/maintenance/`.
- Moved opt-in jingle/TTS/video diagnostics into `scripts/diagnostics/`; retained all dry-run and explicit paid-run safeguards.
- Updated module imports, patch targets, repository-root calculations and every documented command. Added package markers so `python -m` invocation remains supported from the repository root.
- Runtime configuration, recovery behavior, generated-media paths and provider request logic are unchanged.

## Complete tracked-file map

Summary: **115 MOVE, 86 KEEP, 6 REVIEW, 17 OBSOLETE** across 224 tracked files.

| Old path | Class | Proposed path | Evidence / batch |
| --- | --- | --- | --- |
| `.env.example` | KEEP | `.env.example` | Already appropriate or compatibility-sensitive |
| `.gitignore` | KEEP | `.gitignore` | Already appropriate or compatibility-sensitive |
| `AGENTS.md` | KEEP | `AGENTS.md` | Already appropriate or compatibility-sensitive |
| `CURRENT_WORK.md` | KEEP | `CURRENT_WORK.md` | Already appropriate or compatibility-sensitive |
| `JINGLE_IMPLEMENTATION_STATUS.md` | MOVE | `docs/status/jingle-implementation.md` | Batch A documentation |
| `PROMOTION_GALLERY_STATUS.md` | MOVE | `docs/status/promotion-gallery.md` | Batch A documentation |
| `README.md` | KEEP | `README.md` | Already appropriate or compatibility-sensitive |
| `VIDEO_ANIMATION_STATUS.md` | MOVE | `docs/status/video-animation.md` | Batch A documentation |
| `WORD_SHUFFLE_STATUS.md` | MOVE | `docs/status/word-shuffle.md` | Batch A documentation |
| `__init__.py` | OBSOLETE | `__init__.py` | Audit candidate; retain until deletion is approved |
| `data/avatars/0f46e64588f64047adb0d7f837f6afa3.jpg` | KEEP | `data/avatars/0f46e64588f64047adb0d7f837f6afa3.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/14a2c42737f74ad69430d3c66445041c.jpg` | KEEP | `data/avatars/14a2c42737f74ad69430d3c66445041c.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/1776d4e9b0d94b45b273ec4fbdbf5fcf.jpg` | KEEP | `data/avatars/1776d4e9b0d94b45b273ec4fbdbf5fcf.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/1e3df0c547214e79b319ac1141b4b811.jpg` | KEEP | `data/avatars/1e3df0c547214e79b319ac1141b4b811.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/3d85ababc0fd44609c05e2989176bf36.jpg` | KEEP | `data/avatars/3d85ababc0fd44609c05e2989176bf36.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/4899192d2edb455989f68644fa016ac5.jpg` | KEEP | `data/avatars/4899192d2edb455989f68644fa016ac5.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/5913695b85fb45e38ef3d01803568eca.jpg` | KEEP | `data/avatars/5913695b85fb45e38ef3d01803568eca.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/70281879d45a4db9b99a002e29ba22a7.jpg` | KEEP | `data/avatars/70281879d45a4db9b99a002e29ba22a7.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/83f9dedf65ea4cdfacea3a5ac046431e.jpg` | KEEP | `data/avatars/83f9dedf65ea4cdfacea3a5ac046431e.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/9cfe3dd3ccef49be8eff86883dc6e9ef.jpg` | KEEP | `data/avatars/9cfe3dd3ccef49be8eff86883dc6e9ef.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/c3a788eddd284c5f826ad635ec2713d9.jpg` | KEEP | `data/avatars/c3a788eddd284c5f826ad635ec2713d9.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/e61553cd8de74ff090ecc35ce15a4722.jpg` | KEEP | `data/avatars/e61553cd8de74ff090ecc35ce15a4722.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/efc534abbebe400ba74496b0651082cd.jpg` | KEEP | `data/avatars/efc534abbebe400ba74496b0651082cd.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/f0cf7264fb5e431a94afa34174dc8d7b.jpg` | KEEP | `data/avatars/f0cf7264fb5e431a94afa34174dc8d7b.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/fa33a57427d241ebac2d6ebbc9f344f3.jpg` | KEEP | `data/avatars/fa33a57427d241ebac2d6ebbc9f344f3.jpg` | Already appropriate or compatibility-sensitive |
| `data/avatars/fc0b36eb23294b7a9909d61c66eb70d5.jpg` | KEEP | `data/avatars/fc0b36eb23294b7a9909d61c66eb70d5.jpg` | Already appropriate or compatibility-sensitive |
| `data/generated_audio/.gitkeep` | KEEP | `data/generated_audio/.gitkeep` | Already appropriate or compatibility-sensitive |
| `data/generated_images/.gitkeep` | KEEP | `data/generated_images/.gitkeep` | Already appropriate or compatibility-sensitive |
| `data/previews/.gitkeep` | KEEP | `data/previews/.gitkeep` | Already appropriate or compatibility-sensitive |
| `data/seeds/historicalFunnies.json` | KEEP | `data/seeds/historicalFunnies.json` | Already appropriate or compatibility-sensitive |
| `data/seeds/lonelyHearts.json` | KEEP | `data/seeds/lonelyHearts.json` | Already appropriate or compatibility-sensitive |
| `jingle_service/__init__.py` | KEEP | `jingle_service/__init__.py` | Already appropriate or compatibility-sensitive |
| `jingle_service/contract.py` | KEEP | `jingle_service/contract.py` | Already appropriate or compatibility-sensitive |
| `jingle_service/genres.py` | KEEP | `jingle_service/genres.py` | Already appropriate or compatibility-sensitive |
| `jingle_service/modal_app.py` | REVIEW | `jingle_service/modal_app.py` | Historical compatibility or tooling boundary |
| `jingle_service/requirements-dev.txt` | REVIEW | `jingle_service/requirements-dev.txt` | Historical compatibility or tooling boundary |
| `newsmuncher/__init__.py` | KEEP | `newsmuncher/__init__.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/__init__.py` | KEEP | `newsmuncher/api/__init__.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/entries.py` | KEEP | `newsmuncher/api/entries.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/jingles.py` | KEEP | `newsmuncher/api/jingles.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/narrations.py` | REVIEW | `newsmuncher/api/narrations.py` | Historical compatibility or tooling boundary |
| `newsmuncher/api/pets.py` | KEEP | `newsmuncher/api/pets.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/previews.py` | KEEP | `newsmuncher/api/previews.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/promotion_gallery.py` | KEEP | `newsmuncher/api/promotion_gallery.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/reusable.py` | KEEP | `newsmuncher/api/reusable.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/api/videos.py` | KEEP | `newsmuncher/api/videos.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/config.py` | KEEP | `newsmuncher/config.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/endpoints.py` | OBSOLETE | `newsmuncher/endpoints.py` | Audit candidate; retain until deletion is approved |
| `newsmuncher/jobs/__init__.py` | KEEP | `newsmuncher/jobs/__init__.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/jobs/fetch_historical_funny.py` | KEEP | `newsmuncher/jobs/fetch_historical_funny.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/jobs/fetch_people.py` | KEEP | `newsmuncher/jobs/fetch_people.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/jobs/fetch_poem.py` | KEEP | `newsmuncher/jobs/fetch_poem.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/jobs/fetch_wikipedia.py` | KEEP | `newsmuncher/jobs/fetch_wikipedia.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/jobs/process_data.py` | KEEP | `newsmuncher/jobs/process_data.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/main.py` | KEEP | `newsmuncher/main.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/prompts/rewrite.txt` | KEEP | `newsmuncher/resources/prompts/rewrite.txt` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/words/adverbs.csv` | KEEP | `newsmuncher/resources/words/adverbs.csv` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/words/animalsAndObjects.csv` | KEEP | `newsmuncher/resources/words/animalsAndObjects.csv` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/words/names.csv` | KEEP | `newsmuncher/resources/words/names.csv` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/words/nouns.csv` | KEEP | `newsmuncher/resources/words/nouns.csv` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/words/places.csv` | KEEP | `newsmuncher/resources/words/places.csv` | Already appropriate or compatibility-sensitive |
| `newsmuncher/resources/words/slang.csv` | KEEP | `newsmuncher/resources/words/slang.csv` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/__init__.py` | KEEP | `newsmuncher/services/__init__.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/gallery_sessions.py` | KEEP | `newsmuncher/services/gallery_sessions.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/image_generation.py` | KEEP | `newsmuncher/services/image_generation.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/jingle_brief.py` | KEEP | `newsmuncher/services/jingle_brief.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/jingles.py` | KEEP | `newsmuncher/services/jingles.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/moderation.py` | KEEP | `newsmuncher/services/moderation.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/narration.py` | REVIEW | `newsmuncher/services/narration.py` | Historical compatibility or tooling boundary |
| `newsmuncher/services/openai_tts.py` | REVIEW | `newsmuncher/services/openai_tts.py` | Historical compatibility or tooling boundary |
| `newsmuncher/services/profile_background.py` | KEEP | `newsmuncher/services/profile_background.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/promotion_gallery.py` | KEEP | `newsmuncher/services/promotion_gallery.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/rewrite_title.py` | KEEP | `newsmuncher/services/rewrite_title.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/video.py` | KEEP | `newsmuncher/services/video.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/video_pingpong.py` | KEEP | `newsmuncher/services/video_pingpong.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/video_prompt.py` | KEEP | `newsmuncher/services/video_prompt.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/services/wavespeed.py` | MOVE | `newsmuncher/integrations/wavespeed.py` | Batch D provider transport |
| `newsmuncher/services/word_shuffle.py` | KEEP | `newsmuncher/services/word_shuffle.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/audio/Create_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/Create_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/Enhance_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/Enhance_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/Gallery_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/Gallery_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/Munge it/Funny Run Up Take - QuickSounds.com.mp3` | MOVE | `newsmuncher/static/audio/effects/munge/Funny Run Up Take - QuickSounds.com.mp3` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/Man screaming aaaah - QuickSounds.com.mp3` | MOVE | `newsmuncher/static/audio/effects/munge/Man screaming aaaah - QuickSounds.com.mp3` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/fart-02.wav` | MOVE | `newsmuncher/static/audio/effects/munge/fart-02.wav` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/fart-03.wav` | MOVE | `newsmuncher/static/audio/effects/munge/fart-03.wav` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/fart-08.wav` | MOVE | `newsmuncher/static/audio/effects/munge/fart-08.wav` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/fart-quick-puffy-brukowskij-fart-quick-and-puffy-02-1-0m00s.mp3` | MOVE | `newsmuncher/static/audio/effects/munge/fart-quick-puffy-brukowskij-fart-quick-and-puffy-02-1-0m00s.mp3` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/fart-raspy-flab-om-fx-1-00-02.mp3` | MOVE | `newsmuncher/static/audio/effects/munge/fart-raspy-flab-om-fx-1-00-02.mp3` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/fart-squeak-01.wav` | MOVE | `newsmuncher/static/audio/effects/munge/fart-squeak-01.wav` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/hello meme funny - QuickSounds.com.mp3` | MOVE | `newsmuncher/static/audio/effects/munge/hello meme funny - QuickSounds.com.mp3` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/slap sound effect funny memes - QuickSounds.com.mp3` | MOVE | `newsmuncher/static/audio/effects/munge/slap sound effect funny memes - QuickSounds.com.mp3` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Munge it/suspense.wav` | MOVE | `newsmuncher/static/audio/effects/munge/suspense.wav` | Batch B normalize MUNGE audio directory |
| `newsmuncher/static/audio/Mute_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/Mute_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/NewsMuncher_Edit_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/NewsMuncher_Edit_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/NewsMuncher_Promote_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/NewsMuncher_Promote_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/Play_Shout.mp3` | MOVE | `newsmuncher/static/audio/voices/Play_Shout.mp3` | Batch B voice clips |
| `newsmuncher/static/audio/farty_button_squelch.wav` | MOVE | `newsmuncher/static/audio/effects/ui/farty_button_squelch.wav` | Batch B UI effects |
| `newsmuncher/static/audio/squelch_01_wet_pop.wav` | MOVE | `newsmuncher/static/audio/effects/ui/squelch_01_wet_pop.wav` | Batch B UI effects |
| `newsmuncher/static/audio/squelch_02_suction_slurp.wav` | MOVE | `newsmuncher/static/audio/effects/ui/squelch_02_suction_slurp.wav` | Batch B UI effects |
| `newsmuncher/static/audio/udder/mixkit-cartoon-catapult-737.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-cartoon-catapult-737.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-cartoon-fail-blow-fart-3053.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-cartoon-fail-blow-fart-3053.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-cartoon-fart-sound-2891.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-cartoon-fart-sound-2891.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-cartoon-laugh-voice-2882.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-cartoon-laugh-voice-2882.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-falling-into-mud-surface-385.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-falling-into-mud-surface-385.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-funny-cartoon-fast-splat-2889.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-funny-cartoon-fast-splat-2889.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-funny-clown-horn-sounds-2886.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-funny-clown-horn-sounds-2886.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-long-kiss-clean-sound-2188.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-long-kiss-clean-sound-2188.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/mixkit-wet-accident-fart-3041.wav` | MOVE | `newsmuncher/static/audio/effects/udder/mixkit-wet-accident-fart-3041.wav` | Batch B source-udder effects |
| `newsmuncher/static/audio/udder/suspense.wav` | MOVE | `newsmuncher/static/audio/effects/udder/suspense.wav` | Batch B source-udder effects |
| `newsmuncher/static/creation-meta.js` | MOVE | `newsmuncher/static/js/creation/creation-meta.js` | Batch C Creation JavaScript |
| `newsmuncher/static/embellish.js` | MOVE | `newsmuncher/static/js/creation/embellish.js` | Batch C Creation JavaScript |
| `newsmuncher/static/image-background.js` | MOVE | `newsmuncher/static/js/creation/image-background.js` | Batch C Creation JavaScript |
| `newsmuncher/static/image-colors.js` | MOVE | `newsmuncher/static/js/creation/image-colors.js` | Batch C Creation JavaScript |
| `newsmuncher/static/image-loading.js` | MOVE | `newsmuncher/static/js/creation/image-loading.js` | Batch C Creation JavaScript |
| `newsmuncher/static/image-stub.svg` | KEEP | `newsmuncher/static/image-stub.svg` | Persisted public URL; compatibility requires original path |
| `newsmuncher/static/images/Furry Cow-Spot Button Sprite Sheet.png` | OBSOLETE | `newsmuncher/static/images/Furry Cow-Spot Button Sprite Sheet.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/Whimsical Fur-Button Gallery Interface.png` | OBSOLETE | `newsmuncher/static/images/Whimsical Fur-Button Gallery Interface.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/buttons/Coral Arrow on Cowhide Cushion.png` | KEEP | `newsmuncher/static/images/buttons/Coral Arrow on Cowhide Cushion.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/buttons/Furry Cow-Print Button States Spec.png` | OBSOLETE | `newsmuncher/static/images/buttons/Furry Cow-Print Button States Spec.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/buttons/Furry Cowhide Megaphone Emblem.png` | KEEP | `newsmuncher/static/images/buttons/Furry Cowhide Megaphone Emblem.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/buttons/Furry Cowhide Pencil Badge.png` | KEEP | `newsmuncher/static/images/buttons/Furry Cowhide Pencil Badge.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/buttons/Magical Cowhide Wand Emblem.png` | KEEP | `newsmuncher/static/images/buttons/Magical Cowhide Wand Emblem.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/buttons/Rustic Cowhide Volume Icon.png` | KEEP | `newsmuncher/static/images/buttons/Rustic Cowhide Volume Icon.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/buttons/create-idle.png` | KEEP | `newsmuncher/static/images/buttons/create-idle.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/buttons/gallery-idle.png` | KEEP | `newsmuncher/static/images/buttons/gallery-idle.png` | Already appropriate or compatibility-sensitive |
| `newsmuncher/static/images/munge button/Furry Cow Udder Button Asset Sheet.png` | OBSOLETE | `newsmuncher/static/images/munge button/Furry Cow Udder Button Asset Sheet.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/munge button/munge-body.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-body.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/munge button/munge-teat-1.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-teat-1.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/munge button/munge-teat-2.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-teat-2.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/munge button/munge-teat-3.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-teat-3.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/munge button/munge-teat-4.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-teat-4.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/munge button/munge-teat-5.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-teat-5.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/munge button/munge-teat-6.png` | MOVE | `newsmuncher/static/images/udders/munge/munge-teat-6.png` | Batch B normalize MUNGE image directory |
| `newsmuncher/static/images/udder/cow-body.png` | OBSOLETE | `newsmuncher/static/images/udder/cow-body.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/full-udder.png` | OBSOLETE | `newsmuncher/static/images/udder/full-udder.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/master_udder.png` | OBSOLETE | `newsmuncher/static/images/udder/master_udder.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/teat-1.png` | OBSOLETE | `newsmuncher/static/images/udder/teat-1.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/teat-2.png` | OBSOLETE | `newsmuncher/static/images/udder/teat-2.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/teat-3.png` | OBSOLETE | `newsmuncher/static/images/udder/teat-3.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/teat-4.png` | OBSOLETE | `newsmuncher/static/images/udder/teat-4.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/teat-5.png` | OBSOLETE | `newsmuncher/static/images/udder/teat-5.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/udder-body.png` | OBSOLETE | `newsmuncher/static/images/udder/udder-body.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/udder-master-body.png` | MOVE | `newsmuncher/static/images/udders/source/udder-master-body.png` | Batch B active source-udder artwork |
| `newsmuncher/static/images/udder/udder-source.png` | OBSOLETE | `newsmuncher/static/images/udder/udder-source.png` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/images/udder/udder-teat-1.png` | MOVE | `newsmuncher/static/images/udders/source/udder-teat-1.png` | Batch B active source-udder artwork |
| `newsmuncher/static/images/udder/udder-teat-2.png` | MOVE | `newsmuncher/static/images/udders/source/udder-teat-2.png` | Batch B active source-udder artwork |
| `newsmuncher/static/images/udder/udder-teat-3.png` | MOVE | `newsmuncher/static/images/udders/source/udder-teat-3.png` | Batch B active source-udder artwork |
| `newsmuncher/static/images/udder/udder-teat-4.png` | MOVE | `newsmuncher/static/images/udders/source/udder-teat-4.png` | Batch B active source-udder artwork |
| `newsmuncher/static/images/udder/udder-teat-5.png` | MOVE | `newsmuncher/static/images/udders/source/udder-teat-5.png` | Batch B active source-udder artwork |
| `newsmuncher/static/jingles.js` | MOVE | `newsmuncher/static/js/creation/jingles.js` | Batch C Creation JavaScript |
| `newsmuncher/static/mode-nav.js` | MOVE | `newsmuncher/static/js/shared/mode-nav.js` | Batch C shared navigation |
| `newsmuncher/static/munge-control.js` | MOVE | `newsmuncher/static/js/creation/munge-control.js` | Batch C Creation JavaScript |
| `newsmuncher/static/narration.js` | REVIEW | `newsmuncher/static/narration.js` | Historical compatibility or tooling boundary |
| `newsmuncher/static/parchment.png` | MOVE | `newsmuncher/static/images/backgrounds/parchment.png` | Batch B parchment background |
| `newsmuncher/static/profile-editing.js` | OBSOLETE | `newsmuncher/static/profile-editing.js` | Audit candidate; retain until deletion is approved |
| `newsmuncher/static/promotion-gallery.css` | MOVE | `newsmuncher/static/css/gallery/promotion-gallery.css` | Batch C Gallery CSS |
| `newsmuncher/static/promotion-gallery.js` | MOVE | `newsmuncher/static/js/gallery/promotion-gallery.js` | Batch C Gallery JavaScript |
| `newsmuncher/static/script.js` | MOVE | `newsmuncher/static/js/creation/script.js` | Batch C Creation JavaScript |
| `newsmuncher/static/source-udder.js` | MOVE | `newsmuncher/static/js/creation/source-udder.js` | Batch C Creation JavaScript |
| `newsmuncher/static/styles.css` | MOVE | `newsmuncher/static/css/shared/styles.css` | Batch C shared/base CSS |
| `newsmuncher/static/udder-sounds.js` | MOVE | `newsmuncher/static/js/creation/udder-sounds.js` | Batch C Creation JavaScript |
| `newsmuncher/static/video.js` | MOVE | `newsmuncher/static/js/creation/video.js` | Batch C Creation JavaScript |
| `newsmuncher/templates/adopt_pet.html` | KEEP | `newsmuncher/templates/adopt_pet.html` | Already appropriate or compatibility-sensitive |
| `newsmuncher/templates/base.html` | KEEP | `newsmuncher/templates/base.html` | Already appropriate or compatibility-sensitive |
| `newsmuncher/templates/login_pet.html` | KEEP | `newsmuncher/templates/login_pet.html` | Already appropriate or compatibility-sensitive |
| `newsmuncher/templates/pet_profile.html` | KEEP | `newsmuncher/templates/pet_profile.html` | Already appropriate or compatibility-sensitive |
| `newsmuncher/templates/promotion_gallery.html` | KEEP | `newsmuncher/templates/promotion_gallery.html` | Already appropriate or compatibility-sensitive |
| `newsmuncher/templates/view_pets.html` | KEEP | `newsmuncher/templates/view_pets.html` | Already appropriate or compatibility-sensitive |
| `newsmuncher/utils/__init__.py` | KEEP | `newsmuncher/utils/__init__.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/utils/clean_data.py` | KEEP | `newsmuncher/utils/clean_data.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/utils/file_handler.py` | KEEP | `newsmuncher/utils/file_handler.py` | Already appropriate or compatibility-sensitive |
| `newsmuncher/utils/source_preprocessing.py` | KEEP | `newsmuncher/utils/source_preprocessing.py` | Already appropriate or compatibility-sensitive |
| `requirements.txt` | KEEP | `requirements.txt` | Already appropriate or compatibility-sensitive |
| `scripts/__init__.py` | KEEP | `scripts/__init__.py` | Already appropriate or compatibility-sensitive |
| `scripts/diagnostics/benchmark_jingle.py` | MOVE | `scripts/diagnostics/benchmark_jingle.py` | Later script batch; preserve opt-in safeguards |
| `scripts/maintenance/check_database.py` | MOVE | `scripts/maintenance/check_database.py` | Later script batch; preserve admin semantics |
| `scripts/maintenance/clean_word_banks.py` | MOVE | `scripts/maintenance/clean_word_banks.py` | Later script batch; preserve admin semantics |
| `scripts/diagnostics/compare_jingle_reference.py` | MOVE | `scripts/diagnostics/compare_jingle_reference.py` | Later script batch; preserve opt-in safeguards |
| `scripts/diagnostics/compare_tts.py` | MOVE | `scripts/diagnostics/compare_tts.py` | Later script batch; preserve opt-in safeguards |
| `scripts/maintenance/reset_pet_password.py` | MOVE | `scripts/maintenance/reset_pet_password.py` | Later script batch; preserve admin semantics |
| `scripts/maintenance/reset_word_claims.py` | MOVE | `scripts/maintenance/reset_word_claims.py` | Later script batch; preserve admin semantics |
| `scripts/video_smoke_test.md` | MOVE | `docs/diagnostics/video-smoke-test.md` | Batch A documentation |
| `scripts/diagnostics/video_smoke_test.py` | MOVE | `scripts/diagnostics/video_smoke_test.py` | Later script batch; preserve opt-in safeguards |
| `tests/creation_meta.test.js` | MOVE | `tests/frontend/creation_meta.test.js` | Batch E frontend tests |
| `tests/creation_title_presentation.test.js` | MOVE | `tests/frontend/creation_title_presentation.test.js` | Batch E frontend tests |
| `tests/embellish.test.js` | MOVE | `tests/frontend/embellish.test.js` | Batch E frontend tests |
| `tests/frontend/image_background.test.js` | MOVE | `tests/frontend/image_background.test.js` | Batch E frontend tests |
| `tests/frontend/image_flow.test.js` | MOVE | `tests/frontend/image_flow.test.js` | Batch E frontend tests |
| `tests/image_loading.test.js` | MOVE | `tests/frontend/image_loading.test.js` | Batch E frontend tests |
| `tests/frontend/jingles.test.js` | MOVE | `tests/frontend/jingles.test.js` | Batch E frontend tests |
| `tests/loading_audio.test.js` | MOVE | `tests/frontend/loading_audio.test.js` | Batch E frontend tests |
| `tests/media_orchestration.test.js` | MOVE | `tests/frontend/media_orchestration.test.js` | Batch E frontend tests |
| `tests/munge_control.test.js` | MOVE | `tests/frontend/munge_control.test.js` | Batch E frontend tests |
| `tests/frontend/narration.test.js` | MOVE | `tests/frontend/narration.test.js` | Batch E frontend tests |
| `tests/frontend/profile_editing.test.js` | MOVE | `tests/frontend/profile_editing.test.js` | Batch E frontend tests |
| `tests/frontend/promotion_gallery.test.js` | MOVE | `tests/frontend/promotion_gallery.test.js` | Batch E frontend tests |
| `tests/source_udder.test.js` | MOVE | `tests/frontend/source_udder.test.js` | Batch E frontend tests |
| `tests/test_clean_word_banks.py` | MOVE | `tests/python/test_clean_word_banks.py` | Batch E Python tests |
| `tests/test_compare_tts.py` | MOVE | `tests/python/test_compare_tts.py` | Batch E Python tests |
| `tests/test_contender_frontend.py` | MOVE | `tests/python/test_contender_frontend.py` | Batch E Python tests |
| `tests/python/test_copy_edit_pass.py` | MOVE | `tests/python/test_copy_edit_pass.py` | Batch E Python tests |
| `tests/python/test_dating_source.py` | MOVE | `tests/python/test_dating_source.py` | Batch E Python tests |
| `tests/python/test_draft_lifecycle.py` | MOVE | `tests/python/test_draft_lifecycle.py` | Batch E Python tests |
| `tests/python/test_image_generation.py` | MOVE | `tests/python/test_image_generation.py` | Batch E Python tests |
| `tests/test_image_redo.py` | MOVE | `tests/python/test_image_redo.py` | Batch E Python tests |
| `tests/test_jingle_brief.py` | MOVE | `tests/python/test_jingle_brief.py` | Batch E Python tests |
| `tests/python/test_jingle_frontend.py` | MOVE | `tests/python/test_jingle_frontend.py` | Batch E Python tests |
| `tests/test_jingle_genre.py` | MOVE | `tests/python/test_jingle_genre.py` | Batch E Python tests |
| `tests/test_jingle_genre_truncate.py` | MOVE | `tests/python/test_jingle_genre_truncate.py` | Batch E Python tests |
| `tests/test_jingle_reference.py` | MOVE | `tests/python/test_jingle_reference.py` | Batch E Python tests |
| `tests/python/test_jingles.py` | MOVE | `tests/python/test_jingles.py` | Batch E Python tests |
| `tests/test_loading_images.py` | MOVE | `tests/python/test_loading_images.py` | Batch E Python tests |
| `tests/test_modal_schema_diagnostic.py` | MOVE | `tests/python/test_modal_schema_diagnostic.py` | Batch E Python tests |
| `tests/python/test_narration.py` | MOVE | `tests/python/test_narration.py` | Batch E Python tests |
| `tests/python/test_permanent_word_claims.py` | MOVE | `tests/python/test_permanent_word_claims.py` | Batch E Python tests |
| `tests/python/test_profile_background.py` | MOVE | `tests/python/test_profile_background.py` | Batch E Python tests |
| `tests/python/test_promotion_gallery.py` | MOVE | `tests/python/test_promotion_gallery.py` | Batch E Python tests |
| `tests/test_rewrite_title.py` | MOVE | `tests/python/test_rewrite_title.py` | Batch E Python tests |
| `tests/python/test_source_preprocessing.py` | MOVE | `tests/python/test_source_preprocessing.py` | Batch E Python tests |
| `tests/python/test_video.py` | MOVE | `tests/python/test_video.py` | Batch E Python tests |
| `tests/python/test_video_prompt.py` | MOVE | `tests/python/test_video_prompt.py` | Batch E Python tests |
| `tests/python/test_video_smoke_test.py` | MOVE | `tests/python/test_video_smoke_test.py` | Batch E Python tests |
| `tests/udder_sounds.test.js` | MOVE | `tests/frontend/udder_sounds.test.js` | Batch E frontend tests |
| `tests/frontend/video.test.js` | MOVE | `tests/frontend/video.test.js` | Batch E frontend tests |
