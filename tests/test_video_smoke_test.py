"""Standalone harness validation: all upload/generation/download requests mocked."""
import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from scripts import video_smoke_test as video

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1kAAAAASUVORK5CYII=')
MP4 = b'\x00\x00\x00\x18ftypmp42' + b'fixture'


@pytest.fixture
def image(tmp_path):
    path = tmp_path / 'image.png'
    path.write_bytes(PNG)
    return path


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(video, 'OUTPUT_ROOT', tmp_path / 'outputs')
    monkeypatch.setattr(video.time, 'sleep', lambda seconds: None)
    monkeypatch.delenv('WAVESPEED_API_KEY', raising=False)
    monkeypatch.delenv('FAL_KEY', raising=False)
    # Any accidental real HTTP attempt fails the test, even if a guard is broken.
    monkeypatch.setattr(requests.sessions.Session, 'request', lambda *a, **k: pytest.fail('Live HTTP forbidden'))


class Response:
    def __init__(self, value=None, status=200, data=MP4):
        self.value, self.status_code, self.data = value, status, data
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def json(self): return self.value
    def iter_content(self, size): yield self.data


class FakeSession:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert kwargs['allow_redirects'] is False
        if url.endswith('/media/upload/binary'):
            return Response({'data': {'download_url': 'https://storage.invalid/input?secret=upload'}})
        if method == 'POST':
            if self.fail == 'submit':
                raise requests.Timeout('DO NOT LOG test-key https://secret.invalid')
            return Response({'data': {'id': 'wan-id'}} if 'wavespeed' in url else {'request_id': 'svd-id'})
        if self.fail == 'poll':
            return Response({'data': {'status': 'failed', 'error': 'test-key secret URL'}})
        if '/predictions/' in url:
            return Response({'data': {'status': 'completed', 'outputs': ['https://storage.invalid/video?secret=download']}})
        if url.endswith('/status'):
            return Response({'status': 'COMPLETED'})
        return Response({'video': {'url': 'https://storage.invalid/svd?secret=download'}, 'seed': 7})
    def get(self, url, **kwargs):
        self.calls.append(('DOWNLOAD', url, kwargs))
        assert 'headers' not in kwargs and kwargs['allow_redirects'] is False
        return Response(data=b'error body' if self.fail == 'download' else MP4)


def run_args(image):
    return ['--image', str(image), '--providers', 'wan,svd']


@pytest.mark.parametrize('providers', ['', 'wan', 'svd', 'wan,svd'])
def test_dry_run_zero_calls(image, capsys, providers):
    args = ['--image', str(image)] + (['--providers', providers] if providers else [])
    with patch.object(video.requests, 'Session') as session:
        assert video.main(args) == 0
        session.assert_not_called()
    assert not video.OUTPUT_ROOT.exists()
    assert 'zero provider calls' in capsys.readouterr().out


def test_no_providers_even_confirmed_spends_nothing(image):
    with patch.object(video.requests, 'Session') as session:
        assert video.main(['--image', str(image), '--confirm-spend']) == 0
        session.assert_not_called()


@pytest.mark.parametrize('existing', [None, 'WAVESPEED_API_KEY', 'FAL_KEY'])
def test_all_requested_keys_preflight_before_any_call(image, monkeypatch, existing):
    if existing: monkeypatch.setenv(existing, 'test-key')
    with patch.object(video.requests, 'Session') as session:
        assert video.main(run_args(image) + ['--confirm-spend']) == 1
        session.assert_not_called()
    assert not video.OUTPUT_ROOT.exists()


def test_missing_and_invalid_image_do_not_call_providers(tmp_path):
    with patch.object(video.requests, 'Session') as session:
        assert video.main(['--image', str(tmp_path / 'missing'), '--confirm-spend']) == 1
        invalid = tmp_path / 'invalid.png'
        invalid.write_bytes(b'not an image')
        assert video.main(['--image', str(invalid), '--providers', 'wan', '--confirm-spend']) == 1
        session.assert_not_called()


def test_success_same_image_one_generation_each_and_safe_artifacts(image, monkeypatch, capsys):
    for key in video.KEYS.values(): monkeypatch.setenv(key, 'test-key')
    fake = FakeSession()
    with patch.object(video.requests, 'Session', return_value=fake):
        assert video.main(run_args(image) + ['--prompt', '<script>motion</script>', '--confirm-spend']) == 0
    runs = list(video.OUTPUT_ROOT.iterdir())
    assert len(runs) == 1
    run = runs[0]
    assert (run / 'source-image.png').read_bytes() == PNG
    assert (run / 'wan.mp4').read_bytes() == (run / 'svd.mp4').read_bytes() == MP4
    posts = [c for c in fake.calls if c[0] == 'POST' and 'json' in c[2]]
    assert len(posts) == 2
    wan, svd = posts
    assert wan[2]['json']['duration'] == 5
    assert wan[2]['json']['prompt'] == '<script>motion</script>'
    assert 'prompt' not in svd[2]['json']
    assert svd[2]['headers']['X-Fal-No-Retry'] == '1'
    assert base64.b64decode(svd[2]['json']['image_url'].split(',')[1]) == PNG
    upload = next(c for c in fake.calls if 'files' in c[2])
    assert upload[2]['files']['file'][1] == PNG
    assert fake.trust_env is False
    metadata = json.loads((run / 'results.json').read_text())
    assert metadata['providers']['svd']['parameters']['fps'] == 25
    assert metadata['providers']['svd']['parameters']['cond_aug'] == 0.02
    assert metadata['providers']['svd']['parameters']['motion_bucket_id'] == 127
    assert metadata['providers']['svd']['returned_seed'] == 7
    page = (run / 'compare.html').read_text()
    assert '<script>motion</script>' not in page
    assert 'controls loop muted' in page
    output = capsys.readouterr()
    combined = (run / 'results.json').read_text() + page + output.out + output.err
    for secret in ('test-key', 'secret=upload', 'secret=download', 'Authorization', 'data:image/'):
        assert secret not in combined


@pytest.mark.parametrize('failure', ['submit', 'poll', 'download', 'timeout'])
def test_failure_never_resubmits_or_starts_next_provider(image, monkeypatch, capsys, failure):
    for key in video.KEYS.values(): monkeypatch.setenv(key, 'test-key')
    fake = FakeSession(failure)
    if failure == 'timeout': monkeypatch.setattr(video, 'POLL_TIMEOUT', 0)
    with patch.object(video.requests, 'Session', return_value=fake):
        assert video.main(run_args(image) + ['--confirm-spend']) == 1
    assert len([c for c in fake.calls if c[0] == 'POST' and 'json' in c[2]]) == 1
    run = next(video.OUTPUT_ROOT.iterdir())
    assert not list(run.glob('*.mp4')) and not list(run.glob('*.part'))
    metadata = json.loads((run / 'results.json').read_text())
    assert metadata['providers']['wan']['state'] == 'failed_or_uncertain'
    assert metadata['providers']['svd']['state'] == 'not_started'
    if failure != 'submit': assert metadata['providers']['wan']['request_id'] == 'wan-id'
    output = capsys.readouterr()
    assert 'test-key' not in output.out + output.err + (run / 'results.json').read_text()


def test_keys_alone_never_authorize_calls(image, monkeypatch):
    for key in video.KEYS.values(): monkeypatch.setenv(key, 'test-key')
    with patch.object(video.requests, 'Session') as session:
        assert video.main(run_args(image)) == 0
        session.assert_not_called()


def test_svd_only_does_not_upload_to_wavespeed(image, monkeypatch):
    monkeypatch.setenv('FAL_KEY', 'test-key')
    fake = FakeSession()
    with patch.object(video.requests, 'Session', return_value=fake):
        assert video.main(['--image', str(image), '--providers', 'svd', '--confirm-spend']) == 0
    assert len([c for c in fake.calls if c[0] == 'POST']) == 1
    assert not any('wavespeed' in c[1] for c in fake.calls)
    run = next(video.OUTPUT_ROOT.iterdir())
    assert (run / 'svd.mp4').exists() and not (run / 'wan.mp4').exists()
