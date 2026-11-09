# Swear generator vocabulary

The Create-page swear generator reads `newsmuncher/static/data/swear-generator-vocabulary.csv`.
The CSV has two columns: `category,word`. Its supported category identifiers are
`bijv_nw`, `gilles`, `zelfs_nw`, and `handelend`.

To extend it in Excel, add one row for each entry and save/export as UTF-8 CSV. To edit
it as text, quote a word containing a comma or quotation mark according to normal CSV
rules. Blank rows, malformed rows, unknown categories, empty values, and duplicate
values within a category are ignored safely when the page loads. Do not rename the four
category identifiers: the six historical phrase structures refer to them directly.
