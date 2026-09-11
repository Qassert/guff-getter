"""Offline tests: real spaCy English model, no API or database imports."""
import ast
import contextlib
import io
import json
import random
import re
import unittest
from pathlib import Path
from newsmuncher.utils.source_preprocessing import (
    preprocess_source, preserve_source_text, replacement_guidance, log_overlap, filter_word_banks, ingredient_diagnostics,
)


def local_word_helpers():
    path = Path(__file__).resolve().parents[1] / 'newsmuncher/utils/clean_data.py'
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if
             isinstance(node, ast.FunctionDef) and node.name == 'split_list']
    namespace = {'re': re, 'random': random}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


class SourceTests(unittest.TestCase):
    def mask(self, text, **fields):
        return preprocess_source({'extract': text, **fields})

    def test_people_repeated_across_fields_and_possessive(self):
        result = self.mask("Alice Smith saw Alice Smith's dog. She did not leave.", title='Alice Smith')
        text = result['masked']['extract']
        self.assertNotIn('Alice', text)
        self.assertEqual(result['masked']['title'], '[PERSON_1]')
        self.assertEqual(text.count('[PERSON_1]'), 2)
        self.assertIn("[PERSON_1]'s", text)
        self.assertIn('She did not leave', text)

    def test_unique_surname_reference(self):
        result = self.mask('Alice Smith arrived. Smith did not leave.')
        self.assertEqual(result['masked']['extract'].count('[PERSON_1]'), 2)

    def test_prompt_boundary(self):
        path = Path(__file__).resolve().parents[1] / 'newsmuncher/utils/clean_data.py'
        nodes = [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)
                 and n.name == 'prepare_prompt']
        ns = local_word_helpers()
        ns.update(json=json, preserve_source_text=preserve_source_text, preprocess_source=preprocess_source,
                  replacement_guidance=replacement_guidance, filter_word_banks=filter_word_banks,
                  load_random_words=lambda count: {'names': ['Alice', 'Zelda'], 'places': ['London', 'Mars'],
                      'animals': ['fake dog poop', 'jump-rope', 'bananaslicer'], 'nouns': ['teapot'], 'adverbs': ['loudly'], 'slang': ['blimey']})
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
        template = (path.parents[1] / 'resources/prompts/rewrite.txt').read_text()
        with contextlib.redirect_stdout(io.StringIO()):
            result = ns['prepare_prompt']({'title': 'Alice Smith', 'description': 'A pilot',
                       'extract': 'Alice Smith did not fly to London.'}, 10, template)
        for literal in ['Alice', 'Smith', 'London']:
            self.assertNotIn(literal, result['full_prompt'])
        self.assertEqual(set(word for words in result['contenders'].values() for word in words),
                         set(result['preprocessing']['supplied_ingredients']))
        self.assertNotIn('Alice', result['contenders']['names'])
        self.assertNotIn('London', result['contenders']['places'])
        self.assertIn('Zelda', result['full_prompt'])
        self.assertIn('Mars', result['full_prompt'])
        self.assertIn('did not fly to', result['full_prompt'])
        self.assertIn('Alice Smith', str(result['preprocessing']['records']))
        self.assertNotIn("'records'", result['full_prompt'])
        # Clean CSV values pass through verbatim; even an unclean value is not split.
        for ingredient in ['fake dog poop', 'jump-rope', 'bananaslicer']:
            self.assertIn(ingredient, result['full_prompt'])
            self.assertIn(ingredient, result['preprocessing']['supplied_ingredients'])
        self.assertNotIn('fake-dog-poop', result['full_prompt'])
        self.assertNotIn('banana slicer', result['full_prompt'])
        self.assertNotIn('compound_forms', result['preprocessing'])

    def test_places(self):
        result = self.mask('Alice Smith travelled to London before returning to London.')
        self.assertEqual(result['masked']['extract'].count('[PLACE_1]'), 2)
        self.assertNotIn('London', result['masked']['extract'])

    def test_structure_quantity_negation_and_modifiers(self):
        text = self.mask('She did not sell three bizarre machines because he angrily refused. Then she left.')['masked']['extract']
        for retained in ['She did not sell three', 'because he', 'refused', 'Then she left']:
            self.assertIn(retained, text)
        for removed in ['bizarre', 'machines', 'angrily']:
            self.assertNotIn(removed, text)

    def test_distinctive_phrases_and_hyphens(self):
        sample = ("Nordic Ned sand-wedged a foot-long chugnut out of Fatima Whitbread's inept arse crack "
                  "for a timeshare in a horse meat hamper disco. Hank Marvin wore hypnotic bi-folding "
                  "vulva cufflinks and a mashed potato tank top.")
        result = self.mask(sample)
        text = result['masked']['extract']
        for phrase in ['Nordic Ned', 'Fatima Whitbread', 'foot-long chugnut', 'inept arse crack',
                       'horse meat hamper disco', 'hypnotic bi-folding vulva cufflinks', 'Hank Marvin',
                       'mashed potato tank top']:
            self.assertNotIn(phrase, text)
        self.assertIn('sand-wedged', text)
        self.assertIn('out of', text)
        self.assertIn('for a', text)
        self.assertIn('wore', text)

    def test_repeated_objects(self):
        result = self.mask('She carried a red balloon. He found a red balloon.')
        phrase = [r for r in result['records'] if r['literal'] == 'red balloon']
        self.assertEqual(len(phrase), 2)
        self.assertEqual(phrase[0]['placeholder'], phrase[1]['placeholder'])

    def test_guidance_and_local_overlap(self):
        result = self.mask('Alice Smith carried a red balloon to London.')
        guidance = replacement_guidance(result, {'names': ['Zelda'], 'places': ['Mars'], 'animals': ['fake-dog-poop']})
        self.assertIn('Zelda', guidance)
        self.assertIn('Mars', guidance)
        for literal in ['Alice Smith', 'London', 'red balloon']:
            self.assertNotIn(literal, guidance)
        with self.assertLogs('newsmuncher.utils.source_preprocessing', level='WARNING'):
            report = log_overlap(result, {'title': 'Alice Smith in London', 'extract': 'A red balloon.'})
        self.assertIn('Alice Smith', report['people_names_reused'])
        self.assertIn('London', report['places_reused'])
        self.assertIn('red balloon', report['noun_phrases_reused'])
        self.assertGreater(report['targeted_vocabulary_overlap'], 0)

    def test_unicode(self):
        self.assertEqual(preserve_source_text(' José  visited Zürich — today. '), 'José visited Zürich — today.')

    def test_unique_allocation_and_exhaustion(self):
        records = [{'placeholder': f'[{kind}_{i}]', 'kind': kind, 'literal': f'original{i}'}
                   for i, kind in enumerate(['OBJECT', 'PHRASE', 'PERSON', 'PERSON', 'PLACE', 'DESCRIPTION', 'DESCRIPTION'], 1)]
        records.append(records[0].copy())
        data = {'records': records, 'original_word_count': 30}
        guidance = replacement_guidance(data, {'animals': ['jump-rope'], 'nouns': ['Jump Rope', 'teapot'],
            'names': ['Goofy', 'Zelda'], 'places': ['Mars'], 'adverbs': ['loudly'], 'slang': ['LOUDLY']})
        values = [v for v in data['assignments'].values() if v]
        self.assertEqual(len(values), len(set(v.casefold().replace('-', '').replace(' ', '') for v in values)))
        self.assertEqual(guidance.count('[OBJECT_1]'), 1)
        self.assertIn('bank exhausted', guidance)
        self.assertIn('a vs an', guidance)
        self.assertIn('singular/plural agreement', guidance)
        self.assertIn('never concatenate multiple bank values', guidance)
        for line in guidance.splitlines():
            if line.startswith('[') and 'use ingredient' in line:
                self.assertEqual(line.count('"'), 2)

    def test_descriptor_does_not_receive_interjection(self):
        data = {'records': [{'placeholder': '[DESCRIPTION_1]', 'kind': 'DESCRIPTION',
                            'literal': 'angrily', 'grammar': 'adverb/manner'}], 'original_word_count': 5}
        replacement_guidance(data, {'adverbs': [], 'slang': ['blimey']})
        self.assertIsNone(data['assignments']['[DESCRIPTION_1]'])

    def test_grammar_metadata(self):
        data = self.mask("Alice Smith carried a balloon. She took three balloons and angrily broke Alice Smith's vase.")
        grammar = ' '.join(r['grammar'] for r in data['records'])
        self.assertIn('singular count noun', grammar)
        self.assertIn('plural noun', grammar)
        self.assertIn('adverb/manner', grammar)
        self.assertIn('possessive person', grammar)

    def test_ingredient_diagnostics(self):
        data = {'records': [{'placeholder': '[OBJECT_1]'}, {'placeholder': '[OBJECT_1]'}],
                'assignments': {'[OBJECT_1]': 'jump-rope'},
                'supplied_ingredients': ['jump-rope', 'banana']}
        report = ingredient_diagnostics(data, 'A jump-rope and jump-ropes surrounded a screencleaner. It was a apple beside an banana.')
        repeated = report['repeated_supplied_ingredients']
        self.assertTrue(any(r['ingredient'] == 'jump-rope' and r['may_be_intentional'] for r in repeated))
        self.assertEqual(report['obvious_article_errors'], ['a apple', 'an banana'])
        clean = ingredient_diagnostics(data, 'An apple, a banana, an hour and a unicorn.')
        self.assertEqual(clean['obvious_article_errors'], [])

    def test_split_keeps_all_words(self):
        split = local_word_helpers()['split_list']
        for size in [0, 1, 2, 10, 11]:
            groups = split(list(range(size)))
            self.assertEqual(len(groups), 3)
            self.assertEqual(sorted(x for group in groups for x in group), list(range(size)))


if __name__ == '__main__':
    unittest.main()
