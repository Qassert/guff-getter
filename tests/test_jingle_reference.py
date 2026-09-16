"""Offline A/B tests. Modal decorators, network and ACE-Step are never invoked."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import types
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from jingle_service.contract import GenerationRequest, MusicBrief
from scripts import compare_jingle_reference as cli

MP3 = b'ID3' + b'x' * 2000
BRIEF = MusicBrief(music_prompt='Ska. A ferret committee.', lyrics='Ferrets vote again!', duration_seconds=25)
ENTRY = 'a' * 24


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    narration = tmp_path / 'narration'
    narration.mkdir()
    audio = narration / f'{ENTRY}.mp3'
    audio.write_bytes(MP3)
    db = tmp_path / 'jingles.sqlite3'
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE jingles(id TEXT PRIMARY KEY, state TEXT)')
        connection.execute('INSERT INTO jingles VALUES (?, ?)', (ENTRY, json.dumps({'brief': BRIEF.model_dump()})))
    monkeypatch.setattr(cli, 'GENERATED_NARRATION_DIR', narration)
    monkeypatch.setattr(cli, 'JINGLE_STATE_FILE', db)
    monkeypatch.setattr(cli, 'OUTPUT_ROOT', tmp_path / 'experiment')
    monkeypatch.setattr(cli, 'load_dotenv', Mock())
    monkeypatch.setenv('MODAL_JINGLE_ENDPOINT', 'https://example.invalid/generate')
    monkeypatch.setenv('MODAL_JINGLE_KEY', 'secret-key')
    monkeypatch.setenv('MODAL_JINGLE_SECRET', 'secret-secret')
    return audio, db


def pair():
    return cli.make_pair(ENTRY, BRIEF, MP3, 1729)[2]


def test_pair_identical_except_reference_and_namespaced_id():
    a, b = pair().values()
    assert a.seed == b.seed == 1729
    assert a.music_prompt == b.music_prompt == BRIEF.music_prompt
    assert a.lyrics == b.lyrics == BRIEF.lyrics
    assert a.duration_seconds == b.duration_seconds == 25
    assert a.reference_bytes() is None
    assert b.reference_bytes() == MP3
    assert a.request_id != b.request_id
    assert pair()['B'].request_id == b.request_id
    assert a.model_dump(exclude={'request_id', 'reference_audio_b64', 'reference_sha256'}) == b.model_dump(exclude={'request_id', 'reference_audio_b64', 'reference_sha256'})
    assert '/experiments/narration-reference-v1/' in str(b.output_path('/results'))


@pytest.mark.parametrize('changes', [
    {'reference_audio_b64': '%%%bad'},
    {'reference_sha256': '0' * 64},
    {'reference_sha256': None},
    {'reference_audio_b64': ''},
    {'seed': None},
    {'experiment': None},
    {'reference_audio_b64': base64.b64encode(b'not-mp3').decode(), 'reference_sha256': hashlib.sha256(b'not-mp3').hexdigest()},
    {'reference_audio_b64': 'a' * 2_800_001},
])
def test_invalid_reference_rejected(changes):
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate({**pair()['B'].model_dump(), **changes})


def test_decoded_size_limit():
    data = b'ID3' + b'x' * 2_000_000
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate({**pair()['B'].model_dump(),
            'reference_audio_b64': base64.b64encode(data).decode(), 'reference_sha256': hashlib.sha256(data).hexdigest()})


def test_dry_run_no_calls_no_files(inputs, monkeypatch):
    request = Mock(side_effect=AssertionError('No network'))
    monkeypatch.setattr(cli.requests, 'post', request)
    assert cli.main(['--entry-id', ENTRY, '--dry-run']) == 0
    request.assert_not_called()
    assert not cli.OUTPUT_ROOT.exists()
    assert inputs[0].read_bytes() == MP3


def test_run_two_requests_and_repeated_run_stops(inputs, monkeypatch):
    request = Mock(return_value=MP3)
    monkeypatch.setattr(cli, 'fetch_audio', request)
    before = [p.read_bytes() for p in inputs]
    assert cli.main(['--entry-id', ENTRY, '--run']) == 0
    assert request.call_count == 2
    a, b = [call.args[0] for call in request.call_args_list]
    assert a.reference_bytes() is None and b.reference_bytes() == MP3
    outputs = list(cli.OUTPUT_ROOT.glob('*/?.mp3'))
    assert len(outputs) == 2 and all(p.read_bytes() == MP3 for p in outputs)
    assert cli.main(['--entry-id', ENTRY, '--run']) == 1
    assert request.call_count == 2
    assert [p.read_bytes() for p in inputs] == before


def test_failure_stops_without_retry_or_secret_logging(inputs, monkeypatch, capsys):
    request = Mock(side_effect=RuntimeError('secret-key secret-secret'))
    monkeypatch.setattr(cli, 'fetch_audio', request)
    assert cli.main(['--entry-id', ENTRY, '--run']) == 1
    assert cli.main(['--entry-id', ENTRY, '--run']) == 1
    request.assert_called_once()
    assert 'secret-key' not in capsys.readouterr().out


def test_missing_audio_brief_and_config_fail_before_calls(inputs, monkeypatch):
    request = Mock()
    monkeypatch.setattr(cli, 'fetch_audio', request)
    monkeypatch.delenv('MODAL_JINGLE_KEY')
    assert cli.main(['--entry-id', ENTRY, '--run']) == 1
    inputs[0].unlink()
    assert cli.main(['--entry-id', ENTRY]) == 1
    inputs[0].write_bytes(MP3)
    inputs[1].unlink()
    assert cli.main(['--entry-id', ENTRY]) == 1
    request.assert_not_called()
    assert not cli.OUTPUT_ROOT.exists()


def test_exported_brief_fallback(inputs, tmp_path):
    inputs[1].unlink()
    exported = tmp_path / 'brief.json'
    exported.write_text(BRIEF.model_dump_json())
    assert cli.load_inputs(ENTRY, exported) == (BRIEF, MP3)


@pytest.fixture
def endpoint(tmp_path, monkeypatch):
    # Execute the actual endpoint body without importing/deploying Modal or loading ML.
    tree = ast.parse(Path('jingle_service/modal_app.py').read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'JingleGenerator')
    method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == 'generate')
    method.decorator_list = []
    module = ast.Module(body=[method], type_ignores=[])
    ast.fix_missing_locations(module)
    root = tmp_path / 'results'
    original = GenerationRequest.output_path
    monkeypatch.setattr(GenerationRequest, 'output_path', lambda self, unused: original(self, root))
    calls, paths = [], []
    def generate(handler, lm, params, config, save_dir):
        calls.append((params, config))
        if getattr(params, 'reference_audio', None):
            path = Path(params.reference_audio)
            assert path.read_bytes() == MP3
            paths.append(path)
        wav = Path(save_dir) / 'out.wav'
        wav.write_bytes(b'mock-wave')
        return types.SimpleNamespace(success=True, audios=[{'path': str(wav)}])
    fake = types.ModuleType('acestep.inference')
    fake.GenerationParams = lambda **kw: types.SimpleNamespace(**kw)
    fake.GenerationConfig = lambda **kw: types.SimpleNamespace(**kw)
    fake.generate_music = generate
    monkeypatch.setitem(sys.modules, 'acestep', types.ModuleType('acestep'))
    monkeypatch.setitem(sys.modules, 'acestep.inference', fake)
    def probe(args, **kwargs):
        if args[-1].endswith('reference.mp3'):
            return json.dumps({'format': {'duration': '12'}, 'streams': [{'codec_name': 'mp3'}]})
        return '25.0'
    monkeypatch.setattr('subprocess.check_output', probe)
    monkeypatch.setattr('subprocess.run', lambda args, **kwargs: Path(args[-1]).write_bytes(MP3))
    ns = dict(json=json, os=os, Path=Path, tempfile=tempfile, time=time,
              GenerationRequest=GenerationRequest, outputs=Mock(), GPU='L4', MODEL='acestep-v15-turbo', ACE_REVISION='pinned')
    exec(compile(module, 'jingle_service/modal_app.py', 'exec'), ns)
    instance = types.SimpleNamespace(handler=object(), load_seconds=0)
    return lambda request: ns['generate'](instance, request), calls, paths, root, fake


def test_endpoint_params_cleanup_and_production_isolation(endpoint):
    invoke, calls, paths, root, fake = endpoint
    a, b = pair().values()
    # Same ID in production cannot be overwritten by experimental output.
    root.mkdir()
    production = root / f'{b.request_id}.mp3'
    production.write_bytes(b'PRODUCTION')
    for request in (a, b):
        assert invoke(request.model_dump(mode='json')).body == MP3
    pa, ca = calls[0]; pb, cb = calls[1]
    assert vars(ca) == vars(cb) == {'batch_size': 1, 'audio_format': 'wav', 'use_random_seed': False, 'seeds': [1729]}
    assert pa.reference_audio is None and pb.reference_audio
    assert {k:v for k,v in vars(pa).items() if k != 'reference_audio'} == {k:v for k,v in vars(pb).items() if k != 'reference_audio'}
    assert pa.task_type == 'text2music' and not hasattr(pa, 'src_audio')
    assert not hasattr(pa, 'audio_cover_strength')
    assert all(not p.exists() for p in paths)
    assert production.read_bytes() == b'PRODUCTION'
    assert invoke(b.model_dump(mode='json')).headers['x-jingle-cached'] == 'true'
    assert len(calls) == 2
    marker = json.loads(b.output_path(root).with_suffix('.json').read_text())
    assert 'reference_audio_b64' not in marker['request']
    assert marker['request']['reference_sha256'] == b.reference_sha256


def test_production_old_cache_shape_and_defaults_preserved(endpoint):
    invoke, calls, paths, root, fake = endpoint
    request = {**BRIEF.model_dump(), 'request_id': str(uuid4())}
    assert invoke(request).body == MP3
    params, config = calls[0]
    assert vars(config) == {'batch_size': 1, 'audio_format': 'wav'}
    assert not hasattr(params, 'seed') and not hasattr(params, 'reference_audio')
    marker = json.loads((root / f"{request['request_id']}.json").read_text())
    assert marker['request'] == request
    assert invoke(request).headers['x-jingle-cached'] == 'true'
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        invoke({**request, 'lyrics': 'Different'})
    assert exc.value.status_code == 409 and len(calls) == 1


def test_reference_cleanup_on_inference_failure(endpoint):
    invoke, calls, paths, root, fake = endpoint
    original = fake.generate_music
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('inference failed')
    fake.generate_music = fail
    with pytest.raises(RuntimeError):
        invoke(pair()['B'].model_dump(mode='json'))
    assert paths and not paths[0].exists()
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        invoke(pair()['B'].model_dump(mode='json'))
    assert len(calls) == 1


def test_http_single_attempt_and_no_openai_imports(monkeypatch):
    response = Mock()
    response.status_code = 200
    response.headers = {'Content-Type': 'audio/mpeg'}
    response.iter_content.return_value = [MP3]
    post = Mock()
    post.return_value.__enter__ = Mock(return_value=response)
    post.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(cli.requests, 'post', post)
    assert cli.fetch_audio(pair()['B'], 'https://example.invalid', 'key', 'secret') == MP3
    post.assert_called_once()
    assert post.call_args.kwargs['allow_redirects'] is False
    source = Path(cli.__file__).read_text()
    assert 'import OpenAI' not in source and 'generate_openai' not in source and 'create_jingle_brief' not in source


def test_bad_probe_fails_before_inference_and_cleans_temp(endpoint, monkeypatch):
    invoke, calls, paths, root, fake = endpoint
    seen = []
    def bad_probe(args, **kwargs):
        seen.append(Path(args[-1]))
        return json.dumps({'format': {'duration': '0'}, 'streams': []})
    monkeypatch.setattr('subprocess.check_output', bad_probe)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        invoke(pair()['B'].model_dump(mode='json'))
    assert exc.value.status_code == 422 and not calls
    assert seen and not seen[0].exists()


def recovered_pair():
    identity, manifest, requests = cli.make_pair(ENTRY, BRIEF, MP3, 1729)
    directory = cli.OUTPUT_ROOT / identity
    directory.mkdir(parents=True)
    (directory / 'attempt.json').write_text(json.dumps(manifest))
    (directory / 'A.mp3').write_bytes(MP3)
    (directory / 'A.json').write_text(json.dumps({
        'request': requests['A'].marker_request(), 'status': 'complete', 'bytes': len(MP3)}))
    return directory, requests


def test_resume_only_b_and_completed_resume_zero_calls(inputs, monkeypatch):
    directory, requests = recovered_pair()
    original = {p.name: p.read_bytes() for p in directory.iterdir()}
    def fetch(request, *args, observe):
        assert request == requests['B']
        state = json.loads((directory / 'B.state.json').read_text())
        assert state['stage'] == 'submitted'
        assert state['canonical_request'] == request.marker_request()
        assert state['expected_modal_volume_path'] == str(request.output_path('/results'))
        observe(status_code=200, content_type='audio/mpeg', byte_count=len(MP3))
        return MP3
    provider = Mock(side_effect=fetch)
    monkeypatch.setattr(cli, 'fetch_audio', provider)
    # Stored brief is authoritative, even if the production brief has since changed.
    inputs[1].unlink()
    assert cli.main(['--resume', str(directory)]) == 0
    provider.assert_called_once()
    assert json.loads((directory / 'A.state.json').read_text())['recovered']
    assert json.loads((directory / 'B.state.json').read_text())['stage'] == 'completed'
    assert (directory / 'B.mp3').read_bytes() == MP3
    assert all((directory / name).read_bytes() == data for name, data in original.items())
    assert cli.main(['--resume', str(directory)]) == 0
    provider.assert_called_once()


@pytest.mark.parametrize('bad', ['request', 'status', 'size', 'signature', 'missing', 'manifest', 'reference'])
def test_resume_invalid_recovery_no_calls(inputs, monkeypatch, bad):
    directory, requests = recovered_pair()
    marker = json.loads((directory / 'A.json').read_text())
    if bad == 'request':
        marker['request']['seed'] += 1
    elif bad == 'status':
        marker['status'] = 'started'
    elif bad == 'size':
        marker['bytes'] += 1
    elif bad == 'signature':
        (directory / 'A.mp3').write_bytes(b'BAD' + MP3[3:])
    elif bad == 'missing':
        (directory / 'A.mp3').unlink()
    elif bad == 'manifest':
        manifest = json.loads((directory / 'attempt.json').read_text())
        manifest['seed'] += 1
        (directory / 'attempt.json').write_text(json.dumps(manifest))
    elif bad == 'reference':
        inputs[0].write_bytes(MP3 + b'changed')
    (directory / 'A.json').write_text(json.dumps(marker))
    provider = Mock()
    monkeypatch.setattr(cli.requests, 'post', provider)
    assert cli.main(['--resume', str(directory)]) == 1
    provider.assert_not_called()


def test_resume_ambiguous_records_response_never_retries(inputs, monkeypatch, capsys):
    directory, requests = recovered_pair()
    response = Mock(status_code=303, headers={'Content-Type': 'text/html'})
    post = Mock()
    post.return_value.__enter__ = Mock(return_value=response)
    post.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(cli.requests, 'post', post)
    assert cli.main(['--resume', str(directory)]) == 1
    state = json.loads((directory / 'B.state.json').read_text())
    assert state['stage'] == 'ambiguous'
    assert state['status_code'] == 303 and state['content_type'] == 'text/html'
    assert state['byte_count'] == 0
    assert 'Unexpected HTTP status' in state['safe_error_category']
    assert 'Unexpected HTTP status' in capsys.readouterr().out
    assert cli.main(['--resume', str(directory)]) == 1
    post.assert_called_once()
    # Recovery of the exact B result permits completion without another POST.
    (directory / 'B.mp3').write_bytes(MP3)
    (directory / 'B.json').write_text(json.dumps({
        'request': requests['B'].marker_request(), 'status': 'complete', 'bytes': len(MP3)}))
    assert cli.main(['--resume', str(directory)]) == 0
    post.assert_called_once()


def test_resume_concurrent_lock_prevents_calls(inputs, monkeypatch):
    directory, _ = recovered_pair()
    provider = Mock()
    monkeypatch.setattr(cli, 'fetch_audio', provider)
    with (directory / '.resume.lock').open('a') as lock:
        cli.fcntl.flock(lock, cli.fcntl.LOCK_EX | cli.fcntl.LOCK_NB)
        assert cli.main(['--resume', str(directory)]) == 1
    provider.assert_not_called()
