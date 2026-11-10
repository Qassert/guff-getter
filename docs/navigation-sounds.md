# Randomized navigation button sounds

The original checkout has unrelated unfinished prompt/test/media work. Implementation is
isolated in the clean NewsMuncher-Build worktree on develop; that original work is untouched.

The nine user-supplied WAVs were found under audio/bonkers_button_sounds (underscores, not
spaces), copied byte-for-byte into this worktree, and intentionally included as static app
assets for this requested feature. No sound files were deleted or generated. Approximately
630KB total, mono 44.1kHz PCM, 0.70–0.90 seconds each.

The existing shared mode-nav controller caches/preloads the three assigned sounds for each
CREATE/BUILD/GALLERY button. Selection uniformly excludes the last sound for that button;
per-tab sessionStorage preserves the exclusion across navigation, with an in-memory fallback
when storage is blocked. Each new navigation sound stops and rewinds the previous one.
Native Audio playback retains the existing master-audio mute authority. URL construction
uses URL resolution relative to the script, preserving static prefixes and escaping spaces.

Old squelches and hover shouts are removed only from these three buttons. Gallery's separate
hover-voice infrastructure and all old audio files remain available to other controls.
Current-page spans also play their assigned sounds without navigating. Modified clicks retain
native behavior. Existing draft-save flush, save-failure blocking, navigation timing (170ms or
0ms for reduced motion), visual effects and destinations are unchanged. As before, full-page
navigation can end a playing sound; navigation is not delayed for the length of the WAV.

Validation:
- node --test tests/*.test.js tests/frontend/*.test.js: 230 pass, including nine new tests.
- Python BUILD page, adoption access, Gallery text edit and promotion Gallery: 73 pass,
  six existing dependency/datetime warnings; mocked database/provider services.
- node --check shared/mode-nav.js and git diff --check pass.
- Python wave parser validates every WAV; copied bytes match all nine original files.
- Installed headless Chrome local fixture used actual mode-nav/master-audio scripts and HTTP
  static asset serving. All nine reached readyState 4 with finite durations and no errors.
  All three buttons played advancing audio, excluded consecutive repeats, kept at most one
  navigation sound playing across rapid clicks, and obeyed master mute.
- Browser fixture was disposable, without authenticated app or paid generation calls. Fixtures
  and logs are ignored under tmp/. No production access, push, merge or deployment.
