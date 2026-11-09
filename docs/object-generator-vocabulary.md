# OBJECT generator vocabulary

The Create-page OBJECT generator reads `newsmuncher/static/data/object-generator-vocabulary.csv`.
It is independent of the SWEAR generator and uses its own browser-session duplicate history.

## Sources and mapping

- `adjective` contains 73 descriptive entries selected unchanged from
  `newsmuncher/resources/words/adverbs.csv`.
- `surreal_descriptor` contains 97 psychological, emotional, scientific, medical and otherwise
  incongruous descriptors selected unchanged from `adverbs.csv`. It does not duplicate the
  ordinary `adjective` pool.
- `object` contains 187 recognisable household and everyday-object entries selected unchanged
  from the object section of `newsmuncher/resources/words/animalsAndObjects.csv`.
- `device` contains 62 machines, appliances and contraptions selected unchanged from that same
  object section.

No entry is imported from the SWEAR vocabulary. Multi-word source entries remain one CSV value
and one clickable phrase slot.

## Phrase structures

The eight structures are:

1. `adjective object`
2. `adjective device`
3. `object device`
4. `adjective object device`
5. `adjective surreal_descriptor object`
6. `adjective surreal_descriptor device`
7. `adjective surreal_descriptor object device`
8. `surreal_descriptor adjective object device`

The four two-descriptor structures have a combined 70% selection weight; the four shorter
structures retain a combined 30%. This is probabilistic for every generation rather than a fixed
cycle. The two descriptor pools are disjoint, so a long form cannot repeat the same word twice.

They are declared in `static/js/creation/object-generator.js`. To extend the vocabulary, add a
unique `category,word` row using one of the four documented category identifiers. To change the
grammar, edit `STRUCTURES`; every category in a structure must have at least one CSV entry.
