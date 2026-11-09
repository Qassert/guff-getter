(function (root) {
    'use strict';

    const shared = root.NewsMuncherSwearGenerator ||
        (typeof require === 'function' ? require('./swear-generator.js') : null);
    const CATEGORIES = ['adjective', 'surreal_descriptor', 'object', 'device'];
    const STRUCTURES = [
        ['adjective', 'object'],
        ['adjective', 'device'],
        ['object', 'device'],
        ['adjective', 'object', 'device'],
        ['adjective', 'surreal_descriptor', 'object'],
        ['adjective', 'surreal_descriptor', 'device'],
        ['adjective', 'surreal_descriptor', 'object', 'device'],
        ['surreal_descriptor', 'adjective', 'object', 'device']
    ];
    // The first four shorter structures share 30% probability; the four
    // two-descriptor structures share 70%. Selection inside each band remains random.
    const STRUCTURE_WEIGHTS = [7.5, 7.5, 7.5, 7.5, 17.5, 17.5, 17.5, 17.5];

    class ObjectGenerator extends shared.SwearGenerator {
        constructor(vocabulary, options = {}) {
            super(vocabulary, {...options, structures: STRUCTURES,
                structureWeights: STRUCTURE_WEIGHTS,
                emptyError: 'The object vocabulary has no complete phrase structures.'});
        }
    }

    function parseCSV(text) {
        return shared.parseVocabularyCSV(text, CATEGORIES);
    }

    async function mount(element, fetcher) {
        return shared.mountGenerator(element, {
            fetcher: fetcher || ((url, options) => fetch(url, options)),
            categories: CATEGORIES,
            structures: STRUCTURES,
            selectorPrefix: 'object',
            storageKey: 'newsmuncher.objectGenerator.used',
            slotClass: 'object-word-slot',
            errorClass: 'object-generator-error',
            Generator: ObjectGenerator
        });
    }

    const api = {CATEGORIES, STRUCTURES, STRUCTURE_WEIGHTS, parseCSV, ObjectGenerator, mount};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.NewsMuncherObjectGenerator = api;
    if (root.document) root.document.querySelectorAll('[data-object-generator]').forEach(element => mount(element));
})(typeof window !== 'undefined' ? window : globalThis);
