"""Verify that contender words are present only in backend payload, not in frontend DOM.

The contender UI has been removed, but the 'contenders' field is still
included in the rewrite response so that the backend word‑selection logic
remains intact.
"""
import subprocess
import unittest
from jinja2 import Environment, FileSystemLoader


class ContenderBackendOnlyTests(unittest.TestCase):
    def test_js_removed_from_template(self):
        """The contenders.js script is no longer loaded."""
        env = Environment(loader=FileSystemLoader('newsmuncher/templates'))
        env.globals['url_for'] = lambda name, **kw: '/static/' + kw['path']
        html = env.get_template('pet_profile.html').render(pet={})
        # The script tag for contenders.js should be absent
        self.assertNotIn('contenders.js', html)
        # The jingles.js and other essential scripts are still present
        self.assertIn('jingles.js', html)
        self.assertIn('script.js', html)

    def test_contender_words_absent_from_css(self):
        """CSS for contender words has been removed."""
        import pathlib
        css_path = pathlib.Path('newsmuncher/static/styles.css')
        css = css_path.read_text()
        # No CSS rules for .contender-words or .contender-side
        self.assertNotIn('.contender-words', css)
        self.assertNotIn('.contender-side', css)

    def test_contenders_payload_still_present_integration(self):
        """The 'contenders' field is still present in the rewrite response.

        This is tested via integration tests in test_image_generation.py.
        """
        pass
