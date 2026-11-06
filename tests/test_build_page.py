import csv
from pathlib import Path


def test_build_route_is_registered_without_changing_create_route():
    main = Path('newsmuncher/main.py').read_text()
    router = Path('newsmuncher/api/build.py').read_text()
    assert 'app.include_router(build_router' in main
    assert "@router.get('/build'" in router
    assert 'pet_profile' not in router


def test_build_assets_and_csv_schemas_are_complete():
    template = Path('newsmuncher/templates/build.html').read_text()
    assert "build-page.css" in template
    assert "build-page.js" in template
    expected = {
        'build-stuff.csv': {'adjective', 'surreal_descriptor', 'object', 'device'},
        'build-swear.csv': {'bijv_nw', 'gilles', 'zelfs_nw', 'handelend'},
        'build-modifiers.csv': {'adverb', 'adjective'},
        'build-people.csv': {'person'},
        'build-themes.csv': {'theme'},
    }
    for filename, categories in expected.items():
        path = Path('newsmuncher/static/data') / filename
        with path.open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        assert rows
        assert set(rows[0]) == {'category', 'word'}
        assert categories <= {row['category'] for row in rows}
        assert all(row['word'].strip() for row in rows)


def test_build_navigation_is_discoverable_without_editing_create_template():
    gallery = Path('newsmuncher/templates/view_pets.html').read_text()
    create = Path('newsmuncher/templates/pet_profile.html').read_text()
    assert 'href="/build"' in gallery
    assert 'href="/build"' not in create
