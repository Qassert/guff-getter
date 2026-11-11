# Scene-preserving media sanitisation — 2026-11-11

The user confirmed the fax/divorce record in the preceding investigation was the
reported mismatch. Its correct rewrite ID reached media generation; v3 replaced
its entire scene because of the benign anatomy insult `manboob`.

## Implementation

The shared CREATE/BUILD media description is now version media-safe-v4:

1. Normal story-derived description when no modification is needed.
2. Exact benign anatomy labels (manboob/boob, including plural) become `peculiar`.
   Explicit actions are never disguised with token replacements.
3. Recheck sentence/semicolon/newline-bounded clauses with the existing sexual,
   graphic and obfuscation detectors. Omit flagged clauses and retain independent
   safe scene details. No attempt to infer or reconstruct unsafe omitted actions.
4. Use the existing generic safe scene only when no usable safe text remains.

The nominated/displayed text is never changed. The same cached description and
source hash feed main images and video end frames; transition prompts continue
to describe motion between those images. No changes to the race fixes, providers,
paid-call paths, identifiers, front-end controls or existing persisted media.
Version/hash checks rebuild descriptions only when the existing pipeline requests
one; this is not a database migration or a batch rewrite of saved records.

Descriptions persist strategy, rule names and retained/omitted/neutralised counts
alongside their existing concept and source hash. DEBUG logs contain rewrite ID,
categories, strategy, rule names and counts, never story/prompt content. The saved
concept permits inspection of precisely what survived without logging it.

This is a conservative deterministic filter, not a semantic safety classifier.
It may omit a whole sentence containing mixed safe and unsafe detail. Provider
moderation and existing explicit failure handling remain authoritative; there is
no bypass, automatic paid retry, new dependency or extra API call.

## Validation

71 Python tests plus 6 subtests pass (description, mocked image endpoint/retry,
video). Four existing dependency/datetime warnings remain. 26 JS tests pass
(nomination snapshots/races, out-of-order images, delayed video, video controller).
Diff whitespace checks pass. Regressions cover the fax/divorce scene, harmless
absurdity, one flagged element, graphic clause omission, all-unsafe generic
fallback, common image/end-frame concepts, unchanged story data, cache versions,
isolated nominations and diagnostics with no text leakage.

No paid generation or browser media-generation test was performed. No saved
story/media was modified. The pre-existing uncommitted 65px Mad Helper offset is
preserved. Local commit only; no push, merge or deploy.
