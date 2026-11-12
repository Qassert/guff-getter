# Global Mad Helper face toggle — 2026-11-12

The existing toggle now appears 10px left of global mute, sharing its 48px round
shell, 14px top alignment, border, background, shadow and shared glow. A new empty
base-template block places opt-in controls at body level beside mute, outside the
page/parchment layout. CREATE, BUILD and signed-in Gallery override that block;
signed-out Gallery and unrelated pages retain their existing opt-in behaviour.

The original idle.png is reused without generating/editing any asset. CSS crops
and scales it to the face inside the circular viewport. The same native checkbox,
data-assets/data-sounds attributes, saved preference and change handler remain in
use. A CSS unchecked-state red slash indicates disabled without replacing the
face. Its accessible name is Mad Helper; native keyboard toggling/checked state,
focus ring and disabled-asset behaviour are retained. No helper JavaScript changed.

31 existing helper/audio/glow JS tests pass. Four Jinja rendering checks confirm
exactly one named helper toggle beside mute before main content on CREATE, BUILD
and signed-in Gallery, and none on signed-out Gallery. Diff checks pass. PNG
inspection guided the face crop; live browser visual checks were not performed.
No paid calls, media generation, app-server commands, push, merge or deployment.
The prior uncommitted 65px upper-helper positioning edit remains untouched.

Changed: templates/base.html, partials/mad-helper-toggle.html, pet_profile.html,
build.html, promotion_gallery.html; static/css/creation/mad-helper.css;
CURRENT_WORK.md and this report. Helper stylesheet cache versions are advanced.
