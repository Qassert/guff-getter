# NewsMuncher Phase B pilot editorial review

This is an editorial and local-resource review, not authoritative specialist certification. No candidate is production-selectable. Obscure but plausible terminology is retained; uncertain factual, cultural or classification details remain queued for human verification.

## Decision summary

- Accepted: **253**
- Rejected: **23**
- Needs human verification or reclassification: **34**

| Type | Accepted | Rejected | Verify |
|---|---:|---:|---:|
| entity | 120 | 10 | 26 |
| process | 60 | 4 | 4 |
| property | 46 | 2 | 3 |
| relationship | 27 | 7 | 1 |

## Domain decisions

| Domain | Accepted | Rejected | Verify |
|---|---:|---:|---:|
| acoustics | 32 | 0 | 0 |
| aurora-science | 29 | 1 | 4 |
| divination-practices | 22 | 6 | 6 |
| experimental-archaeology | 18 | 4 | 2 |
| glassmaking | 24 | 5 | 2 |
| history-of-surgery | 28 | 0 | 6 |
| industrial-archaeology | 20 | 2 | 2 |
| mycology | 30 | 2 | 2 |
| puppet-theatre | 17 | 2 | 10 |
| topology | 33 | 1 | 0 |

## Effective noun identity capacity

The 156 surviving entity records are not 156 confirmed new hard noun identities. After editorial decisions, **120 entity phrases are accepted** and **26 remain pending**.
Among accepted entities, **76 noun heads are absent from existing resources**. A further **44 accepted compounds share an existing generic head but represent a genuinely different identity. These compounds add phrase-level diversity, while their shared head does not enlarge the single-token anchor pool.
Pending verification could add up to **21 further new noun heads**. Capacity claims should use the confirmed new-head figure, not raw entity count.

The exclusion stemmer also converts `lens` to `len`; this is an existing normalisation quirk, so `acoustic lens` should not be counted as a clean new head until that behaviour is reviewed. No runtime change is proposed here.

## All 54 retained noun-head collisions

| Candidate | Domain | Decision |
|---|---|---|
| clamp connection | mycology | distinct_compound |
| quarter-wave tube | acoustics | distinct_compound |
| organ pipe | acoustics | distinct_compound |
| tuning fork | acoustics | distinct_compound |
| acoustic lens | acoustics | distinct_compound |
| phonograph horn | acoustics | distinct_compound |
| Helmholtz cavity | acoustics | distinct_compound |
| reed pipe | acoustics | distinct_compound |
| anechoic chamber | acoustics | distinct_compound |
| substorm current wedge | aurora-science | distinct_compound |
| field-aligned current | aurora-science | distinct_compound |
| Birkeland current | aurora-science | superficial_alias |
| ring current | aurora-science | distinct_compound |
| polar cap patch | aurora-science | distinct_compound |
| discrete arc | aurora-science | distinct_compound |
| diffuse aurora | aurora-science | distinct_compound |
| proton aurora | aurora-science | distinct_compound |
| black aurora | aurora-science | distinct_compound |
| stable auroral red arc | aurora-science | distinct_compound_verify |
| ion drift | aurora-science | distinct_compound |
| beam engine | industrial-archaeology | distinct_compound |
| Cornish engine | industrial-archaeology | distinct_compound |
| Cornish boiler | industrial-archaeology | distinct_compound |
| Woolf compound engine | industrial-archaeology | distinct_compound |
| Boulton and Watt engine | industrial-archaeology | distinct_compound_verify |
| Cromford Canal | industrial-archaeology | unsuitable_proper_identity |
| inclined plane | industrial-archaeology | distinct_compound |
| stave mill | industrial-archaeology | distinct_compound |
| flax scutching machine | industrial-archaeology | distinct_compound |
| sugar house | industrial-archaeology | distinct_compound |
| pithead bath | industrial-archaeology | distinct_compound_verify |
| Gigli saw | history-of-surgery | distinct_compound |
| carbolic spray | history-of-surgery | distinct_compound |
| Boyle apparatus | history-of-surgery | distinct_compound_verify |
| ether cone | history-of-surgery | distinct_compound |
| simplicial complex | topology | distinct_compound |
| CW complex | topology | distinct_compound |
| quotient space | topology | distinct_compound |
| covering space | topology | distinct_compound |
| homology group | topology | distinct_compound |
| cohomology ring | topology | distinct_compound |
| simplicial set | topology | distinct_compound |
| mapping cylinder | topology | distinct_compound |
| glove puppet | puppet-theatre | distinct_compound |
| rod puppet | puppet-theatre | distinct_compound |
| hand puppet | puppet-theatre | superficial_alias |
| tabletop puppet | puppet-theatre | distinct_compound |
| feeder | glassmaking | overbroad_existing_head |
| stain | glassmaking | overbroad_existing_head |
| experimental hut | experimental-archaeology | distinct_compound |
| sedge mat | experimental-archaeology | distinct_compound |
| bronze axe | experimental-archaeology | distinct_compound |
| charcoal | experimental-archaeology | superficial_existing_identity |
| tanning pit | experimental-archaeology | distinct_compound |

## Rejected or verification-required entries

- **rejected:** `anamorphosis` (mycology) — Nonstandard/misleading name for the fungal anamorph state.
- **rejected:** `teleomorphosis` (mycology) — Nonstandard/misleading name for the fungal teleomorph state.
- **needs_human_verification:** `anamorph-teleomorph transition` (mycology) — Concept is sound; wording should be checked against current mycological usage.
- **needs_human_verification:** `coenocytic hyphae` (mycology) — Genuine term but classified as a relationship; reclassify as property/structure.
- **rejected:** `Birkeland current` (aurora-science) — Genuine historical synonym of field-aligned current; duplicate concept in this set.
- **needs_human_verification:** `stable auroral red arc` (aurora-science) — Genuine SAR arc; verify classification because it is not always treated as ordinary aurora.
- **needs_human_verification:** `Keogram` (aurora-science) — Genuine observational plot; normalise casing to keogram after review.
- **needs_human_verification:** `quasi-trapping` (aurora-science) — Plausible magnetospheric process; specialist source confirmation needed.
- **needs_human_verification:** `optical thickness` (aurora-science) — Valid radiative property but weakly specific to auroral science.
- **needs_human_verification:** `Boulton and Watt engine` (industrial-archaeology) — Genuine historical technology; proper names/provenance need review.
- **rejected:** `Cromford Canal` (industrial-archaeology) — Specific proper location rather than a reusable ingredient identity.
- **needs_human_verification:** `pithead bath` (industrial-archaeology) — Genuine facility, usually expressed as plural pithead baths.
- **rejected:** `underpowered` (industrial-archaeology) — Generic modifier; adds no specialist domain mechanism.
- **needs_human_verification:** `rhabdomancy` (divination-practices) — Plausible historical term; verify exact historical sense.
- **needs_human_verification:** `spodomancy` (divination-practices) — Plausible obscure mantic term; verify authoritative spelling/definition.
- **needs_human_verification:** `anthracomancy` (divination-practices) — Plausible obscure mantic term; verify authoritative spelling/definition.
- **needs_human_verification:** `ceraunomancy` (divination-practices) — Plausible obscure mantic term; verify authoritative spelling/definition.
- **needs_human_verification:** `sciomancy` (divination-practices) — Term is plausible but definitions vary between shadows and spirits.
- **rejected:** `sorting` (divination-practices) — Generic operation, not a distinctive divinatory process.
- **needs_human_verification:** `ominal reading` (divination-practices) — Understandable construction; verify that ominal is useful rather than awkward.
- **rejected:** `jugation` (divination-practices) — Meaning and claimed divinatory usage are unsupported locally and likely misleading.
- **rejected:** `signifier-signified linkage` (divination-practices) — Generic semiotic description rather than domain terminology.
- **rejected:** `intercessory mediation` (divination-practices) — Generic religious relation rather than a distinct divinatory mechanism.
- **rejected:** `cause-and-sign correlation` (divination-practices) — Model-composed generic phrase, not established specialist terminology.
- **rejected:** `analogy mapping` (divination-practices) — Generic cognitive phrase, not a distinct divinatory mechanism.
- **needs_human_verification:** `Liston forceps` (history-of-surgery) — Likely genuine eponym; verify exact instrument and definition.
- **needs_human_verification:** `Sims speculum` (history-of-surgery) — Genuine eponym with ethical/historical sensitivity requiring editorial review.
- **needs_human_verification:** `ecraseur` (history-of-surgery) — Genuine instrument; decide whether to retain French diacritic as écraseur.
- **needs_human_verification:** `Middeldorpf forceps` (history-of-surgery) — Specialist eponym needs authoritative instrument verification.
- **needs_human_verification:** `Boyle apparatus` (history-of-surgery) — Genuine anaesthetic equipment; verify preferred historical name.
- **needs_human_verification:** `plaster of Paris splint` (history-of-surgery) — Plausible historical equipment phrase; verify period terminology.
- **rejected:** `inclusion` (topology) — Too generic alone to function as a distinctive comedy ingredient.
- **needs_human_verification:** `wayang kulit` (puppet-theatre) — Genuine cultural form; specialist/cultural review required.
- **needs_human_verification:** `bunraku` (puppet-theatre) — Genuine cultural form; specialist/cultural review required.
- **needs_human_verification:** `ningyō jōruri` (puppet-theatre) — Genuine cultural form; spelling and relationship to bunraku need review.
- **needs_human_verification:** `karagöz` (puppet-theatre) — Genuine named character; decide whether proper characters suit reusable ingredients.
- **needs_human_verification:** `Hacivat` (puppet-theatre) — Genuine named character; decide whether proper characters suit reusable ingredients.
- **needs_human_verification:** `dalang` (puppet-theatre) — Genuine specialist occupation; cultural review required.
- **needs_human_verification:** `tayū` (puppet-theatre) — Genuine specialist role; spelling and scope require review.
- **needs_human_verification:** `kuroko` (puppet-theatre) — Genuine theatre role; verify precision for puppet theatre specifically.
- **needs_human_verification:** `pupi` (puppet-theatre) — Genuine Sicilian form; confirm singular/plural handling.
- **needs_human_verification:** `kathputli` (puppet-theatre) — Genuine cultural tradition; classification and cultural review required.
- **rejected:** `hand puppet` (puppet-theatre) — Superficial synonym of glove puppet in the same candidate set.
- **rejected:** `miniature` (puppet-theatre) — Generic property with little domain-specific contribution.
- **rejected:** `batch` (glassmaking) — Valid glassmaking sense but overly generic hard noun identity.
- **rejected:** `feeder` (glassmaking) — Valid specialist sense but overly broad head identity for hard exclusion.
- **rejected:** `pontil` (glassmaking) — Variant/synonym of retained punty; does not add a distinct concept.
- **rejected:** `stain` (glassmaking) — Ambiguous generic noun rather than a safely distinct glassmaking identity.
- **needs_human_verification:** `cord-free` (glassmaking) — Industry-style quality term; verify usefulness and exact technical sense.
- **needs_human_verification:** `striation-free` (glassmaking) — Industry-style quality term; verify usefulness and overlap with cord-free.
- **rejected:** `batch-to-gob ratio` (glassmaking) — Plausible description but not established reusable specialist relationship.
- **rejected:** `replica` (experimental-archaeology) — Generic noun rather than a new specialist identity.
- **rejected:** `hearth` (experimental-archaeology) — Generic existing concept; domain context does not create a new identity.
- **needs_human_verification:** `coprolite` (experimental-archaeology) — Genuine archaeological noun but peripheral to experimental archaeology.
- **rejected:** `charcoal` (experimental-archaeology) — Existing generic material identity, not a distinct new concept.
- **needs_human_verification:** `petrographic analysis` (experimental-archaeology) — Genuine archaeological method but primarily archaeometry, not experiment.
- **rejected:** `source-to-product chain` (experimental-archaeology) — Generic model-composed phrase rather than stable specialist terminology.

## Mechanism and usability assessment

Processes add useful mechanisms such as karyogamy, heterodyning, magnetic reconnection, scutching, trephination, compactification, marvering and use-wear analysis. Properties add materially different states such as dikaryotic, saprotrophic, anisotropic, soot-blackened, haemostatic, paracompact and hygroscopic. Relationships are the weakest type: several were generic model-composed phrases and are rejected, while modal coupling, magnetosphere-ionosphere coupling, mycoparasitism, homotopy equivalence, operator–figure linkage and tool-to-use-wear correlation are useful new structures.

Highly technical topology, auroral physics and surgical terms should remain low-frequency ingredients. They work best as occasional collision material; repeated dense clusters would produce awkward prose. Their obscurity alone is not a defect.

## Representative material to preserve

`gleba`, `chlamydospore`, `rhizomorph`, `heterodyning`, `anechoic chamber`, `black aurora`, `substorm current wedge`, `horse gin`, `blast furnace bosch`, `spodomancy`, `ecraseur`, `catling`, `orbifold`, `fundamental groupoid`, `castelet`, `forehearth`, `punty`, `marvering`, and `loomweight`.

## Required next review

Verify the queued historical eponyms, cultural terms, rare mantic terms and disputed scientific wording against authoritative domain sources. Correct type assignments before integration. Re-run duplicate and exclusion-identity checks after those edits; synonyms and proper-name candidates should not be counted as capacity gains.
