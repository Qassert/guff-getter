import pytest

from newsmuncher.services.rewrite_title import final_title


def test_independently_written_headline_is_not_replaced_by_body_prefix():
    body = 'The mayor sells moon soup. Cats queue outside the town hall.'
    title = 'Bewildered Cats Queue Overnight After Moon Soup Mayor Opens Town Hall Café'
    assert final_title(body, title) == title
    assert not title.startswith('The mayor sells moon soup')


def test_twelve_to_eighteen_word_headlines_are_preserved():
    for count in (12, 15, 18):
        title = ' '.join(f'word{i}' for i in range(count))
        assert final_title('Unrelated body opening words.', title) == title


def test_headline_has_hard_eighteen_word_cap_without_body_fallback():
    words = [f'word{i}' for i in range(25)]
    assert final_title('Body prefix must never become the title.', ' '.join(words)).split() == words[:18]


def test_missing_ai_title_fails_instead_of_using_body_prefix():
    with pytest.raises(ValueError):
        final_title('The first six body words must not be used.', None)
