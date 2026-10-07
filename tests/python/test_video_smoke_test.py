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
        if url.endswith('/media/uploads'):
            return Response({'data': {'upload': {'url': 'https://storage.invalid/put?secret=signed',
                'headers': {'Content-Type': 'image/png'}},
                'download_url': 'https://storage.invalid/input?secret=upload'}})
        if method == 'PUT':
            return Response(status=204)
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
    posts = [c for c in fake.calls if c[0] == 'POST' and not c[1].endswith('/media/uploads')]
    assert len(posts) == 2
    wan, svd = posts
    assert wan[2]['json']['duration'] == 5
    assert wan[2]['json']['prompt'] == '<script>motion</script>'
    assert 'prompt' not in svd[2]['json']
    assert svd[2]['headers']['X-Fal-No-Retry'] == '1'
    assert base64.b64decode(svd[2]['json']['image_url'].split(',')[1]) == PNG
    upload = next(c for c in fake.calls if c[0] == 'PUT')
    assert upload[2]['data'] == PNG
    assert upload[2]['headers'] == {'Content-Type': 'image/png'}
    ticket = fake.calls[0]
    assert ticket[1] == video.WAN_BASE + '/media/uploads'
    assert ticket[2]['json'] == {'filename': 'source-image.png', 'size': len(PNG), 'content_type': 'image/png'}
    assert wan[2]['json']['image'] == 'https://storage.invalid/input?secret=upload'
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
    assert len([c for c in fake.calls if c[0] == 'POST' and not c[1].endswith('/media/uploads')]) == 1
    run = next(video.OUTPUT_ROOT.iterdir())
    assert not list(run.glob('*.mp4')) and not list(run.glob('*.part'))
    metadata = json.loads((run / 'results.json').read_text())
    assert metadata['providers']['wan']['state'] == 'failed_or_uncertain'
    error = metadata['providers']['wan']['error']
    assert error['stage'] == {'submit': 'model_submission', 'poll': 'prediction_polling',
                              'download': 'output_download', 'timeout': 'prediction_polling'}[failure]
    assert error['http_status'] == (None if failure in ('submit', 'timeout') else 200)
    if failure == 'submit':
        assert error['exception_type'] == 'Timeout'
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


@pytest.mark.parametrize('stage,status', [
    ('auth_upload_ticket', 401), ('auth_upload_ticket', 503),
    ('image_upload', 403), ('model_submission', 422),
    ('prediction_polling', 500), ('output_download', 404),
])
def test_stage_http_errors_are_safe_and_never_retry(image, monkeypatch, capsys, stage, status):
    monkeypatch.setenv('WAVESPEED_API_KEY', 'test-key')
    fake = FakeSession()
    original = fake.request
    def request(method, url, **kwargs):
        current = ('auth_upload_ticket' if url.endswith('/media/uploads') else
                   'image_upload' if method == 'PUT' else
                   'model_submission' if method == 'POST' else 'prediction_polling')
        if current == stage:
            fake.calls.append((method, url, kwargs))
            return Response({'message': 'Input rejected', 'error': {
                'detail': 'test-key https://storage.invalid/put?secret=signed'},
                'headers': {'Authorization': 'Bearer unknown-secret'},
                'token': 'unknown-secret'}, status=status)
        return original(method, url, **kwargs)
    fake.request = request
    if stage == 'output_download':
        fake.get = lambda *a, **k: Response({'message': 'Output expired'}, status=status)
    with patch.object(video.requests, 'Session', return_value=fake):
        assert video.main(['--image', str(image), '--providers', 'wan', '--confirm-spend']) == 1
    run = next(video.OUTPUT_ROOT.iterdir())
    raw = (run / 'results.json').read_text()
    record = json.loads(raw)['providers']['wan']
    error = record['error']
    assert error['stage'] == stage
    assert error['http_status'] == status
    assert error['exception_type'] == 'SmokeError'
    assert ('Output expired' if stage == 'output_download' else 'Input rejected') in error['provider_message']
    assert all(s['state'] == 'complete' for s in record['stages'][:-1])
    assert len([c for c in fake.calls if c[0] == 'POST' and not c[1].endswith('/media/uploads')]) <= 1
    output = capsys.readouterr()
    assert stage in output.err and str(status) in output.err
    for forbidden in ('test-key', 'unknown-secret', 'Authorization', 'secret=signed', 'https://storage.invalid'):
        assert forbidden not in raw + output.out + output.err


@pytest.mark.parametrize('key_present', [False, True])
def test_diagnose_wan_always_offline_even_with_spend_flags(image, monkeypatch, key_present, capsys):
    if key_present:
        monkeypatch.setenv('WAVESPEED_API_KEY', 'test-key')
    with patch.object(video.requests, 'Session') as session:
        assert video.main(run_args(image) + ['--diagnose-wan', '--confirm-spend']) == (0 if key_present else 1)
        session.assert_not_called()
    assert not video.OUTPUT_ROOT.exists()
    assert 'test-key' not in capsys.readouterr().out


def test_success_records_all_wan_stages(image, monkeypatch):
    monkeypatch.setenv('WAVESPEED_API_KEY', 'test-key')
    with patch.object(video.requests, 'Session', return_value=FakeSession()):
        assert video.main(['--image', str(image), '--providers', 'wan', '--confirm-spend']) == 0
    record = json.loads(next(video.OUTPUT_ROOT.glob('*/results.json')).read_text())['providers']['wan']
    assert [s['stage'] for s in record['stages']][1:] == [
        'auth_upload_ticket', 'image_upload', 'model_submission', 'prediction_polling', 'output_download']
    assert all(s['state'] == 'complete' for s in record['stages'])
    assert [s['http_status'] for s in record['stages']][1:] == [200, 204, 200, 200, 200]
    assert 'error' not in record


@pytest.mark.parametrize('failure', ['network', 'malformed_ticket', 'error_envelope', 'invalid_json'])
def test_ticket_protocol_and_transport_failures(image, monkeypatch, capsys, failure):
    monkeypatch.setenv('WAVESPEED_API_KEY', 'test-key')
    fake = FakeSession()
    def request(*args, **kwargs):
        fake.calls.append(args)
        if failure == 'network':
            raise requests.ConnectionError('Connection failed test-key https://private.invalid/path')
        if failure == 'malformed_ticket':
            return Response({'data': {'upload': {'url': 123, 'headers': {}}, 'download_url': None}})
        if failure == 'error_envelope':
            return Response({'code': 400, 'message': 'Upload capacity exceeded'})
        response = Response()
        def invalid():
            raise ValueError('Invalid JSON')
        response.json = invalid
        return response
    fake.request = request
    with patch.object(video.requests, 'Session', return_value=fake):
        assert video.main(['--image', str(image), '--providers', 'wan', '--confirm-spend']) == 1
    assert len(fake.calls) == 1
    raw = next(video.OUTPUT_ROOT.glob('*/results.json')).read_text()
    error = json.loads(raw)['providers']['wan']['error']
    assert error['stage'] == 'auth_upload_ticket'
    assert error['http_status'] == (None if failure == 'network' else 200)
    if failure == 'network':
        assert error['exception_type'] == 'ConnectionError'
        assert 'Connection failed' in error['exception_message']
    if failure == 'error_envelope':
        assert 'Upload capacity exceeded' in error['provider_message']
    output = capsys.readouterr()
    assert 'test-key' not in raw + output.err
    assert 'private.invalid' not in raw + output.err
