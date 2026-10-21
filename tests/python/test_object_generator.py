import csv
from collections import Counter
import hashlib
from pathlib import Path


def test_object_vocabulary_is_dedicated_and_sourced_from_existing_csv_files():
    path = Path('newsmuncher/static/data/object-generator-vocabulary.csv')
    with path.open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    assert Counter(row['category'] for row in rows) == {
        'adjective': 73, 'surreal_descriptor': 97, 'object': 1442, 'device': 857,
    }
    assert len({(row['category'], row['word']) for row in rows}) == 2469

    def source_words(filename):
        with Path(filename).open(encoding='utf-8-sig', newline='') as source:
            return {word.strip() for row in csv.reader(source) for word in row if word.strip()}

    adjectives = source_words('newsmuncher/resources/words/adverbs.csv')
    objects = source_words('newsmuncher/resources/words/animalsAndObjects.csv')
    for row in rows[:419]:
        assert row['word'] in (adjectives if row['category'] in {'adjective', 'surreal_descriptor'} else objects)

    with Path('docs/object-expansion-batch-01.csv').open(
            encoding='utf-8', newline='') as source:
        approved = list(csv.DictReader(source))
    assert [(row['category'], row['word']) for row in rows[419:669]] == [
        (row['category'], row['word']) for row in approved]
    later_batches = []
    for number in range(2, 20):
        with Path(f'docs/object-expansion-batch-{number:02d}.csv').open(
                encoding='utf-8', newline='') as source:
            later_batches.extend(csv.DictReader(source))
    assert [(row['category'], row['word']) for row in rows[669:]] == [
        (row['category'], row['word']) for row in later_batches]

    ordinary = {row['word'] for row in rows if row['category'] == 'adjective'}
    surreal = {row['word'] for row in rows if row['category'] == 'surreal_descriptor'}
    assert ordinary.isdisjoint(surreal)


def test_object_assets_are_local_and_mounted_after_the_shared_engine():
    template = Path('newsmuncher/templates/pet_profile.html').read_text()
    assert template.index('js/creation/swear-generator.js') < template.index('js/creation/object-generator.js')
    assert 'data/object-generator-vocabulary.csv' in template


def test_domain_sidecar_covers_runtime_vocabulary_exactly_once():
    runtime_path = Path('newsmuncher/static/data/object-generator-vocabulary.csv')
    sidecar_path = Path('newsmuncher/static/data/object-generator-domains.csv')
    with runtime_path.open(encoding='utf-8', newline='') as source:
        runtime = list(csv.DictReader(source))
    with sidecar_path.open(encoding='utf-8', newline='') as source:
        sidecar = list(csv.DictReader(source))

    assert len(runtime) == len(sidecar) == 2469
    runtime_keys = [(row['category'], row['word']) for row in runtime]
    sidecar_keys = [(row['category'], row['word']) for row in sidecar]
    assert len(sidecar_keys) == len(set(sidecar_keys))
    assert set(sidecar_keys) == set(runtime_keys)
    assert Counter(row['category'] for row in sidecar) == Counter(row['category'] for row in runtime)


def test_domain_sidecar_uses_only_reviewed_metadata_values():
    physical_domains = {
        'kitchen_and_food_preparation', 'furniture_and_interiors',
        'cleaning_and_laundry', 'tools_and_hardware',
        'electronics_and_computing', 'office_and_stationery',
        'plumbing_and_sanitation', 'gardening_and_outdoors',
        'clothing_and_accessories', 'sports_and_recreation',
        'safety_and_monitoring', 'containers_and_storage',
        'domestic_appliances', 'medical_equipment', 'transport_and_maritime',
        'lighting_and_heating', 'toys_and_novelty',
        'industrial_machinery', 'scientific_and_laboratory_equipment',
        'agriculture_and_farming', 'musical_instruments',
        'historical_weapons_and_armour', 'siege_and_fortification',
        'ceremonial_and_religious_objects', 'historical_household_and_writing',
        'road_transport', 'rail_transport', 'maritime_equipment', 'aviation_equipment',
        'construction_tools', 'construction_machinery', 'infrastructure_components',
        'surveying_and_site_equipment', 'computer_hardware',
        'electronics_and_test_equipment', 'robotics_and_automation',
        'communications_and_media_hardware', 'field_and_court_sports',
        'outdoor_and_water_recreation', 'indoor_sports_and_games',
        'theatre_and_stage_equipment', 'film_and_photography',
        'circus_magic_and_puppetry', 'event_and_broadcast_equipment',
        'clothing_and_outerwear', 'accessories_and_personal_items',
        'unusual_furniture_and_interiors', 'domestic_and_cleaning_objects',
        'space_and_astronomy', 'security_and_surveillance',
        'archaeology_and_fieldwork', 'emergency_and_miscellaneous_equipment',
        'maritime_deck_equipment', 'marine_navigation_and_signalling',
        'fishing_and_aquaculture', 'diving_and_underwater_equipment',
        'victorian_domestic_objects', 'medieval_household_and_craft',
        'historical_lighting_and_heating', 'historical_personal_and_travel',
        'chemistry_glassware', 'analytical_instruments',
        'biology_and_microscopy', 'physics_and_demonstration_apparatus',
        'gardening_hand_tools', 'forestry_and_arboriculture',
        'watering_and_greenhouse_equipment', 'landscaping_and_groundskeeping',
        'fairground_rides_and_mechanisms', 'carnival_games_and_stalls',
        'festival_and_parade_objects', 'circus_performance_equipment',
        'firefighting_equipment', 'road_and_medical_rescue',
        'water_and_flood_rescue', 'disaster_and_search_equipment',
        'machine_tools_and_metalworking', 'forming_and_fabrication',
        'woodworking_and_patternmaking', 'factory_handling_and_packaging',
        'camera_and_lens_accessories', 'darkroom_and_printing',
        'broadcast_and_recording', 'cinema_and_projection',
        'museum_display_and_conservation', 'archaeological_excavation',
        'exploration_and_field_equipment', 'navigation_and_cartography',
        'unusual_furniture', 'architectural_fittings', 'public_space_fixtures',
        'institutional_and_library_furniture',
    }
    descriptor_domains = {
        'physical_property', 'texture_and_surface', 'shape_and_geometry',
        'size_and_proportion', 'condition_and_damage', 'motion_and_mechanics',
        'sound', 'light_and_colour', 'emotion_and_mood',
        'personality_and_social', 'cognitive_and_behavioural',
        'medical_and_biological', 'scientific_and_technical',
        'legal_and_institutional', 'political_and_economic',
        'logical_and_abstract', 'supernatural_and_mystical',
    }
    physical_forms = {
        'passive_object', 'hand_tool', 'powered_device', 'measuring_instrument',
        'container', 'fixture', 'furnishing', 'consumable', 'component',
        'location_or_space',
    }
    with Path('newsmuncher/static/data/object-generator-domains.csv').open(
            encoding='utf-8', newline='') as source:
        reader = csv.DictReader(source)
        rows = list(reader)
    assert reader.fieldnames == [
        'category', 'word', 'domain', 'form', 'source_file', 'review_status']
    for row in rows:
        if row['category'] in {'adjective', 'surreal_descriptor'}:
            assert row['domain'] in descriptor_domains
            assert row['form'] == 'descriptor'
            assert row['source_file'] == 'adverbs.csv'
        elif row['source_file'] == 'animalsAndObjects.csv':
            assert row['domain'] in physical_domains
            assert row['form'] in physical_forms
        else:
            assert row['category'] in {'object', 'device'}
            assert row['domain'] in physical_domains
            assert row['form'] in physical_forms
            assert row['source_file'].startswith('curated_batch_')
        assert row['review_status'] in {'confirmed', 'needs_review'}
    assert Counter(row['review_status'] for row in rows)['needs_review'] == 24
    assert Counter(row['review_status'] for row in rows)['confirmed'] == 2445
    assert Counter(row['review_status'] for row in rows[:419]) == {
        'confirmed': 395, 'needs_review': 24,
    }
    assert {row['review_status'] for row in rows[419:]} == {'confirmed'}
    with Path('docs/object-expansion-batch-01.csv').open(
            encoding='utf-8', newline='') as source:
        batch = list(csv.DictReader(source))
    assert [(row['category'], row['word'], row['domain'], row['form'], row['source_file'])
            for row in rows[419:669]] == [
        (row['category'], row['word'], row['domain'], row['form'], row['source_file'])
        for row in batch]
    later_batches = []
    for number in range(2, 20):
        with Path(f'docs/object-expansion-batch-{number:02d}.csv').open(
                encoding='utf-8', newline='') as source:
            later_batches.extend(csv.DictReader(source))
    assert [(row['category'], row['word'], row['domain'], row['form'], row['source_file'])
            for row in rows[669:]] == [
        (row['category'], row['word'], row['domain'], row['form'], row['source_file'])
        for row in later_batches]


def test_classic_banks_remain_byte_identical_and_object_runtime_matches_approved_import():
    expected = {
        'newsmuncher/resources/words/slang.csv':
            'f47f7c575d335a9632a9078f81c384a210bf9bc591f16797e8ac5597191814b1',
        'newsmuncher/resources/words/nouns.csv':
            '616c1becc0dfbbc9b1e5e10e9f39ef460677cde79fe9767a5a9b22454af964e5',
        'newsmuncher/resources/words/adverbs.csv':
            '2dc0da3968971dd5be8d94b14ed1dac48fb308e1618db0bff94cbbe51a130a9e',
        'newsmuncher/resources/words/animalsAndObjects.csv':
            '470cebe68e20b18ffb48618695231faedf09dc6548e62de43784cb5b1a0cccc7',
        'newsmuncher/resources/words/names.csv':
            '233aa81bacac63bbc9747f6b60817fbf3ba49a5e083e9445a1a2290a528d211a',
        'newsmuncher/resources/words/places.csv':
            'af502ec8ac638895ce75c0f6f26b5db87fa758e5c19181bcda285ff6470fb38b',
        'newsmuncher/static/data/object-generator-vocabulary.csv':
            '45f4e688d33ee1199e6e0c920a69a4dad3586946d518f89d5c55aeaa2c08d259',
    }
    for filename, digest in expected.items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest
