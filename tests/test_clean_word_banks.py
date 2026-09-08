"""Full-vocabulary cleaner tests; no API calls and writes only to temp fixtures."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import clean_word_banks as c


class CleanerTests(unittest.TestCase):
    def check_split(self, original, expected):
        result = c.classify_entry(original, controlled_bank=True)
        self.assertIn(result['group'], {'CERTAIN', 'REVIEW'})
        self.assertEqual(result['proposal'], expected)

    def test_single_words(self):
        for word in 'Cat Aardvark Alligator Accordion Calculator Defibrillator Zucchini Ox thermometer Mandrill Canid Aardwolf Urial'.split():
            with self.subTest(word=word):
                r = c.classify_entry(word, controlled_bank=True)
                self.assertEqual(r['group'], 'UNCHANGED')
                self.assertEqual(r['proposal'], word)

    def test_animals_and_objects(self):
        examples = {'Arabianleopard': 'Arabian leopard', 'Blackwidowspider': 'Black widow spider',
                    'Bluewhale': 'Blue whale', 'Dungbeetle': 'Dung beetle', 'Elephantseal': 'Elephant seal',
                    'Englishpointer': 'English pointer', 'Greatblueheron': 'Great blue heron',
                    'Greatwhiteshark': 'Great white shark', 'Hammerheadshark': 'Hammerhead shark',
                    'Hermitcrab': 'Hermit crab', 'Komododragon': 'Komodo dragon', 'Mantaray': 'Manta ray',
                    'Polarbear': 'Polar bear', 'ballpointpen': 'ballpoint pen',
                    'baseballbat': 'baseball bat', 'bathroomscale': 'bathroom scale', 
                    'clothespeg': 'clothes peg', 'remotecontrol': 'remote control', 'towelrack': 'towel rack'}
        for old, new in examples.items():
            with self.subTest(old=old): self.check_split(old, new)

    def test_conventional_closed_compounds(self):
        words = """Seahorse Swordtail Catshark Flyingfish Ladybug Goldfish Starfish Jellyfish
        Dragonfly Firefly Butterfly Grasshopper Woodpecker Kingfisher Blackbird Bluebird
        Bluejay Cockroach Centipede Earthworm Silkworm Silverfish Rattlesnake Roadrunner
        Swordfish Angelfish Clownfish Parrotfish Shellfish Crayfish Cuttlefish Bedframe""".split()
        for word in words:
            for value in [word, word.lower()]:
                with self.subTest(value=value):
                    result = c.classify_entry(value, controlled_bank=True)
                    self.assertEqual(result['group'], 'UNCHANGED')
                    self.assertEqual(result['proposal'], value)

    def test_spelling_variants_require_review(self):
        for value in ['Gamefowl', 'Landfowl', 'Sabertoothedcat']:
            self.assertEqual(c.classify_entry(value, controlled_bank=True)['group'], 'REVIEW')

    def test_whole_word_score_guard(self):
        # Common parts alone must not authorize a split of an attested whole word.
        with patch.object(c, 'frequency', return_value=3.5), patch.object(c, 'segment', return_value=[(8.0, ('test', 'word')), (11.0, ('tes', 'tword'))]):
            self.assertEqual(c.classify_entry('testword', controlled_bank=True)['group'], 'UNCHANGED')
        with patch.object(c, 'frequency', side_effect=lambda w: 0.5 if w == 'testword' else 4.0), patch.object(c, 'segment', return_value=[(8.0, ('test', 'word')), (11.0, ('tes', 'tword'))]):
            self.assertEqual(c.classify_entry('testword', controlled_bank=True)['group'], 'REVIEW')

    def test_closed_component_does_not_protect_longer_phrase(self):
        self.check_split('jellyfishhat', 'jellyfish hat')
        self.check_split('greatwhiteshark', 'great white shark')
        self.check_split('blackwidowspider', 'black widow spider')

    def test_camel_case(self):
        for old, new in {'ArcticFox': 'Arctic Fox', 'DomesticBactriancamel': 'Domestic Bactrian camel',
                         'NewWorldquail': 'New World quail', 'OldWorldquail': 'Old World quail',
                         'Rubberduckarmy': 'Rubber duck army', 'Screaminggoatfigurine': 'Screaming goat figurine'}.items():
            self.check_split(old, new)

    def test_long_phrases_and_names(self):
        for old, new in {
            'lifesizecardboardcutoutofDannyDeVito': 'life size cardboard cutout of Danny DeVito',
            'glowinthedarktoiletpaper': 'glow in the dark toilet paper',
            'cheesegrateronastick': 'cheese grater on a stick',
            'rubberbandballthesizeofawatermelon': 'rubber band ball the size of a watermelon',
            'basketballhoopforthetoilet': 'basketball hoop for the toilet',
            'minidrumsetforyourfingers': 'mini drum set for your fingers',
        }.items(): self.check_split(old, new)

    def test_readable_and_proper_banks(self):
        for word in ['paper towel', 'can opener electric', 'air-conditioner', "Pickle's Lament", 'Danny DeVito']:
            self.assertEqual(c.classify_entry(word, controlled_bank=True)['group'], 'UNCHANGED')
        self.assertEqual(c.classify_entry('ArcticFox', proper_bank=True)['group'], 'UNCHANGED')
        self.assertNotEqual(c.classify_entry('camcorderstabilizer')['group'], 'CERTAIN')

    def test_review_and_determinism(self):
        r = c.classify_entry('hedgeshears', controlled_bank=True)
        self.assertEqual(r['group'], 'REVIEW')
        self.assertEqual(r, c.classify_entry('hedgeshears', controlled_bank=True))
        self.assertEqual(c.classify_entry('zzqzxq', controlled_bank=True)['group'], 'UNRESOLVED')

    def test_csv_dry_run_and_certain_only_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'animalsAndObjects.csv'
            original = b'\xef\xbb\xbfword,category\r\n"ArcticFox",animal\r\nhedgeshears,"already spaced"\r\n'
            p.write_bytes(original)
            plan = c.plan_file(p)
            self.assertEqual(plan['updated'], original.replace(b'ArcticFox', b'Arctic Fox'))
            with patch.object(c, 'WORDS_DIR', Path(directory)), contextlib.redirect_stdout(io.StringIO()):
                c.main([])
            self.assertEqual(p.read_bytes(), original)
            self.assertEqual(list(Path(directory).glob('*.bak')), [])
            with contextlib.redirect_stdout(io.StringIO()): c.apply_plans([plan])
            self.assertEqual(p.read_bytes(), plan['updated'])
            self.assertEqual(next(Path(directory).glob('*.bak')).read_bytes(), original)

    def test_no_word_count_limit(self):
        result = c.classify_entry('bananapaper' * 8, controlled_bank=True)
        self.assertEqual(result['proposal'], ' '.join(['banana', 'paper'] * 8))
        self.assertEqual(result['group'], 'REVIEW')

    def test_stale_apply_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'animalsAndObjects.csv'
            p.write_text('ArcticFox')
            plan = c.plan_file(p)
            p.write_text('user edit')
            with self.assertRaises(RuntimeError): c.apply_plans([plan])
            self.assertEqual(p.read_text(), 'user edit')
            self.assertEqual(list(Path(directory).glob('*.bak')), [])

    def test_full_real_file_audit(self):
        plan = c.plan_file(c.WORDS_DIR / 'animalsAndObjects.csv')
        self.assertEqual(len(plan['audits']), plan['stats']['entries'])
        self.assertGreater(plan['stats']['CERTAIN'] + plan['stats']['REVIEW'], 80)
        for record in plan['audits']:
            self.assertIn(record['group'], {'CERTAIN', 'REVIEW', 'UNCHANGED', 'UNRESOLVED'})


if __name__ == '__main__': unittest.main()
