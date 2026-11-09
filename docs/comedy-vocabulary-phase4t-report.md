# NewsMuncher Phase 4T — selective repetition replacement

Date: 2026-10-13

## Outcome

Phase 4T implements the smallest reversible experiment recommended by the
Phase 4S investigation. It is default-off and extends the existing `gpt-6-sol`
copy-edit request only when reliable targets and usable current-slate thematic
alternatives both exist. It does not alter first-pass selection, ingredient
quotas, comedy instructions, media generation, persistence or production
defaults. It adds no provider call.

Enable it with:

```sh
NEWSMUNCHER_REPETITION_REPLACEMENT=evaluation
```

Unset the variable or set it to `off` to retain the original copy-edit request.

## Target selection

The experiment reads the existing bounded, persistent, per-pet Phase 4M
ledger. It can read and update that ledger independently when Phase 4M's
first-pass ranking is disabled, so enabling Phase 4T does not silently turn on
Phase 4M ingredient weighting or guidance.

A target must have confirmed ingredient provenance, occur exactly in the
first-pass article, have a recent exposure score of at least six and be absent
from the source vocabulary. Candidate anchors come from concept bases,
descriptor subjects and raw/thematic ingredient identities. This lets `gravy`
be recognised inside differently worded constructions without treating every
frequent word in model prose as a replaceable noun.

The selector rejects source vocabulary, configured names and places, absent
ingredients, low-exposure terms and an explicit conservative set of narrative
or reporting verbs. Multiword identities require their own identity exposure;
a frequent component word does not create overlapping word and phrase targets.
At most three targets reach the copy editor. If confidence is insufficient,
the normal copy edit runs unchanged.

## Alternatives and prompt contract

At most two current Phase 4P ingredients are offered. They must be absent from
the first pass and compatible by broad ingredient kind, with exact role or bank
matches preferred naturally by the available current slate. Lower lexical
exposure sorts first. No catalogue, substitution dictionary or new selection
path was added.

Phase 4P is therefore the practical dependency for an actionable replacement
plan. Phase 4T still parses and audits independently, but without current Phase
4P alternatives it performs the ordinary copy edit.

The bounded instruction allows no more than two substitutions and permits the
editor to leave every target unchanged. It explicitly preserves narrative
sequence, source-derived events and relationships, sentence density,
ridiculous combinations, profanity, innuendo, surreal intensity, humour and
comic timing. It forbids whole-article rewrites, conventionalisation,
sanitisation, new stories, removed unrelated jokes and additional recurring
motifs. Only the listed alternatives are exempted from the existing rule that
the editor introduce no new vocabulary.

The first-pass call and existing copy-edit call remain the only two provider
calls. The model, timeout, response schema, token limit and failure fallback are
unchanged. A failed second pass still returns the first-pass article.

## Audit diagnostics

Optional Phase 4I JSONL records now include:

- experiment state;
- eligible and rejected targets with exact reasons;
- bounded recent exposure signals;
- source and identity protection decisions;
- offered alternatives;
- exact first-pass and final occurrence counts;
- exact removals and additions;
- newly appearing terms that were already in recent exposure history; and
- copy-edit fallback state.

Disappearance and appearance are reported only as exact string evidence. The
audit does not infer that a semantic replacement succeeded.

## Compatibility and provider-free validation

The feature works with Phase 4M, 4N, 4P and 4R. Phase 4R presentation does not
change the Phase 4P items available after the first pass. Phase 4M may remain
off while Phase 4T reads the same per-pet ledger after ingredient selection,
which preserves Phase 4M default-off selection behavior. The ledger continues
to record only successfully persisted rewrites and retains its existing
per-pet isolation, duplicate protection and bounded window.

Focused tests cover flag parsing, default-off behavior, exact first-pass
eligibility, exposure thresholds, source exemption, proper-name protection,
narrative exclusions, zero-target and zero-alternative paths, three-target and
two-alternative caps, prompt constraints, absurd/profane input, exact audit
evidence, unchanged call count and copy-edit fallback. Existing lexical-memory
tests cover isolation, concurrency, bounded storage and persistence.

Final validation: 44 focused tests passed; the full Python suite passed 517
tests plus 105 subtests; the JavaScript suite passed 84 tests. Python
compilation, production JavaScript syntax and `git diff --check` also passed.
All provider calls were mocked; no production database was used.

## Local manual evaluation

Start NewsMuncher with the compatible Phase 4 experiments and local audit log:

```sh
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation \
NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation \
NEWSMUNCHER_THEME_INGREDIENTS=evaluation \
NEWSMUNCHER_THEME_SPARKS=evaluation \
NEWSMUNCHER_REPETITION_REPLACEMENT=evaluation \
NEWSMUNCHER_COMEDY_AUDIT_LOG=on \
NEWSMUNCHER_COMEDY_AUDIT_PATH=local_audits/comedy_audit_phase4t.jsonl \
PYTHONPATH=. .venv/bin/python -B -m uvicorn newsmuncher.main:app \
  --reload --host 127.0.0.1 --port 8000
```

This command uses the normal paid two-pass path when MUNGE is pressed. It was
documented but not run during implementation.

For a small manual check, use the same source article for five to ten sequential
MUNGEs on one pet so the per-pet history accumulates. In each JSONL record,
compare `first_pass`, `final`, `repetition_replacement.eligible_targets`,
`offered_alternatives`, `exact_target_changes`,
`exact_alternative_additions` and `new_recently_overused_terms`. Review the
complete prose as well as the exact counts: a disappearing target alone is not
evidence of a good substitution. Check specifically that replacements retain
the story's order, density, rude language, innuendo and strange relationships,
and that the editor does not begin mechanically inserting thematic sparks.

## Limitations

- Eligibility is deliberately narrow and provenance-led. Model-invented nouns
  without a matching current ingredient are not automatically targeted.
- Exact matching misses inflections, paraphrases and semantic equivalents.
- Broad kind compatibility cannot guarantee that an alternative fits every
  sentence; the model is therefore allowed to decline it.
- Phase 4P supplies only three thematic ingredients per slate, and all may
  already appear or be unsuitable. In that case Phase 4T does nothing.
- Provider-free tests establish contracts and safety boundaries, not finished
  article quality. A reviewed manual experiment is still required.

No paid provider calls, production writes, commits or pushes were made.
