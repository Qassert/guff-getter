# Free Content API Evaluation for NewsMuncher

Research performed on **2 November 2026**. This is a research snapshot, not legal advice. Live requests were made without registering an account or supplying a private API key. Wikipedia was excluded.

## Summary

**OpenAlex is the strongest first integration.** It returned substantial abstracts without authentication, supports precise filtering, has generous anonymous limits, and describes all OpenAlex data as CC0. Its scientific language is especially fertile for surreal substitutions, although a production importer should still retain source links and distinguish OpenAlex metadata from linked publishers' copies.

**NASA Image and Video Library is the strongest second source.** Its technical captions often contain people, equipment, actions and outcomes, and the API worked without a key. NASA content is generally reusable for informational purposes with acknowledgement and without implying endorsement, but third-party material, logos and identifiable people require care. NASA's current media guidance also has specific rules for AI-derived products.

**arXiv is the best conditional third source.** Abstracts are consistently rich, but article licences vary. arXiv permits transformation and sharing of descriptive metadata under CC0; redistribution or adaptation of an e-print requires the individual work's licence or permission. Integration should admit only records with a licence that permits adaptation and the intended commercial status.

Hacker News produced lively human narratives, but the official API offers no content-reuse licence and comments may contain personal information. UK PlanIt is operationally attractive and inherently British, but the sampled descriptions averaged only 39 words and the site's copyright notice places strict limits on linked application documents. The Guardian requires registration and its free developer tier is non-commercial; its commercial terms explicitly include generative-AI-derived uses, so it is not a free fit for this project.

## Live test results

| Source | Live result | Saved records | Words per record (min / mean / max) | Authentication | Stated limit | Overall fit |
|---|---:|---:|---:|---|---|---:|
| OpenAlex | HTTP success | 10 | 106 / 257 / 834 | None for basic use | 10 requests/s without a key; max 100 records/request | **5/5** |
| arXiv | HTTP success | 10 | 157 / 198 / 284 | None | One request per 3 seconds, one connection | **4/5 with licence filter** |
| Hacker News | HTTP success | 8 | 100 / 131 / 233 | None | Official docs currently state no rate limit | **3/5** |
| UK PlanIt | HTTP success | 10 | 24 / 39 / 49 | None | Rate-limited; 5,000 records and 1,000 kB max/request | **3/5 as a secondary ingredient** |
| NASA Images | HTTP success | 10 | 100 / 122 / 152 | None | No numeric rate limit published in the API reference | **4.5/5** |
| Guardian | **HTTP 401** | 0 | — | API key required | Developer: 1 request/s, 500/day | **1/5 for free deployment** |

The sample selection was deliberately spread through larger result sets or across authorities rather than copying each API's first ten results. Exact request URLs and selection notes are stored with the sample data. Response-time observations were qualitative rather than benchmarked: OpenAlex, Hacker News, NASA and the Guardian rejection were responsive; PlanIt authority queries completed within the 20-second guard; arXiv was the slowest source and should be polled conservatively.

## Comparison for NewsMuncher

Scores are 1 (poor) to 5 (excellent).

| Source | Descriptive richness | Comedy potential | Variety | Integration | Free sustainability | Reuse confidence | Narrative content |
|---|---:|---:|---:|---:|---:|---:|---:|
| OpenAlex | 5 | 5 | 5 | 5 | 5 | 5 for API data | 3 |
| NASA Images | 4 | 5 | 4 | 5 | 5 | 4 | 4 |
| arXiv | 5 | 5 | 5 | 4 | 5 | 2–5 by work | 3 |
| Hacker News | 4 | 4 | 5 | 3 | 5 | 1 | 5 |
| UK PlanIt | 2 | 5 | 4 | 4 | 4 | 2 | 2 |
| Guardian | 5 | 4 | 5 | 3 | 1 | 1 | 5 |

## 1. OpenAlex

### Access and operation

- Official API: <https://api.openalex.org>; [API reference](https://help.openalex.org/api/).
- Basic use is free without a key. Anonymous clients are limited to 10 requests/second. A free registered key increases the rate and budget, but is unnecessary for a small proof of concept.
- The test requested a random sample of 50 works having abstracts and retained 10 substantial, spread selections. Abstract prose was reconstructed from `abstract_inverted_index`.
- OpenAlex cautions that text is sourced externally and should be treated as untrusted input; escape it before rendering.

### Rights

OpenAlex states that all data returned by its API are [CC0](https://help.openalex.org/api/). A work's `locations` may separately identify the licence of the linked publication. This makes OpenAlex metadata and abstracts the clearest reuse case in the study, while linked PDFs and publisher pages must not be treated as CC0 merely because OpenAlex points to them.

### Suitability

Strengths are volume, random sampling, rich abstracts, broad disciplines and easy filtering. Weaknesses are scientific density, occasional non-English records, stale or low-quality metadata, and abstracts that describe findings more than sequential human events. Filter for English, abstract length, work type and concepts, then favour abstracts containing active verbs, concrete equipment, organisms, places or procedures.

### Real examples

- [Matrix-binding proteins of *Staphylococcus aureus*](https://doi.org/10.1099/00221287-145-9-2497) — **279 words**. Molecular actors and hybrid molecules provide concrete transformations.
- [Evaluation of subsetting programming language elements](https://doi.org/10.1145/971300.971392) — **210 words**. People, rules, tools and failure modes form a usable narrative skeleton.
- [Loss and improvement analysis applied to the wine industry](https://openalex.org/W7120869602) — **169 words**. Familiar physical processes collide with managerial terminology.

## 2. arXiv

### Access and operation

- Official endpoint: `https://export.arxiv.org/api/query`; [API guide](https://info.arxiv.org/help/api/basics.html).
- No key is required. The [API terms](https://info.arxiv.org/help/api/tou.html) require no more than one request every three seconds and one connection at a time.
- A 30-result window starting at result 137 was requested; every third result supplied the 10 saved samples. All sampled abstracts exceeded 150 words.
- Responses are Atom XML. Production code must normalise TeX, Unicode and category identifiers.

### Rights

arXiv says descriptive metadata may be retrieved, transformed and shared under CC0. E-prints remain copyrighted and most use arXiv's non-exclusive distribution licence; others use one of several Creative Commons licences. The [licence guidance](https://info.arxiv.org/help/license/index.html) confirms that licences are selected per submission and may differ between versions. A public comedy derivative should therefore use only records with a compatible licence (for example CC BY or CC0), preserve attribution, and reject no-derivatives or incompatible non-commercial records as appropriate.

Whether the abstract is safely treated solely as CC0 metadata should be confirmed before production; the conservative implementation is to require an adaptation-compatible article licence.

### Suitability

The abstracts are reliably long and structurally coherent, and technical language is excellent raw comedy material. Many are written in impersonal research style, contain heavy notation, or lack recognisable everyday actors. Filters should prefer applied experiments, fieldwork, instruments and failures; strip TeX safely; and reject abstracts dominated by equations.

### Real examples

- [Inflight GPU reconstruction for ALICE Run 3](http://arxiv.org/abs/2608.11819v1) — **208 words**. Hardware, distributed work and reconstruction tasks provide active mechanisms.
- [IceCube Upgrade probing Earth's interior](http://arxiv.org/abs/2608.06543v1) — **157 words**. A detector, a planet and atmospheric particles create vivid scale.
- [Moon and Sun shadows observed with cosmic rays](http://arxiv.org/abs/2608.04658v1) — **170 words**. Visually intelligible celestial objects and unusual measurement actions.

## 3. Hacker News

### Access and operation

- Official [Firebase API documentation](https://github.com/HackerNews/API).
- No key is required, and the documentation says there is currently no rate limit.
- The API exposes stories and comments as individual items, so useful prose requires many small requests and traversal of comment trees.
- The test sampled every fifth item from part of `beststories`, inspected each story and up to four leading comments, and retained eight records of at least 100 words.

### Rights and privacy

The API documentation's MIT licence covers the API documentation/code, not user submissions. It gives no general licence to republish or transform comments. Authors may edit, delete or request removal, and text can contain personal claims or identifying information. This is a significant publication and moderation risk. If pursued, store IDs rather than permanent text, re-fetch before use, omit usernames from generated work, exclude sensitive/personal narratives, link and attribute, and obtain legal advice or author permission for republication.

### Suitability

HN has the best conversational narratives in the tested set: people explain decisions, tools, mishaps and consequences. It is also noisy, subjective and frequently about software abstractions. Long Ask HN text submissions are stronger than arbitrary comments. Technical integration is easy at low volume but inefficient for bulk discovery because the official API has no full-text search.

### Real examples

- [Ask HN: Which TV do you recommend for privacy?](https://news.ycombinator.com/item?id=50328896) — **103 words**. A concrete domestic object, constraints and social concerns.
- [Comment 50326361](https://news.ycombinator.com/item?id=50326361) — **233 words**. The longest sampled human account, with actions and reasoning.
- [Comment 50327005](https://news.ycombinator.com/item?id=50327005) — **133 words**. A compact first-person explanation with sequential ideas.

## 4. UK PlanIt

### Access and operation

- Official [API documentation](https://www.planit.org.uk/api/); no key is required.
- Five authority queries were made (Hackney, Wiltshire, Cornwall, Leeds and Edinburgh), and the two longest descriptions from each result set were retained.
- The API documents a 5,000-record and 1,000-kB ceiling per request. It is rate-limited without publishing a numeric allowance; repeated excess produces HTTP 429.
- More than 30 authorities were described by PlanIt as not currently up to date, so freshness must be checked per authority.

### Rights

PlanIt aggregates local-authority material and lists mixed source licences in its [acknowledgements](https://www.planit.org.uk/acknowledgements/). Its warning for linked plans, drawings and submitted documents permits limited consultation uses and says further copying needs permission. The page does not state a simple blanket licence for every application description. Do not ingest documents or assume all description text is Open Government Licence content without confirming provenance and terms with PlanIt/local authorities.

### Suitability

Planning language is exceptionally British and rich in concrete objects: dormers, flues, outbuildings, shopfronts, illuminated signs and retrospective permissions. However, all 10 sampled descriptions were below 50 words and usually describe one proposed action rather than a story. PlanIt is better as a premise/object feed or paired with another source than as a standalone article source.

### Real examples

- [5 Clarendon Court, Marlborough](https://www.planit.org.uk/planapplic/Wiltshire/PL/2024/08681/) — **49 words**. Multiple alterations and architectural objects.
- [29A–31 Frederick Street, Edinburgh](https://www.planit.org.uk/planapplic/Edinburgh/24/05219/LBC/) — **46 words**. Listed-building detail and a concrete sequence of changes.
- [Strathavon Farmhouse, Great Durnford](https://www.planit.org.uk/planapplic/Wiltshire/PL/2024/04109/) — **46 words**. Rural location, structures and proposed work.

## 5. NASA Image and Video Library

### Access and operation

- Official root: `https://images-api.nasa.gov`; [API specification](https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf).
- No key was required. The API provides search, asset, metadata, captions and album endpoints. The reference does not publish a numeric rate limit.
- A 100-result search for experiments was made. Ten descriptions of at least 100 words were selected across the eligible result list.
- Captions are uneven: some are merely photo credits, while experiment and mission descriptions contain clear people, equipment, action and purpose.

### Rights

NASA's [media usage guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/) says NASA content generally is not subject to US copyright and may be used for educational or informational purposes, with NASA acknowledged and no implied endorsement. It flags third-party copyrighted material, logos, commercial use, and identifiable people's publicity/privacy rights. Current guidance also sets conditions for AI-derived products: disclose the generated nature, do not imply NASA permission or accuracy, and attribute generated outputs to the product rather than presenting them as NASA statements. Each record therefore needs provenance screening.

### Suitability

NASA combines technical specificity with physical stakes and strong visuals. It is more narratively useful than generic scholarly abstracts when captions describe an experiment being installed, operated or recovered. Search terms such as `experiment`, `test`, `crew`, `repair`, `prototype` and `deployment` should be rotated, while duplicate photo captions and credit-only records should be removed.

### Real examples

- [Inflatable Antenna Experiment](https://images.nasa.gov/details/s77e5022) — **127 words**. A physical deployment sequence with obvious comic scale.
- [The Polar Night Nitric Oxide Experiment](https://images.nasa.gov/details/GSFC_20171208_Archive_e000135) — **150 words**. Strange scientific nouns attached to an understandable mission.
- [CFE-2 Experiment Run](https://images.nasa.gov/details/iss038e000264) — **127 words**. Equipment, operators and an experimental action.

## 6. The Guardian Open Platform

### Live result

The documented `api-key=test` request returned **HTTP 401 Unauthorized** with no content. No Guardian article text was stored. The [current documentation](https://open-platform.theguardian.com/documentation/) says every request needs a key.

### Access and rights

The [access page](https://open-platform.theguardian.com/access/) offers a free developer key for non-commercial use at one request per second and 500 requests per day. Registration is required, so none was created for this task. The same page places commercial uses—including generative-AI services and products derived from Guardian content—under a paid commercial arrangement. This makes the source unsuitable for the requested free, accountless experiment and potentially unsuitable for NewsMuncher without a negotiated licence.

## Sampling and limitations

- Samples contain source descriptions/abstracts required for evaluation, not full linked papers or articles.
- OpenAlex's random sample is inherently non-repeatable. The saved IDs make this evaluation auditable.
- arXiv was sampled from one deliberately offset result window, not a statistically representative cross-category study.
- HN's best-story feed changes continuously and the sample overrepresents prominent discussions.
- PlanIt sampling covered five authorities and one historical year; authority completeness varies.
- NASA was queried using `experiment`, which intentionally favours procedural captions.
- Licensing conclusions are conservative operational guidance and should be reviewed before public deployment.

## Saved evidence

The `samples/` directory contains compact JSON records with retrieval time, request URLs, source IDs, links, descriptive text, word counts and relevant metadata:

- `openalex.json` — 10 records
- `arxiv.json` — 10 records
- `hacker-news.json` — 8 records
- `uk-planit.json` — 10 records
- `nasa-images.json` — 10 records
- `guardian-attempt.json` — the failed unauthorised request, with no article content

