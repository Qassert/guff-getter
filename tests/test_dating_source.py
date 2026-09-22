"""Reusable source integration with fake Mongo and HTTP; no live services."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]


class Collection:
    def __init__(self):
        self.rows = {}

    def update_one(self, query, update, upsert=False):
        key = query['_id']
        if upsert:
            self.rows.setdefault(key, dict(_id=key, **copy.deepcopy(update['$setOnInsert'])))
        elif key in self.rows:
            self.rows[key]['numberOftimesUsed'] += update['$inc']['numberOftimesUsed']
        return MagicMock(modified_count=int(key in self.rows))

    def find(self):
        return copy.deepcopy(list(self.rows.values()))


@pytest.fixture
def api(tmp_path):
    collections = {'reusable_entries': Collection(), 'dating_entries': Collection()}
    with patch('pymongo.MongoClient') as mongo:
        mongo.return_value.__getitem__.return_value.__getitem__.side_effect = collections.__getitem__
        spec = importlib.util.spec_from_file_location('isolated_reusable', ROOT / 'newsmuncher/api/reusable.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.SEEDS_DIR = tmp_path
    (tmp_path / 'lonelyHearts.json').write_text(json.dumps([
        {'title': 'First', 'description': 'First description'},
        {'title': 'Second', 'description': 'Second description', 'extract': 'Full ad', 'numberOftimesUsed': 3},
    ]))
    return module, collections


def test_dating_seed_and_persistent_usage(api):
    module, collections = api
    client = TestClient(module.app)
    entries = client.get('/get_all/?source=dating').json()
    assert [(e['title'], e['description'], e['extract'], e['numberOftimesUsed']) for e in entries] == [
        ('First', 'First description', 'First description', 0), ('Second', 'Second description', 'Full ad', 3)]
    assert client.put('/increment_usage/' + entries[0]['id'] + '?source=dating').status_code == 200
    assert client.get('/get_all/?source=dating').json()[0]['numberOftimesUsed'] == 1
    assert len(collections['dating_entries'].rows) == 2
    assert not collections['reusable_entries'].rows
    assert client.get('/get_all/?source=unknown').status_code == 400


@pytest.mark.parametrize('source', [None, 'dating'])
def test_shared_job_selection_preview_and_increment(api, tmp_path, source):
    from newsmuncher.jobs import fetch_historical_funny as job
    module, collections = api
    from bson import ObjectId
    key = ObjectId()
    collections['reusable_entries'].rows[key] = dict(_id=key, title='Drivel', description='History', extract='Story', numberOftimesUsed=0)
    client = TestClient(module.app)
    suffix = '?source=dating' if source else ''
    target = tmp_path / 'preview.json'
    with patch.object(job, 'TEMP_FILE', target), patch.object(job.requests, 'get', side_effect=lambda url: client.get(url.split(job.REUSABLE_API_BASE_URL)[1])) as get, patch.object(job.requests, 'put', side_effect=lambda url: client.put(url.split(job.REUSABLE_API_BASE_URL)[1])) as put:
        result = job.fetch_historical_funny_from_api(source)
    assert result == json.loads(target.read_text())
    assert result == (dict(title='First', description='First description', extract='First description') if source else dict(title='Drivel', description='History', extract='Story'))
    get.assert_called_once_with(job.REUSABLE_API_BASE_URL + '/get_all/' + suffix)
    assert put.call_count == 1 and put.call_args.args[0].endswith(suffix)
    rows = client.get('/get_all/' + suffix).json()
    assert rows[0]['numberOftimesUsed'] == 1
    if source:
        assert collections['reusable_entries'].rows[key]['numberOftimesUsed'] == 0


def test_real_seed_and_button_layout(api):
    module, _ = api
    module.SEEDS_DIR = ROOT / 'data/seeds'
    entries = module.get_all_reusable_entries('dating')
    seed = json.loads((module.SEEDS_DIR / 'lonelyHearts.json').read_text())
    assert entries[0]['title'] == seed[0]['title']
    assert entries[0]['description'] == seed[0]['description']
    env = Environment(loader=FileSystemLoader(ROOT / 'newsmuncher/templates'))
    env.globals['url_for'] = lambda *args, **kwargs: '/static/' + kwargs.get('path', '')
    html = env.get_template('pet_profile.html').render(pet={})
    import re
    labels = re.findall(r'class="funky-button source-choice"[^>]*>([^<]+)', html)
    assert labels == ['DATING', 'DRIVEL', 'WIKIPEDIA', 'POEM', 'PEOPLE']
    css = (ROOT / 'newsmuncher/static/styles.css').read_text()
    block = css.split('.profile-page .nonsense-container, .profile-page .generation-controls {')[1].split('}')[0]
    assert 'justify-content: center' in block and 'left: 50%' in block
    assert 'flex-wrap: wrap' in css.split('.nonsense-container {')[1].split('}')[0]
    preview = (ROOT / 'newsmuncher/api/previews.py').read_text()
    assert '"fetch_dating_from_api": [sys.executable, "-m", "newsmuncher.jobs.fetch_historical_funny", "dating"]' in preview
