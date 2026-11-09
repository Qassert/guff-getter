# NewsMuncher Phase 4U — smarter repetition replacement

Date: 2026-10-13

## Outcome

Phase 4U refines the default-off Phase 4T experiment without changing Phase 4T
when the new flag is disabled. It keeps the first-pass generator, existing
`gpt-6-sol` copy editor, two-call provider flow, failure fallback, per-pet
memory, source protection and comedy direction.

Enable Phase 4U with both switches:

```sh
NEWSMUNCHER_REPETITION_REPLACEMENT=evaluation
NEWSMUNCHER_PHRASE_REPLACEMENT=evaluation
```

The Phase 4T flag enables the replacement integration. The Phase 4U flag
selects the new phrase-aware strategy. With Phase 4U off, the Phase 4T selector
and instruction remain unchanged.

## Phrase-aware targeting

Phase 4U uses only identities already supplied by selected ingredient
provenance: concept bases, descriptor subjects and raw/thematic base identities.
It does not infer noun phrases from arbitrary surrounding prose.

Each base or subject is treated atomically. Recent exposure may come from its
identity key or any exposed component word, but qualifying exposure promotes
the complete provenance-backed identity. Thus repeated `press` exposure can
select `trouser press`; it cannot create separate `trouser` and `press`
replacement opportunities.

Targets still require an exact first-pass occurrence, recent exposure of at
least six, source absence and protection from selected names and locations.
Narrative and reporting verbs remain excluded. Selection is deterministic:
higher exposure wins, then longer identities, then lexical order. Targets that
share a meaningful component are collapsed into one opportunity. The audit
records the excluded components and their chosen parent phrase.

The implementation deliberately selects the confirmed `licensing authority`
base rather than guessing the longer `municipal licensing authority` from
nearby prose. This is slightly narrower than the illustrative phrase in the
task, but it follows the stronger requirement to avoid unreliable grammatical
guessing.

## Compatible alternatives

Phase 4T supplied complete Phase 4P constructions such as `megaphone in
counterweight balance with byzantine`. Phase 4U instead offers the same selected
ingredient's provenance-backed base or subject, such as `megaphone`. The audit
retains the full source construction, domain IDs, seed kinds and construction
ID.

Alternatives must be absent from the first pass, contain one to four meaningful
words and match the broad ingredient kind. Exact target-bank or grammatical-role
matches sort first, followed by lower recent exposure, closer phrase length and
lexical order. At most two are offered.

If current Phase 4P ingredients exist but none has a compatible insertable
base/subject, the plan explicitly records an inventive fallback and supplies at
most four current domain IDs. The copy editor may then invent one fresh,
grammatically compatible and equally absurd replacement. This fallback is
auditable and does not add a catalogue, selection path or provider call.

## Copy-editor instruction

When Phase 4U has eligible targets, the evaluation-only instruction now asks
the editor to make one or two substitutions where safe, with a hard maximum of
two. It prioritises the highest-confidence repeated phrases, prefers compatible
supplied alternatives, permits the explicit domain-guided fallback only when
needed and allows unchanged text when an edit would damage grammar, continuity
or the joke.

It directs the editor to change only the phrase and local agreement while
preserving the surrounding sentence, source-derived sequence, events,
relationships, dense surreal combinations, outrageous British humour,
profanity, innuendo, joke density and comic timing. It forbids changed names,
protected source details, simplification, sanitisation, rationalisation,
whole-story rewrites and new recurring motifs.

## Offline replay of the three Phase 4T articles

The local Phase 4T audit retained complete first-pass text, ingredient
provenance, the selected Phase 4T targets and bounded exposure snapshots. The
snapshot stores only the top 80 penalty keys, so replay supplemented missing
component scores with the exact target scores already recorded by Phase 4T.
No model or database was invoked.

| Article | Phase 4T targets | Phase 4U targets | Overlap removed | Phase 4U alternatives |
|---|---|---|---|---|
| Cecil Wattleford-Ditheridge | rescue; press; jelly | rescue wheelbarrow; sandwich press; jelly mould | rescue; press; jelly | cucumber slicer (0); certificate (0) |
| Pat Poppycock | licensing authority; authority; licensing | licensing authority | licensing; authority | backup cardigan (0); pony (0) |
| Wilf Wagglestead | press; gravy; trouser | trouser press; gravy boat | press; trouser; gravy | megaphone (0); standards board (56) |

All Phase 4U targets are exact provenance-backed identities present in the
first pass. Phase 4T created nine replacement opportunities, including five
nested component duplicates. Phase 4U creates six non-overlapping phrase
opportunities. The replay's first low-exposure alternative is zero in every
article. Phase 4T's full alternatives ranged from 0 to 64 and were substantially
longer than the targets.

Prompt clarity also changes from “you may make at most two” isolated-word edits
to an explicit request for one or two safe local phrase substitutions, while
retaining permission to decline a damaging edit.

This replay establishes materially cleaner inputs to the copy editor. It does
not establish improved finished articles or humour; that requires a later
manual provider run.

## Audit diagnostics

Local Phase 4I records now distinguish:

- Phase 4T and Phase 4U switch state;
- complete selected phrases, ingredient phrase, provenance and semantic theme;
- component and nested candidates excluded through overlap;
- exact protected-source/name/location rejection reasons;
- short alternative text plus its full Phase 4P source construction, role,
  domains, seed kinds, construction, exposure and length distance;
- exact first-pass and final target counts;
- exact supplied-alternative appearances;
- new already-exposed terms introduced in the final text;
- targets removed without any supplied alternative appearing;
- inventive fallback state and domain cues; and
- copy-edit failure fallback state.

The diagnostics remain bounded and local. Exact disappearance is never labelled
as a successful semantic substitution.

## Provider-free validation

Focused coverage includes the three observed regressions, longest reliable
phrase selection, nested and duplicate suppression, repeated occurrences,
case and punctuation boundaries, thresholds, source/name/location protection,
role compatibility, low-exposure ordering, caps, fallback diagnostics, flag
independence, prompt preservation, unchanged call count and copy-edit fallback.

Focused validation passed 50 tests. The full Python suite passed 523 tests plus
105 subtests, and the JavaScript suite passed 84 tests. Python compilation,
production JavaScript syntax and `git diff --check` passed. No paid provider
call or production database write occurred.

## Manual evaluation command

```sh
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation \
NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation \
NEWSMUNCHER_THEME_INGREDIENTS=evaluation \
NEWSMUNCHER_THEME_SPARKS=evaluation \
NEWSMUNCHER_REPETITION_REPLACEMENT=evaluation \
NEWSMUNCHER_PHRASE_REPLACEMENT=evaluation \
NEWSMUNCHER_COMEDY_AUDIT_LOG=on \
NEWSMUNCHER_COMEDY_AUDIT_PATH=local_audits/comedy_audit_phase4u.jsonl \
PYTHONPATH=. .venv/bin/python -B -m uvicorn newsmuncher.main:app \
  --reload --host 127.0.0.1 --port 8000
```

This command uses the normal paid two-pass path when MUNGE is pressed. It was
not executed during Phase 4U implementation.

For a minimal manual comparison, reuse the same source and pet for three Phase
4T-only MUNGEs and three Phase 4U MUNGEs. In the Phase 4U JSONL, inspect
`first_pass`, `final`, `eligible_targets`, `overlap_exclusions`,
`offered_alternatives`, `exact_target_changes`,
`exact_alternative_additions`, `targets_removed_without_supplied_alternative`,
`new_recently_overused_terms` and `copy_edit_fell_back`. Read the full articles
to check that local replacements preserve the surrounding madness and do not
turn current thematic domains into a new repeated motif.

## Limitations

- Component exposure is evidence that the complete current ingredient identity
  belongs to a repeated lexical family; it does not prove that exact phrase was
  previously printed.
- Strict provenance skips model-invented phrases that cannot be tied safely to
  an offered base or subject.
- Broad role compatibility cannot prove a replacement works in a particular
  sentence. The editor can decline it.
- The inventive fallback is intentionally limited but necessarily less
  auditable than selecting an exact supplied alternative.
- Offline replay measures selector and prompt inputs only. It cannot demonstrate
  uptake, comedy quality or absence of narrative drift.

No commit or push was made.
