from newsmuncher.services.rewrite_title import final_title


def test_grounded_summary_and_unrelated_title():
    body = 'The mayor sells moon soup. Cats queue outside the town hall.'
    assert final_title(body, 'Mayor sells moon soup') == 'Mayor sells moon soup'
    assert final_title(body, 'Aliens steal a spaceship') == 'The mayor sells moon soup'


def test_caps_and_fallback_use_only_body():
    body = 'The extraordinarily eccentric mayor sells luminous moon soup to bewildered cats.'
    for candidate in (None, 'x' * 61, body, 'A completely unrelated title'):
        title = final_title(body, candidate)
        assert len(title) <= 60
        assert len(title.split()) <= 8
        assert title in body


def test_short_and_single_long_word_bodies():
    assert final_title('Moon soup.', None) == 'Moon soup'
    assert len(final_title('x' * 80, None)) == 60
