"""Static, provider-free checks for the standalone Create-page generator."""
import csv
from collections import Counter
from pathlib import Path


def test_authoritative_vocabulary_was_extracted_without_rtf_artifacts():
    path = Path('newsmuncher/static/data/swear-generator-vocabulary.csv')
    with path.open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    counts = Counter(row['category'] for row in rows)
    assert counts == {'bijv_nw': 440, 'gilles': 141, 'zelfs_nw': 70, 'handelend': 105}
    assert len({(row['category'], row['word']) for row in rows}) == 756
    assert all(row['word'] and not row['word'].startswith(('{\\rtf', '\\')) for row in rows)
    assert {'risqué', 'artist formally known as', 'ball sack', 'pipe-player'} <= {
        row['word'] for row in rows}


def test_create_page_loads_only_the_local_generator_assets():
    template = Path('newsmuncher/templates/pet_profile.html').read_text()
    assert 'data/swear-generator-vocabulary.csv' in template
    assert 'js/creation/swear-generator.js' in template
    assert 'css/creation/swear-generator.css' in template
    generator = Path('newsmuncher/static/js/creation/swear-generator.js').read_text()
    assert 'statcounter' not in generator.lower()
    assert 'https://' not in generator and 'http://' not in generator
