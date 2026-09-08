"""Local source masking. Literal metadata is for diagnostics, never prompt content."""
import logging
import re
from collections import Counter
from functools import lru_cache

logger = logging.getLogger(__name__)
STRUCTURAL = frozenset('not no never neither nor hardly rarely scarcely only also then now later earlier before after already still again yet here there when where why how because therefore however first last next former latter'.split())
ENTITY_TYPES = {'PERSON': 'PERSON', 'GPE': 'PLACE', 'LOC': 'PLACE', 'ORG': 'ORGANIZATION'}


@lru_cache(maxsize=1)
def get_nlp():
    try:
        import spacy
        return spacy.load('en_core_web_sm')
    except (ImportError, OSError) as exc:
        raise RuntimeError('Source preprocessing requires spaCy and en_core_web_sm. Run python -m pip install "spacy>=3.8,<4" and python -m spacy download en_core_web_sm.') from exc


def preserve_source_text(value):
    """Normalize whitespace only; keep original Unicode, casing and punctuation."""
    if isinstance(value, str):
        return re.sub(r'\s+', ' ', value).strip()
    if isinstance(value, dict):
        return {key: preserve_source_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [preserve_source_text(item) for item in value]
    return value


def _key(text):
    return ' '.join(re.findall(r"\w+", text.casefold()))


def preprocess_source(entry):
    """Mask fields together with shared entity IDs and retain local diagnostics."""
    nlp = get_nlp()
    fields = {key: preserve_source_text(entry.get(key, '')) for key in ('title', 'description', 'extract')}
    docs = {key: nlp(text) for key, text in fields.items()}
    entities = {}
    for doc in docs.values():
        for ent in doc.ents:
            if ent.label_ in ENTITY_TYPES:
                literal = ent.text.removesuffix("'s").removesuffix('’s')
                entities[_key(literal)] = (literal, ENTITY_TYPES[ent.label_])
        # Back up NER for invented multiword names with proper-noun sequences.
        for match in re.finditer(r'\b[A-Z][\w]*\s+[A-Z][\w]*(?:\s+[A-Z][\w]*)*\b', doc.text):
            span = doc.char_span(*match.span(), alignment_mode='expand')
            if span and any(t.pos_ == 'PROPN' for t in span):
                entities.setdefault(_key(match.group()), (match.group(), 'PERSON'))

    # Link an unambiguous surname to its detected full person name.
    # Do not guess first-name aliases or resolve pronouns automatically.
    surname_owners = {}
    for key, (literal, kind) in list(entities.items()):
        if kind == 'PERSON' and len(key.split()) > 1:
            surname_owners.setdefault(key.split()[-1], set()).add(key)
    aliases = {}
    for surname, owners in surname_owners.items():
        if len(owners) == 1:
            owner = next(iter(owners))
            aliases[('PERSON', surname)] = ('PERSON', owner)
            entities.setdefault(surname, (entities[owner][0].split()[-1], 'PERSON'))

    counts = Counter()
    identifiers = {}
    records = []
    masked = {}
    for field, doc in docs.items():
        spans = []
        occupied = set()

        def add(start, end, kind):
            if start >= end or any(i in occupied for i in range(start, end)):
                return
            literal = doc.text[start:end]
            key = (kind, _key(literal))
            key = aliases.get(key, key)
            if key not in identifiers:
                counts[kind] += 1
                identifiers[key] = f'[{kind}_{counts[kind]}]'
            placeholder = identifiers[key]
            span = doc.char_span(start, end, alignment_mode='expand')
            lemmas = {t.lemma_.casefold() for t in span if t.is_alpha and not t.is_stop} if span else set()
            grammar = 'noun phrase' if kind == 'PHRASE' else kind.lower()
            if kind in {'PHRASE', 'OBJECT'} and span:
                noun = next((t for t in reversed(span) if t.pos_ in {'NOUN', 'PROPN'}), span.root)
                number = noun.morph.get('Number')
                if 'Plur' in number:
                    grammar += '; plural noun'
                elif span.start > 0 and doc[span.start - 1].lower_ in {'a', 'an', 'one'}:
                    grammar += '; singular count noun'
                else:
                    grammar += '; singular or mass noun; choose natural countability'
            elif kind == 'DESCRIPTION' and span:
                grammar = 'adverb/manner' if span.root.pos_ == 'ADV' else 'adjective/descriptor'
            elif kind == 'PERSON' and doc.text[end:end + 2] in {"'s", '’s'}:
                grammar = 'possessive person; possessive suffix is already outside placeholder'
            records.append({'kind': kind, 'literal': literal, 'placeholder': placeholder,
                            'lemmas': sorted(lemmas), 'grammar': grammar})
            spans.append((start, end, placeholder))
            occupied.update(range(start, end))

        for literal, kind in sorted(entities.values(), key=lambda item: -len(item[0])):
            for match in re.finditer(r'(?<!\w)' + re.escape(literal) + r'(?!\w)', doc.text, re.IGNORECASE):
                add(*match.span(), kind)

        # Keep hyphenated actions intact rather than emitting [OBJECT]wedged.
        action_tokens = set()
        for match in re.finditer(r"\b\w+(?:[-‐‑]\w+)+\b", doc.text):
            span = doc.char_span(*match.span(), alignment_mode='expand')
            if span and span[-1].pos_ == 'VERB':
                action_tokens.update(t.i for t in span)

        def disposable(token):
            return (token.i not in action_tokens and token.pos_ in {'NOUN', 'PROPN', 'ADJ', 'ADV'}
                    and token.lower_ not in STRUCTURAL and token.dep_ != 'neg'
                    and token.ent_type_ not in {'DATE', 'TIME', 'CARDINAL', 'ORDINAL', 'QUANTITY', 'MONEY', 'PERCENT'})

        # Preserve determiners, possessives, quantities, verbs, and prepositions.
        # Mask contiguous content inside each noun chunk, not the whole clause.
        for chunk in doc.noun_chunks:
            run = []
            def flush():
                while run and run[-1].text in {'-', '‐', '‑'}:
                    run.pop()
                if run:
                    kind = 'PHRASE' if len(run) > 1 else 'OBJECT'
                    add(run[0].idx, run[-1].idx + len(run[-1]), kind)
                    run.clear()
            for token in chunk:
                if any(i in occupied for i in range(token.idx, token.idx + len(token))):
                    flush()
                elif disposable(token) or (token.text in {'-', '‐', '‑'} and run and token.i not in action_tokens):
                    run.append(token)
                else:
                    flush()
            flush()
        for token in doc:
            if disposable(token):
                add(token.idx, token.idx + len(token), 'DESCRIPTION' if token.pos_ in {'ADJ', 'ADV'} else 'OBJECT')
        text = doc.text
        for start, end, placeholder in sorted(spans, reverse=True):
            text = text[:start] + placeholder + text[end:]
        masked[field] = text
    return {'masked': masked, 'records': records,
            'original_word_count': len(re.findall(r'\b\w+\b', fields['extract']))}


def filter_word_banks(preprocessed, banks):
    """Exclude detected phrases and entity-name components from fresh ingredients."""
    forbidden = {_key(record['literal']) for record in preprocessed['records']}
    for record in preprocessed['records']:
        if record['kind'] in {'PERSON', 'PLACE', 'ORGANIZATION'}:
            forbidden.update(_key(record['literal']).split())
    return {category: [word for word in words if _key(word) not in forbidden]
            for category, words in banks.items()}


def _ingredient_key(value):
    # Treat spacing, hyphens and capitalization as the same supplied ingredient.
    return _key(value).replace(' ', '')


def replacement_guidance(preprocessed, banks):
    """Allocate one globally unused ingredient per ID; retain assignments locally."""
    categories = {'PERSON': ('names',), 'PLACE': ('places',),
                  'ORGANIZATION': ('nouns', 'places'), 'OBJECT': ('animals', 'nouns'),
                  'PHRASE': ('animals', 'nouns'), 'DESCRIPTION': ('adverbs', 'slang')}
    banks = filter_word_banks(preprocessed, banks)
    preprocessed['supplied_ingredients'] = list(dict.fromkeys(word for words in banks.values() for word in words))
    assignments = {}
    used = set()
    lines = []
    for record in preprocessed['records']:
        placeholder, kind = record['placeholder'], record['kind']
        if placeholder in assignments:
            continue
        choices = [word for category in categories[kind] for word in banks.get(category, [])
                   if _ingredient_key(word) not in used]
        if kind == 'DESCRIPTION':
            # A slang noun/interjection is not automatically a usable modifier.
            choices = [word for word in choices
                       if get_nlp()(word.lower())[:].root.pos_ in {'ADJ', 'ADV'}]
        word = choices[0] if choices else None
        if word is not None:
            used.add(_ingredient_key(word))
        assignments[placeholder] = word
        grammar = '; '.join(dict.fromkeys(r.get('grammar', kind.lower()) for r in preprocessed['records']
                                         if r['placeholder'] == placeholder))
        instruction = f'use ingredient "{word}"' if word else 'invent one fresh unused replacement; bank exhausted'
        lines.append(f'{placeholder} ({grammar}): {instruction}')
    preprocessed['assignments'] = assignments
    return ('SOURCE REPLACEMENT RULES:\n'
            'Do not reuse the same supplied replacement ingredient for different placeholders. '
            'Repeated references to the same placeholder must remain consistent. '
            'An assigned ingredient is reserved for its placeholder, including in the title. '
            'Any extra supplied ingredient should be used only once. '
            'Use correct articles: a vs an, based on pronunciation (an apple, a banana). '
            'Maintain grammatical singular/plural agreement; inflect the assigned ingredient as needed. '
            'Treat PERSON as a person name and PLACE as a place, not as extra noun modifiers. '
            'Preserve possessive ownership; do not double a possessive suffix already in the source. '
            'Descriptors may need adjective/adverb inflection and ordinary lowercase. '
            'Do not create long chains of unrelated nouns merely to force bank words into the sentence. '
            'Prefer one strong replacement per semantic slot; never concatenate multiple bank values into one slot. '
            'Rewrite surrounding articles and sentence structure to fit that one ingredient naturally. '
            'Preserve actions, negation, quantities and event order. Do not output placeholder IDs.\n'
            f"Original extract word count: {preprocessed['original_word_count']}. Use this for the length target.\n"
            + '\n'.join(lines))


def ingredient_diagnostics(preprocessed, text):
    """Approximate local warnings, not grammatical judgments or generation gates."""
    doc = get_nlp()(text)
    # Lemmas allow ordinary plural inflection; punctuation/hyphens are separators.
    tokens = [t.lemma_.casefold() for t in doc if t.is_alpha]
    repeated = []
    seen = set()
    for ingredient in preprocessed.get('supplied_ingredients', []):
        key = _ingredient_key(ingredient)
        if key in seen:
            continue
        seen.add(key)
        pattern = [t.lemma_.casefold() for t in get_nlp()(ingredient) if t.is_alpha]
        if not pattern:
            continue
        count = sum(tokens[i:i + len(pattern)] == pattern for i in range(len(tokens) - len(pattern) + 1))
        if count > 1:
            ids = [slot for slot, value in preprocessed.get('assignments', {}).items() if value and _ingredient_key(value) == key]
            references = sum(r['placeholder'] in ids for r in preprocessed['records'])
            repeated.append({'ingredient': ingredient, 'count': count, 'assigned_placeholders': ids,
                             'source_reference_count': references,
                             'may_be_intentional': len(ids) == 1 and references > 1})
    # A small high-confidence list avoids pretending spelling predicts pronunciation.
    vowel_sound = {'apple', 'orange', 'egg', 'elephant', 'umbrella', 'onion', 'hour', 'honest'}
    consonant_sound = {'banana', 'dog', 'cat', 'person', 'table', 'university', 'unicorn', 'one'}
    article_errors = []
    for left, right in zip(doc, doc[1:]):
        if (left.lower_ == 'a' and right.lower_ in vowel_sound or
                left.lower_ == 'an' and right.lower_ in consonant_sound):
            article_errors.append(left.text + ' ' + right.text)
    return {'repeated_supplied_ingredients': repeated,
            'obvious_article_errors': article_errors}


def log_overlap(preprocessed, generated):
    """Diagnostic only: never reject, regenerate, or interrupt generation."""
    try:
        text = ' '.join(str(generated.get(key, '')) for key in ('title', 'extract'))
        normalized = ' ' + _key(text) + ' '
        reused = lambda kinds: sorted({r['literal'] for r in preprocessed['records']
                                      if r['kind'] in kinds and ' ' + _key(r['literal']) + ' ' in normalized})
        target = {lemma for r in preprocessed['records'] for lemma in r['lemmas']}
        actual = {t.lemma_.casefold() for t in get_nlp()(text) if t.is_alpha and not t.is_stop}
        report = {'people_names_reused': reused({'PERSON'}), 'places_reused': reused({'PLACE'}),
                  'noun_phrases_reused': reused({'PHRASE', 'OBJECT'}),
                  'targeted_vocabulary_overlap': round(len(target & actual) / len(target), 3) if target else 0.0}
        report.update(ingredient_diagnostics(preprocessed, text))
        logger.warning('Local rewrite overlap diagnostic: %s', report)
        return report
    except Exception:
        logger.exception('Local rewrite overlap diagnostic unavailable')
        return None
