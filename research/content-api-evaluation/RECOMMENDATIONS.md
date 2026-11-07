# Recommended Content APIs

## Recommended order

### 1. OpenAlex

Use OpenAlex for the first proof of concept. It is the only candidate combining substantial prose, anonymous access, broad variety, precise filters and a clear CC0 statement for API data.

Suggested filter pipeline:

1. Require an abstract and a language confidently identified as English.
2. Prefer 120–350 words; reject extremely short and unusually long records.
3. Prefer applied research, experiments, case reports, field studies, tools, organisms and physical processes.
4. Score up concrete nouns and active verbs; score down equations, citation-heavy fragments and purely theoretical notation.
5. Deduplicate by OpenAlex ID, DOI and normalised title.
6. Retain title, OpenAlex ID, DOI, source link, retrieval date and any location licence metadata.
7. Escape all source text before displaying it.

Comedy potential is highest where formal language describes recognisable physical behaviour: machines being tested, organisms responding, people following protocols, or systems failing under peculiar conditions.

### 2. NASA Image and Video Library

Use NASA as the second feed, initially limited to records whose metadata clearly identifies NASA as the source and whose description contains at least 100 words.

Suggested filter pipeline:

1. Rotate searches across `experiment`, `test`, `crew`, `repair`, `prototype`, `deployment`, `habitat` and `training`.
2. Prefer descriptions with two or more actions and at least two concrete entities.
3. Reject credit-only captions, repeated photo-set captions and descriptions dominated by names.
4. Deduplicate near-identical descriptions across a photo series.
5. Flag third-party credits, JPL material, logos and identifiable people for stricter handling.
6. Preserve source acknowledgement and link; label the resulting article clearly as AI-generated comedy and avoid implying NASA endorsement or factual authorship.

NASA descriptions offer stronger visual and event structure than most scholarly abstracts, which should help NewsMuncher preserve a coherent sequence while transforming the vocabulary.

### 3. arXiv, behind a licence gate

Add arXiv only after implementing per-record licence checks. Treat an absent licence or the default arXiv distribution licence as ineligible for public derivative comedy until legal review confirms otherwise.

Suggested filter pipeline:

1. Admit only adaptation-compatible licences for the intended use, initially CC0 and CC BY; handle share-alike and non-commercial licences only if the product can comply.
2. Keep the required three-second delay and a single request connection.
3. Prefer applied categories and abstracts describing experiments, instruments, observed behaviour or fieldwork.
4. Reject abstracts with a high ratio of TeX, symbols, citations or undefined acronyms.
5. Normalise display text without changing scientific meaning; retain author, arXiv ID, version and licence for attribution.

arXiv should complement rather than duplicate OpenAlex. OpenAlex is better for discovery and anonymous scale; arXiv is useful when its own record exposes a suitable licence and a clean abstract.

## Sources not recommended as primary feeds

### UK PlanIt

PlanIt is worth a later, narrow experiment as a British object/premise ingredient source. The sampled descriptions were vivid but averaged only 39 words, too little for a self-contained article skeleton. Before publication use, clarify the reuse status of application descriptions with PlanIt or the originating authorities. Do not ingest linked plans or documents.

### Hacker News

Do not make HN a public production source without a rights/privacy policy. The API is free and the prose is narratively strong, but no user-content reuse licence is stated. A safer future experiment would use author-opted-in text, public-domain submissions, or transient local evaluation with IDs and links rather than retaining comments.

### The Guardian

Do not integrate it under the “free content” objective. It requires registration, the free tier is non-commercial, and the access page places generative-AI-derived commercial use in the paid tier. Reconsider only if the project obtains an appropriate written licence.

## Minimal proof-of-concept design

Keep ingestion separate from the existing MUNGE engines until source quality is measured:

1. Fetch a bounded set of OpenAlex and NASA candidates on demand or into a short-lived cache.
2. Apply source-specific licence/provenance checks before comedy-quality filtering.
3. Score narrative fitness using local rules: word length, active verbs, entity variety, concrete nouns and a low equation/symbol ratio.
4. Present title, excerpt, source and licence/provenance to the user before selection.
5. Store only the selected source ID and necessary text, with an attribution record.
6. Track rejection reasons and source yield so later integration is driven by evidence rather than volume.

Recommended initial mix: **60% OpenAlex, 40% NASA**. Add arXiv only for compatible licences and use PlanIt as an occasional British premise supplement rather than a full source article.
