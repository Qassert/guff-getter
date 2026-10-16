"""Focused, provider-free tests for the optional comedy editor."""
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from newsmuncher.config import comedy_editor_enabled, comedy_editor_model
from newsmuncher.services.comedy_audit import build_audit_record
from newsmuncher.utils.clean_data import comedy_editor_pass, comedy_editor_word_target


def _mock_openai(payload=None, error=None):
    client = Mock()
    if error:
        client.responses.create.side_effect = error
    else:
        client.responses.create.return_value = SimpleNamespace(
            status="completed", output_text=json.dumps(payload))
    context = MagicMock()
    context.__enter__.return_value = client
    mocked = MagicMock(return_value=context)
    return mocked, client


def test_editor_flag_defaults_off_and_model_is_configurable(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_COMEDY_EDITOR", raising=False)
    monkeypatch.delenv("NEWSMUNCHER_COMEDY_EDITOR_MODEL", raising=False)
    assert comedy_editor_enabled() is False
    assert comedy_editor_model() == "gpt-5.6-luna"
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_EDITOR", "evaluation")
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_EDITOR_MODEL", "test-editor")
    assert comedy_editor_enabled() is True
    assert comedy_editor_model() == "test-editor"


def test_editor_receives_source_and_first_pass(monkeypatch):
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_EDITOR_MODEL", "test-editor")
    mocked, client = _mock_openai({"title": "Tighter otter", "extract": "An otter exploded."})
    source = {"title": "Council meets", "description": "A short report", "extract": "They voted."}
    first = {"crazyReplacement1Title": "Long otter", "crazyReplacement1Extract": "An otter exploded at unnecessary length."}
    with patch("newsmuncher.utils.clean_data.OpenAI", mocked):
        result = comedy_editor_pass(source, first)
    supplied = json.loads(client.responses.create.call_args.kwargs["input"][1]["content"])
    instruction = client.responses.create.call_args.kwargs["input"][0]["content"]
    assert "ARTICLE BODY contains 6 words" in instruction
    assert "approximately 3 words" in instruction
    assert "3-3 words" in instruction
    assert "excludes the title" in instruction
    assert "repetitive concepts, unnecessary explanations, weaker jokes" in instruction
    assert "remove them for repetition or weakness, not to meet a category count" in instruction
    assert "readily imaginable absurd situations" in instruction
    assert "strongest one or two animal jokes" not in instruction
    assert "derived only from the final edited article" in instruction
    assert supplied == {
        "original_source_article": source,
        "first_pass_comedy_rewrite": {
            "title": first["crazyReplacement1Title"],
            "extract": first["crazyReplacement1Extract"],
        },
    }
    assert client.responses.create.call_args.kwargs["model"] == "test-editor"
    assert result["crazyReplacement1Extract"] == "An otter exploded."
def test_editor_calculates_explicit_body_target_and_short_input():
    target = comedy_editor_word_target("word " * 136)
    assert target == {
        "first_pass_word_count": 136,
        "target_word_count": 68,
        "target_min_word_count": 61,
        "target_max_word_count": 75,
    }
    assert comedy_editor_word_target("Nonsense!") == {
        "first_pass_word_count": 1,
        "target_word_count": 1,
        "target_min_word_count": 1,
        "target_max_word_count": 1,
    }


def test_editor_failure_returns_none_for_caller_fallback():
    mocked, _ = _mock_openai(error=TimeoutError("offline"))
    first = {"crazyReplacement1Title": "Original", "crazyReplacement1Extract": "Original body."}
    with patch("newsmuncher.utils.clean_data.OpenAI", mocked):
        assert comedy_editor_pass({"title": "Source"}, first) is None


def test_editor_keeps_edited_article_when_only_title_is_invalid():
    mocked, _ = _mock_openai({
        "title": " ",
        "extract": "Professor Marmalade detonated the parliamentary kettle. The walls applauded.",
    })
    first = {"crazyReplacement1Title": "Old title",
             "crazyReplacement1Extract": "A much longer old body."}
    with patch("newsmuncher.utils.clean_data.OpenAI", mocked):
        result = comedy_editor_pass({"title": "Unrelated source"}, first)
    assert result["crazyReplacement1Extract"].startswith("Professor Marmalade")
    assert result["crazyReplacement1Title"] == (
        "Professor Marmalade detonated the parliamentary kettle.")


def test_route_uses_editor_final_for_persistence_and_exclusions():
    import test_image_generation as fixtures
    fixture = fixtures.ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        first = dict(fixture.result)
        edited = {**first, "crazyReplacement1Title": "Edited title",
                  "crazyReplacement1Extract": "Edited final otter."}
        routes.prepare_prompt.return_value = {
            "full_prompt": "masked", "preprocessing": None,
            "contenders": {"nouns": ["otter"]},
        }
        routes.send_prompt.return_value = {"title": "first", "extract": "first body"}
        routes.format_shizzalise_result.return_value = first
        routes.comedy_editor_pass.return_value = edited
        memory = MagicMock()
        memory.exclusions.return_value = set()
        memory.reserve.return_value = True
        routes.NounExclusionMemory = MagicMock(return_value=memory)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.extract_final_entries = MagicMock(return_value={"noun_identity:otter"})
        with patch.dict(os.environ, {
            "NEWSMUNCHER_COMEDY_EDITOR": "evaluation",
            "NEWSMUNCHER_NOUN_EXCLUSION": "evaluation",
        }):
            result = routes.shizzalise_data(
                routes.ShizzRequest(title="Source title", description="", extract="Source body"),
                "alice", "alice")
        routes.copy_edit_pass.assert_not_called()
        assert routes.comedy_editor_pass.call_args.args[1] == first
        assert result["crazyReplacement1Extract"] == "Edited final otter."
        assert routes.extract_final_entries.call_args.kwargs["body"] == "Edited final otter."
        memory.complete.assert_called_once()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_audit_records_compact_editor_measurements():
    record = build_audit_record(
        rewrite_id="r", source={}, result={}, comedy_editor_context={
            "enabled": True, "invoked": True, "model": "test-editor",
            "succeeded": True, "fell_back": False,
            "first_pass_word_count": 100, "final_word_count": 52,
            "target_word_count": 50, "target_min_word_count": 45,
            "target_max_word_count": 55, "achieved_word_count": 52,
            "percentage_reduction": 48.0,
        })
    assert record["comedy_editor"] == {
        "enabled": True, "invoked": True, "model": "test-editor",
        "succeeded": True, "fell_back": False,
        "first_pass_word_count": 100, "final_word_count": 52,
        "target_word_count": 50, "target_min_word_count": 45,
        "target_max_word_count": 55, "achieved_word_count": 52,
        "percentage_reduction": 48.0,
    }
