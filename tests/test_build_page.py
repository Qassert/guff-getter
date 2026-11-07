import csv
from pathlib import Path


def test_build_route_is_registered_without_changing_create_route():
    main = Path('newsmuncher/main.py').read_text()
    router = Path('newsmuncher/api/build.py').read_text()
    assert 'app.include_router(build_router' in main
    assert "@router.get('/build'" in router
    assert "request.cookies.get('active_pet'" in router
    assert "quote(active_pet, safe='')" in router


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


def test_build_reuses_create_udder_parchment_and_background_without_source_actions():
    template = Path('newsmuncher/templates/build.html').read_text()
    create = Path('newsmuncher/templates/pet_profile.html').read_text()
    assert 'class="profile-page build-page"' in template
    assert 'id="initialBackground" class="initial-background"' in template
    assert 'id="generatedBackdrop" class="generated-backdrop"' in template
    assert 'container profile-container build-parchment' in template
    assert 'id="sourceUdder" class="source-udder"' in template
    assert template.count('class="source-choice udder-teat') == 1  # Jinja loop, five runtime buttons.
    for asset in ('udder-master-body.png', 'udder-teat-1.png', 'udder-teat-5.png'):
        assert asset in template and asset in create
    for script in ('image-background.js', 'image-colors.js', 'source-udder.js', 'udder-sounds.js'):
        assert script in template
    assert 'onclick="fetchAndDisplay' not in template
    assert 'data-source=' not in template
    assert 'js/creation/script.js' in template  # Shared CREATE result/action lifecycle only.
    assert "if (!document.querySelector('[data-build-workshop]')) restoreImageRewrite()" in Path(
        'newsmuncher/static/js/creation/script.js').read_text()
    assert '<h1>BUILD A MUNGE</h1>' in template


def test_build_uses_create_parchment_rules_instead_of_a_second_paper_surface():
    css = Path('newsmuncher/static/build-page.css').read_text()
    shared = Path('newsmuncher/static/css/shared/styles.css').read_text()
    assert "border-image: url('../../images/backgrounds/parchment.png')" in shared
    assert '.profile-page :is(.profile-container, #outputContainer)::before' in shared
    assert '.build-parchment::before' not in css
    assert "url('parchment.png')" not in css
    assert 'margin-top: clamp(70px, 8vw, 150px)' in css


def test_build_is_centered_in_shared_furry_navigation_only():
    create = Path('newsmuncher/templates/pet_profile.html').read_text()
    build = Path('newsmuncher/templates/build.html').read_text()
    gallery = Path('newsmuncher/templates/promotion_gallery.html').read_text()
    pet_selection = Path('newsmuncher/templates/view_pets.html').read_text()
    for template in (create, build, gallery):
        assert template.index('mode-nav-create') < template.index('mode-nav-build') < template.index('mode-nav-gallery')
        assert 'images/buttons/build-idle.png' in template
    assert 'mode-nav-build mode-nav-active" aria-current="page" aria-label="BUILD"' in build
    assert 'mode-navigation' not in pet_selection and 'href="/build"' not in pet_selection


def test_build_button_asset_matches_existing_navigation_dimensions():
    import struct
    def png_size(path):
        data = Path(path).read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
        return struct.unpack('>II', data[16:24])
    create = png_size('newsmuncher/static/images/buttons/create-idle.png')
    gallery = png_size('newsmuncher/static/images/buttons/gallery-idle.png')
    build = png_size('newsmuncher/static/images/buttons/build-idle.png')
    assert build == create
    assert all(abs(width / height - 3) < .07 for width, height in (create, build, gallery))


def test_build_offers_three_responsive_munge_story_lengths():
    template = Path('newsmuncher/templates/build.html').read_text()
    css = Path('newsmuncher/static/build-page.css').read_text()
    assert 'for target in (30, 60, 90)' in template
    assert 'data-munge-target="{{ target }}"' in template
    assert 'role="group" aria-label="Choose story length"' in template
    assert '.munge-buttons' in css
    assert 'flex-wrap: wrap' in css


def test_build_removes_theme_scene_selector_but_keeps_other_ingredient_groups():
    template = Path('newsmuncher/templates/build.html').read_text()
    assert 'Theme / Scene' not in template
    assert 'data-theme-url' not in template
    assert 'data-category="theme"' not in template
    for category in ('stuff', 'swear', 'modifier', 'person'):
        assert f'data-category="{category}"' in template
    assert "path='build-page.js') }}?v=build-edit-2" in template
    assert "path='build-page.css') }}?v=build-layout-2" in template


def test_build_reuses_create_editors_and_bottom_action_order():
    template = Path('newsmuncher/templates/build.html').read_text()
    assert template.count('data-prompt-editor') == 1
    assert 'data-prompt-preview' not in template
    assert 'Complete prompt preview' not in template
    assert 'id="responseBodyDraft" data-build-story' in template
    action_ids = [
        'copyMungeButton', 'bankButton', 'redoImageButton', 'deleteCreationButton',
        'embellishButton', 'jingleButton', 'jingleStop', 'animationControls',
    ]
    positions = [template.index(f'id="{action_id}"') for action_id in action_ids]
    assert positions == sorted(positions)
    for script in ('creation-meta.js', 'image-loading.js', 'embellish.js', 'video.js',
                   'jingles.js', 'script.js'):
        assert script in template


def test_build_prompt_editor_auto_sizes_and_remains_the_only_prompt_surface():
    script = Path('newsmuncher/static/build-page.js').read_text()
    css = Path('newsmuncher/static/build-page.css').read_text()
    assert "editor.style.height = 'auto'" in script
    assert "editor.style.height = `${editor.scrollHeight}px`" in script
    assert "target_words: targetWords, prompt" in script
    assert "if (!this.promptDirty) this.resetPrompt()" in script
    assert "this.promptDirty = true" in script
    assert 'data-reset-prompt' in Path('newsmuncher/templates/build.html').read_text()
    assert 'overflow-y: hidden' in css
    assert '.prompt-preview pre' not in css


def test_build_success_explicitly_overrides_shared_hidden_output_style():
    script = Path('newsmuncher/static/build-page.js').read_text()
    shared_css = Path('newsmuncher/static/css/shared/styles.css').read_text()
    assert '#outputContainer { display: none;' in shared_css
    assert "result.style.display = 'block'" in script
    assert 'displayBuildStory(this.element, story)' in script


def test_build_reuses_create_article_fitter_after_generation_and_manual_edits():
    template = Path('newsmuncher/templates/build.html').read_text()
    script = Path('newsmuncher/static/build-page.js').read_text()
    assert "js/shared/article-text-fit.js" in template
    assert 'oninput="autoResize(this); responseEdited(); updateCopyButton()"' in template
    assert 'root.autoResize?.(editor)' in script
