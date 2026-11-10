"""Offline tests only: local static assets, no database or generation providers."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

ROOT = Path('newsmuncher/static/images/mad-helper')
MANIFEST = json.loads((ROOT / 'manifest.json').read_text())


def test_shared_helper_settings_and_create_editors_render_unchanged():
    env = Environment(loader=FileSystemLoader('newsmuncher/templates'), autoescape=True)
    html = env.get_template('pet_profile.html').render(
        url_for=lambda name, path: '/static/' + path, creation_url='/create')
    assert 'data-mad-helper-toggle checked' in html
    assert 'data-assets="/static/images/mad-helper/"' in html
    assert '>Mad Helper</label>' in html
    assert 'id="sourceBodyDraft"' in html
    assert 'id="responseBodyDraft"' in html
    assert 'oninput="autoResize(this); responseEdited(); updateCopyButton()"' in html
    for page in ['build.html', 'promotion_gallery.html']:
        rendered = env.get_template(page).render(url_for=lambda name, path: '/static/' + path,
            creation_url='/create', signed_in=True, build_initial_prompt='Editable prompt')
        assert rendered.count('data-mad-helper-toggle') == 1
        assert 'data-mad-helper-text' in rendered
        assert 'data-mad-helper-paper' in rendered
        assert 'mad-helper-3' in rendered
    signed_out = env.get_template('promotion_gallery.html').render(
        url_for=lambda name, path: '/static/' + path, signed_in=False, login_url='/login')
    assert 'data-mad-helper-toggle' not in signed_out
    assert 'js/shared/mad-helper.js' not in signed_out
    assert 'SIGN IN' in signed_out


def test_all_transparent_derivatives_and_manifest_are_served_successfully():
    app = FastAPI()
    app.mount('/static', StaticFiles(directory='newsmuncher/static'))
    with TestClient(app) as client:
        assert client.get('/static/images/mad-helper/manifest.json').json() == MANIFEST
        assert client.get('/static/images/mad-helper/idle.png').content.startswith(b'\x89PNG')
        assert len(MANIFEST['animations']) == 16
        assert len(MANIFEST['originals']) == 17
        for clip in MANIFEST['animations']:
            assert 0 < clip['duration'] < 20
            for key, content_type in [('webm', 'video/webm'), ('fallback', 'image/webp')]:
                response = client.get('/static/images/mad-helper/' + clip[key])
                assert response.status_code == 200
                assert response.headers['content-type'].startswith(content_type)
                assert len(response.content) > 100


@pytest.mark.skipif(not shutil.which('ffprobe'), reason='Offline ffmpeg tooling not installed')
@pytest.mark.parametrize('clip', MANIFEST['animations'], ids=lambda clip: clip['webm'])
def test_every_video_has_alpha_and_no_audio(clip):
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-of', 'json', str(ROOT / clip['webm'])]))
    assert len(info['streams']) == 1
    video = info['streams'][0]
    assert video['codec_type'] == 'video'
    assert video['width'] == video['height'] == 320
    assert video['tags']['alpha_mode'] == '1'


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='Offline ffmpeg tooling not installed')
@pytest.mark.parametrize('filename', ['idle.png', 'animation-01.webm'])
def test_refined_matte_removes_leg_gap_and_preserves_light_details(filename):
    command = ['ffmpeg', '-v', 'error']
    if filename.endswith('.webm'):
        command += ['-ss', '2', '-c:v', 'libvpx-vp9']
    raw = subprocess.check_output(command + ['-i', str(ROOT / filename), '-frames:v', '1',
        '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'])
    alpha = lambda x, y: raw[(y * 320 + x) * 4 + 3]
    assert alpha(158 if filename.endswith('.png') else 155, 282) == 0
    for x, y in [(148, 99), (170, 157), (140, 220)]:
        assert alpha(x, y) >= 250
