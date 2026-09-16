"""Import/decorator tests with Modal completely mocked; no remote calls/builds."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import types
from unittest.mock import Mock, patch

import jingle_service.contract as contract


def test_cpu_diagnostic_and_single_baked_source():
    builder = Mock()
    for method in ('apt_install', 'pip_install', 'run_commands', 'env', 'add_local_python_source'):
        getattr(builder, method).return_value = builder
    app = Mock()
    app.function.side_effect = lambda **kw: lambda fn: fn
    app.cls.side_effect = lambda **kw: lambda cls: cls
    modal = types.ModuleType('modal')
    modal.App = Mock(return_value=app)
    modal.Image = Mock()
    modal.Image.debian_slim.return_value = builder
    modal.Volume = Mock()
    for name in ('enter', 'fastapi_endpoint', 'concurrent'):
        setattr(modal, name, lambda **kw: lambda value: value)
    with patch.dict(sys.modules, {'modal': modal}):
        spec = importlib.util.spec_from_file_location('offline_modal_app', 'jingle_service/modal_app.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, 'JingleGenerator', side_effect=AssertionError('GPU class used')):
            result = module.diagnostic_schema()
    settings = app.function.call_args.kwargs
    assert settings['gpu'] is None
    assert settings['image'] is builder
    assert settings['min_containers'] == 0
    assert settings['retries'] == 0
    assert settings['include_source'] is False
    assert 'volumes' not in settings
    assert app.cls.call_args.kwargs['include_source'] is False
    assert app.cls.call_args.kwargs['image'] is builder
    builder.add_local_python_source.assert_called_once_with('jingle_service', copy=True)
    assert result['build_identifier'] == 'reference-ab-schema-diagnostic-v1'
    assert result['contract_file'] == contract.__file__
    assert result['contract_sha256'] == hashlib.sha256(Path(contract.__file__).read_bytes()).hexdigest()
    assert result['modal_app_file'] == module.__file__
    assert result['modal_app_sha256'] == hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
    assert result['fields'] == sorted(['music_prompt', 'lyrics', 'duration_seconds', 'request_id',
                                      'experiment', 'seed', 'reference_audio_b64', 'reference_sha256', 'genre_profile'])
