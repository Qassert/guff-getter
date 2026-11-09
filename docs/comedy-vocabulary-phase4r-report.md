# NewsMuncher Phase 4R — Thematic Ingredient Prompt Salience

Date: 2026-10-13

## Outcome

Phase 4R adds a presentation-only, default-off experiment for Phase 4P. When
both Phase 4P and Phase 4R are enabled, the same two thematic concepts and one
thematic descriptor selected by Phase 4P are removed from their anonymous
comma-separated banks and presented once in a compact block immediately before
the source text:

```text
Optional thematic sparks:
- [selected concept]
- [selected concept]
- [selected descriptor and its existing grammar tag]
These are creative ingredients, not mandatory content. Freely combine,
distort, ignore or reinterpret them.
```

No ingredient is added, removed, reselected or reranked. Concept and descriptor
counts remain 20 and 10. The core comedy instructions, source handling, memory
systems, copy edit and two-call provider flow are unchanged. The wording keeps
the sparks optional so the model can ignore or transform them.

## Configuration

Phase 4R is off unless explicitly enabled:

```sh
NEWSMUNCHER_THEME_INGREDIENTS=evaluation
NEWSMUNCHER_THEME_SPARKS=evaluation
```

`NEWSMUNCHER_THEME_SPARKS=evaluation` has no effect when Phase 4P is disabled.
Unset the flag or set it to `off` to recover the exact Phase 4P presentation.
It is independent of Phase 4M lexical diversity and Phase 4N thematic guidance.

A local evaluation startup with all compatible experimental features and audit
logging is:

```sh
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation \
NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation \
NEWSMUNCHER_THEME_INGREDIENTS=evaluation \
NEWSMUNCHER_THEME_SPARKS=evaluation \
NEWSMUNCHER_COMEDY_AUDIT_LOG=on \
PYTHONPATH=. .venv/bin/python -B -m uvicorn newsmuncher.main:app \
  --reload --host 127.0.0.1 --port 8000
```

That command is for reviewed live evaluation and uses the normal paid rewrite
path when MUNGE is pressed. No live call was made during Phase 4R implementation.

## Integration details

The new switch is parsed beside the Phase 4P configuration. Spark partitioning
runs only after ordinary concept and descriptor selection and after Phase 4P
has completed its replacements. It performs no sampling, ranking, catalogue
read or memory operation.

With sparks off, all twenty concepts and ten role-tagged descriptors follow the
existing path. With sparks on, eighteen concepts and nine descriptors remain
in their existing banks while the three Phase 4P values appear in the adjacent
block. The combined slate is identical. Descriptor grammar tags are retained.

The optional local JSONL audit now records:

- the existing selected Phase 4P seed, domain and construction provenance;
- whether theme sparks were enabled;
- `ordinary_ingredient_banks` or `adjacent_before_source` placement;
- conservative exact matches in the first-pass title/body;
- conservative exact matches in the final title/body.

These fields are exact string evidence only. They do not claim semantic or
partial uptake. The log remains local, optional and written only after a
successful persisted rewrite.

## Provider-free validation

A 500-generation equivalent-slate check produced three sparks in every
generation and confirmed identical combined ingredient text in all 500 on/off
pairs. Moving the values added a mean net 138 prompt characters, approximately
34.5 input tokens using the repository's character/4 estimate. It added no
selection work and no request.

Automated coverage verifies:

- default-off behavior and no effect without Phase 4P material;
- identical combined ingredients with sparks on and off;
- each thematic ingredient appears once in the rendered prompt;
- the block is adjacent to and before `Text to Transform`;
- preservation of the 20-concept and 10-descriptor totals;
- Phase 4M, Phase 4N and Phase 4P configuration independence;
- one first-pass call and one existing copy-edit call;
- audit placement plus separate first-pass and final exact evidence.

The Phase 4P documentation has also been corrected. The implementation has
nine possible construction IDs: three concept patterns and six descriptor-role
patterns. The original provider-free sample observed seven additional
construction identities; seven observed was not the implemented capacity.

## Proposed live comparison

The smallest useful paired check is three neutral Phase 4K fixture sources,
with one Phase 4P rewrite without sparks and one with sparks for each source:
six finished articles and twelve normal two-pass calls. Use isolated memory
scopes and alternate off/on order. Reuse captured Phase 4P selections in the
paired prompt where practical so prompt placement is the only intended variable.
Provider sampling remains nondeterministic even with identical prompt content.

Enable Phase 4I logging and measure:

- exact Phase 4P uptake in first pass and final;
- recognisable semantic or partial uptake by manual review;
- whether uptake rises above the Phase 4Q result of one item per article;
- whether wording is transformed creatively or inserted mechanically;
- whether copy editing preserves or removes each use.

The recent 36-article Phase 4M run estimated 140,000–165,000 input tokens and
15,000–30,000 output tokens for 72 calls, but the provider wrapper did not
return billable usage or expose local pricing. Scaling that observed workload
to twelve calls gives roughly 23,000–28,000 input tokens and 2,500–5,000 output
tokens. A conservative approval cap is **USD $0.50**. Exact spend cannot be
confirmed from repository data. No paid run should begin without separate
approval.

## Limitations

Provider-free checks prove prompt structure and selection equivalence, not
finished-article uptake or humour. Exact matching misses paraphrases and other
recognisable thematic influence. A six-article live check can identify a large
salience effect or mechanical insertion, but it cannot establish a stable
population rate. Phase 4R does not address whether the model prefers some seed
types or constructions after noticing them.

All work remains uncommitted and unpushed. No provider request or production
database write was made.
