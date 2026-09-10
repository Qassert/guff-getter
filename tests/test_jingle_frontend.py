from pathlib import Path
import subprocess
import unittest
from jinja2 import Environment, FileSystemLoader
from html.parser import HTMLParser


class JingleFrontendTests(unittest.TestCase):
    def test_javascript(self):
        subprocess.run(["node", "tests/jingles.test.js"], check=True)
        for file in ("jingles.js", "script.js"):
            subprocess.run(["node", "--check", "newsmuncher/static/" + file], check=True)

    def test_template_controls_and_unique_ids(self):
        env = Environment(loader=FileSystemLoader("newsmuncher/templates"))
        env.globals["url_for"] = lambda name, **kw: "/static/" + kw["path"]
        html = env.get_template("pet_profile.html").render(pet={})
        class IDs(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "id" in attrs:
                    self.ids.append(attrs["id"])
        parser = IDs()
        parser.feed(html)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(html.count('class="jingle-controls"'), 1)
        self.assertIn('id="jingleControls" class="jingle-controls" hidden', html)
        self.assertIn('onclick="jingleUI.act()"', html)
        self.assertIn('onclick="jingleUI.stop()"', html)
        self.assertNotIn('id="savedJingles"', html)
        self.assertNotIn('savedJingleSelect', html)
        self.assertNotIn('savedJinglePlay', html)
        self.assertNotIn('savedJingleStop', html)
        self.assertNotIn('jingleUI.playSaved()', html)
        script = Path("newsmuncher/static/script.js").read_text()
        self.assertIn('jingleUI.discover();', script.split('window.onload =')[1])
        self.assertIn('jingleUI.discover();', script.split('function bankThisBeauty()')[1].split('async function loadRewriteImage')[0])
        self.assertIn('aria-live="polite"', html)
        self.assertEqual(html.count(">EDIT</button>"), 2)
