"""Audit CSV word banks offline with frequency-weighted English segmentation.

Install the optional standalone dependency: python -m pip install 'wordfreq>=3.1,<4'
Preview: python -m scripts.clean_word_banks
Only CERTAIN proposals are written with --apply; REVIEW requires human approval
via REVIEWED_OVERRIDES. No runtime application imports beyond path configuration.
"""
import argparse
import csv
import io
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from newsmuncher.config import WORDS_DIR

# Exceptions, not the segmentation dictionary. A reviewed mapping authorizes apply.
REVIEWED_OVERRIDES = {
    'polarbear': 'polar bear',
    'blackwidowspider': 'black widow spider',
    'lifesizecardboardcutoutofDannyDeVito'.lower(): 'life size cardboard cutout of Danny DeVito',
    'cheesegrateronastick': 'cheese grater on a stick',
    'rubberbandballthesizeofawatermelon': 'rubber band ball the size of a watermelon',
}
# Rare zoological words absent/misrepresented in frequency corpora.
PROTECTED_WHOLE_WORDS = {'urial', 'leopon', 'tiglon', 'galliform'}
# Conventional closed spellings: frequency alone can favor their common pieces.
# Exact whole-token protection only; never protects a longer glued expression.
PROTECTED_CLOSED_COMPOUNDS = frozenset("""
    seahorse swordtail catshark flyingfish ladybug goldfish starfish jellyfish
    dragonfly firefly butterfly grasshopper woodpecker kingfisher blackbird bluebird
    bluejay cockroach centipede earthworm silkworm silverfish rattlesnake roadrunner
    swordfish angelfish clownfish parrotfish shellfish crayfish cuttlefish crawfish
    bedframe flashlight
""".split())
# Orthographic variants needing human judgment (closed/open/hyphenated names).
REVIEW_ONLY = {'gamefowl', 'landfowl', 'sabertoothedcat'}
# Preserve internal name casing instead of treating every capital as a boundary.
EMBEDDED_NAMES = {'DannyDeVito': ('Danny', 'DeVito')}
PROPER_BANKS = {'names.csv', 'places.csv'}
HEADER_LABELS = {'word', 'words', 'name', 'names', 'value', 'values', 'category', 'type',
                 'noun', 'nouns', 'adverb', 'adverbs', 'slang', 'animal', 'object'}
CONNECTORS = frozenset('a an of on in with for to the and from your'.split())


@lru_cache(maxsize=1)
def frequency_function():
    try:
        from wordfreq import zipf_frequency
    except ImportError as exc:
        raise RuntimeError("Install the standalone cleaner dependency: python -m pip install 'wordfreq>=3.1,<4'") from exc
    return zipf_frequency


@lru_cache(maxsize=65536)
def frequency(word):
    return frequency_function()(word, 'en')


def segment(value):
    """Top two complete paths through all character positions; no word-count cap."""
    lower = value.lower()
    boundaries = {i for i in range(1, len(value)) if value[i].isupper() and value[i-1].islower()}
    forced = {}
    for name, parts in EMBEDDED_NAMES.items():
        for match in re.finditer(re.escape(name), value):
            start = match.start()
            for part in parts:
                forced[start] = (start + len(part), part)
                boundaries.difference_update(range(start + 1, start + len(part)))
                start += len(part)
    paths = [[] for _ in range(len(value) + 1)]
    paths[0] = [(0.0, ())]
    for start in range(len(value)):
        if not paths[start]:
            continue
        ends = [forced[start][0]] if start in forced else range(start + 1, len(value) + 1)
        for end in ends:
            if any(start < pos < end for pos in forced):
                continue
            word = lower[start:end]
            freq = frequency(word)
            if start not in forced and (freq < 1.0 or len(word) == 1 and word != 'a'):
                continue
            if len(word) == 2 and word not in CONNECTORS and freq < 4.0:
                continue
            cost = 10.0 - max(freq, 1.0)
            if end - start < len(value):
                cost += 2.0 * max(0.0, 3.0 - freq)
            if len(word) <= 2 and word != 'a':
                cost += 1.5
            cost += 5 * sum(start < pos < end for pos in boundaries)
            if end in boundaries:
                cost -= 1.0
            for previous, words in paths[start]:
                paths[end].append((previous + cost, words + (value[start:end],)))
            paths[end] = sorted(set(paths[end]), key=lambda p: (p[0], p[1]))[:2]
    return paths[-1]


def classify_entry(value, *, proper_bank=False, controlled_bank=False):
    """Return a reviewable classification, proposal and explanation."""
    base = {'value': value, 'proposal': value}
    if proper_bank or not value.isalpha() or ' ' in value or '-' in value:
        return dict(base, group='UNCHANGED', reason='already readable/protected')
    if value.lower() in PROTECTED_CLOSED_COMPOUNDS:
        return dict(base, group='UNCHANGED', reason='normal single word; conventional closed compound')
    override = REVIEWED_OVERRIDES.get(value.lower()) if controlled_bank else None
    if override:
        if value[0].isupper():
            override = override[0].upper() + override[1:]
        return dict(base, proposal=override, group='CERTAIN', reason='reviewed exception')
    if value.lower() in PROTECTED_WHOLE_WORDS:
        return dict(base, group='UNCHANGED', reason='normal single word')
    whole = frequency(value.lower())
    camel = any(value[i].isupper() and value[i-1].islower() for i in range(1, len(value)))
    paths = segment(value)
    if not paths:
        if whole >= 1.0:
            return dict(base, group='UNCHANGED', reason='normal single word')
        return dict(base, group='UNRESOLVED', reason='no complete dictionary segmentation')
    best, parts = paths[0]
    if len(parts) == 1:
        return dict(base, group='UNCHANGED' if whole >= 1.0 else 'UNRESOLVED',
                    reason='normal single word' if whole >= 1.0 else 'rare whole word; uncertain')
    proposal = ' '.join(parts)
    margin = paths[1][0] - best if len(paths) > 1 else 9.0
    weakest = min(frequency(word.lower()) for word in parts)
    # Compare the actual split cost with the whole-token cost on the same scale.
    # An attested word needs a substantial advantage, not merely splittable parts.
    whole_cost = 10.0 - max(whole, 1.0)
    split_advantage = whole_cost - best
    if whole >= 2.5 and split_advantage < 2.0 and not camel:
        return dict(base, group='UNCHANGED', reason='normal single word; whole-word score preferred')
    certain = controlled_bank and margin >= 1.5 and weakest >= 3.0
    if value.lower() in REVIEW_ONLY or whole > 0 and split_advantage < 2.0:
        certain = False
    # Long phrases and rare constituents need a human; ranking is not semantics.
    if len(parts) > 5 or any(len(word) < 3 and word.lower() not in CONNECTORS for word in parts):
        certain = False
    return dict(base, proposal=proposal, group='CERTAIN' if certain else 'REVIEW',
                reason=f'margin={margin:.2f}; weakest Zipf={weakest:.2f}; whole Zipf={whole:.2f}; split advantage={split_advantage:.2f}')


def field_spans(text):
    """Locate comma-delimited CSV cells without rewriting delimiters or quoting."""
    start = i = row = column = 0
    quoted = False
    while i < len(text):
        char = text[i]
        if char == '"' and (quoted or not text[start:i].strip()):
            if quoted and i + 1 < len(text) and text[i + 1] == '"':
                i += 2
                continue
            quoted = not quoted
        if not quoted and char in ',\r\n':
            yield start, i, row, column
            if char == ',':
                column += 1
            else:
                row += 1
                column = 0
                if char == '\r' and i + 1 < len(text) and text[i + 1] == '\n':
                    i += 1
            start = i + 1
        i += 1
    if start < len(text) or text.endswith(','):
        yield start, len(text), row, column


def plan_file(path):
    original = path.read_bytes()
    text = original.decode('utf-8-sig')
    # Validate conventional comma CSV before proposing any mutation.
    rows = list(csv.reader(io.StringIO(text, newline=''), strict=True))
    header = bool(rows and rows[0] and all(v.strip().casefold() in HEADER_LABELS for v in rows[0]))
    replacements = []
    audits = []
    stats = Counter(files=1)
    for start, end, row, column in field_spans(text):
        raw = text[start:end]
        # Preserve whitespace, surrounding quotes, BOM and line endings byte-for-byte.
        stripped = raw.strip()
        cell = stripped[1:-1].replace('""', '"') if stripped.startswith('"') and stripped.endswith('"') else stripped
        if not cell or header and row == 0:
            continue
        stats['entries'] += 1
        result = classify_entry(cell, proper_bank=path.name.casefold() in PROPER_BANKS,
                                controlled_bank=path.name.casefold() == 'animalsandobjects.csv')
        result.update(row=row + 1, column=column + 1)
        audits.append(result)
        stats[result['group']] += 1
        if result['group'] == 'UNCHANGED':
            stats['single' if result['reason'].startswith('normal single word') else 'readable'] += 1
        if result['group'] == 'CERTAIN':
            proposal = result['proposal']
            # Only bare alphabetic values reach here; substitution preserves cell style.
            offset = raw.index(cell)
            replacements.append((start + offset, start + offset + len(cell), proposal, cell, row + 1, column + 1))
    for start, end, proposal, _, _, _ in reversed(replacements):
        text = text[:start] + proposal + text[end:]
    updated = (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
    return {'path': path, 'original': original, 'updated': updated, 'changes': replacements, 'stats': stats, 'audits': audits}


def apply_plans(plans):
    """Back up all changing files before writing any; refuse stale previews."""
    changed = [p for p in plans if p['changes']]
    for plan in changed:
        if plan['path'].read_bytes() != plan['original']:
            raise RuntimeError(f"File changed since scan: {plan['path']}")
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    for plan in changed:
        backup = plan['path'].with_name(plan['path'].name + f'.{stamp}.bak')
        with backup.open('xb') as handle:
            handle.write(plan['original'])
        print(f'Backup: {backup}')
    for plan in changed:
        plan['path'].write_bytes(plan['updated'])



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Back up and apply CERTAIN proposals only.')
    args = parser.parse_args(argv)
    plans = [plan_file(path) for path in sorted(WORDS_DIR.glob('*.csv'))]
    totals = Counter()
    print('APPLY CERTAIN ONLY' if args.apply else 'DRY RUN — no files will be modified')
    for plan in plans:
        totals.update(plan['stats'])
        print(f"\n{plan['path'].name}:")
        for group in ['CERTAIN', 'REVIEW', 'UNCHANGED', 'UNRESOLVED']:
            print(group + ':')
            for entry in plan['audits']:
                if entry['group'] == group:
                    print(f"  [{entry['row']}:{entry['column']}] {entry['value']} -> {entry['proposal']} ({entry['reason']})")
        print('FILE SUMMARY:', json.dumps(dict(plan['stats']), sort_keys=True))
    if args.apply:
        apply_plans(plans)
    print('\nSUMMARY:', json.dumps(dict(totals), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
