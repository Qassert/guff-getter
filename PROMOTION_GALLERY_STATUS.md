# Promotion Gallery handover

STATUS: REVIEW / CODEX
BRANCH: feature/promotion-gallery
BASE: 903f5d1 (feature/global-word-shuffle)

All six implementation milestones are complete and pushed. No deployment performed.

## Checkpoints

1. `126f185` — discovery/design and recoverable milestone plan.
2. `c32976f` — private access, data/API, stored-asset retrieval, backend tests.
3. `8e56d11` — one-item page, navigation, text/images and promotion UI.
4. `53a7b25` — cancellable audio lifecycle and autoplay fallback.
5. `6e5e5d0` — parchment page turns, responsive/reduced-motion/fallback states.
6. Final checkpoint: `Complete Promotion Gallery regression and handover`.

## Entry points and storage

Creation page links to `/promotion-gallery/`; authenticated viewers can return to
`/pets/pet_profile/{their-pet}`. Successful existing login/adoption now also issues
an opaque HttpOnly, SameSite=Strict gallery session (Secure on HTTPS). Existing users
must sign in once again. Hashed tokens in pet_adoption_db.gallery_sessions expire
in 24 hours. Sessions check pet adoption and password version on each gallery request.
Only gallery routes use this new authentication boundary; this is not an app-wide
authentication rewrite. Older entries/media endpoints retain their existing access rules.

All nominated entries across pets appear, including promoted ones. Explicit
nominated=False is excluded. Legacy missing nominated follows the existing
moderation compatibility rule: crazyReplacement1done=True means nominated.
Stable entries._id remains the identity. No creation/media copies or backfill.
New fields, written lazily on the existing nomination:

- promoted: true, plus promoted_at UTC datetime (first promotion only).
- promotion_gallery_seen_count: nonnegative integer; missing/invalid means zero.

Existing gallery_status is preserved and is separate from promoted. There is no
unpromote, public Gallery, social feature, editing or generation interface.

## Rotation and acknowledgements

GET /promotion-gallery/next selects randomly among the minimum seen-count entries.
The previous item is excluded when another equal-minimum candidate exists. Selection
alone does not increment. After visible DOM rendering, JS sends POST /displayed.
A short-lived promotion_gallery_views receipt and the entry count commit in one
Mongo transaction; duplicate ACKs do not count twice. Receipts expire in 10 minutes.
Next selection waits for the prior ACK. Expired/deleted receipts allow recovery on
another NEXT attempt; network failures retain the receipt for safe retry.

Counts persist across visits and are shared across viewers. New nominations start
at zero. Concurrent viewers can select the same item before either ACKs, but each
actual acknowledged display counts independently. This is lowest-count fairness,
not a strict permutation/queue reservation across simultaneous browser sessions.
Mongo transactions are required, as already required by permanent word claims.
TTL indexes are created lazily on runtime session/receipt collections; no destructive
migration or live DB action was performed during development.

## Existing media only

Gallery service imports no generation services. Image: canonical stored UUID PNG.
Narration: existing nomination-ID MP3 with matching narration entry_id metadata.
Jingle: existing nomination-ID MP3 with Mongo URL or read-only SQLite sidecar proof.
Gallery media routes authenticate access and serve those same files, with range
support for audio. Missing, empty, symlinked, unsafe or unsupported legacy/external
references fall back to text. No remote image proxy/fetch or asset regeneration.

JS uses separate audio objects per active page. Both play calls are made in the same
event turn. NEXT/pagehide immediately pause/unload old audio and invalidate late
callbacks. Autoplay failure offers PLAY AUDIO; STOP cancels even pending starts.
No attempt to bypass browser autoplay policy. Exact sample-synchronization is not
promised; network buffering and browser policy still apply.

## Validation

125 Python tests passed + 6 subtests:

```sh
./.venv/bin/python -m pytest tests/test_promotion_gallery.py tests/test_dating_source.py tests/test_draft_lifecycle.py tests/test_image_generation.py tests/test_narration.py tests/test_jingles.py tests/test_jingle_frontend.py tests/test_profile_background.py tests/test_copy_edit_pass.py tests/test_permanent_word_claims.py tests/test_source_preprocessing.py -q
```

15 Node tests passed:

```sh
node --test tests/promotion_gallery.test.js tests/profile_editing.test.js tests/image_flow.test.js tests/image_background.test.js tests/narration.test.js tests/jingles.test.js
```

Only existing dependency/datetime deprecation warnings. Diff reviewed; whitespace
checks passed. Mongo/providers mocked and test media temporary. No live generation,
Mongo migration, reset, deployment, or main modification.

Browser visual/audio checks remain manual: browser connection unavailable and native
Computer Use permissions denied. The loopback fixture server was stopped. Antigravity
was not used for review: only `agy --help` inspected; no convenient enforced read-only
mode found. No agent was permitted to edit the working tree.

## Next review action

Start the app normally, sign in again, then open PROMOTION GALLERY. Check a text-only
nomination and stored-media nomination; turn rapidly during audio; verify STOP/PLAY,
PROMOTE, reload persistence, keyboard access, narrow layout and reduced-motion mode.
This requires retrieval and review-state writes only, no generation. Do not deploy
or merge main without separate authorization.
