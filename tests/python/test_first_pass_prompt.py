from pathlib import Path

import pytest

from newsmuncher.config import (
    NARRATIVE_SKELETON_PROMPT_ENV, NARRATIVE_SKELETON_PROMPT_FILE,
    PROMPT_FILE, first_pass_prompt_file,
)


def test_narrative_skeleton_prompt_is_default_off(monkeypatch):
    monkeypatch.delenv(NARRATIVE_SKELETON_PROMPT_ENV, raising=False)
    assert first_pass_prompt_file() == PROMPT_FILE


def test_narrative_skeleton_prompt_can_be_selected_for_evaluation(monkeypatch):
    monkeypatch.setenv(NARRATIVE_SKELETON_PROMPT_ENV, "evaluation")
    assert first_pass_prompt_file() == NARRATIVE_SKELETON_PROMPT_FILE
    prompt = Path(first_pass_prompt_file()).read_text(encoding="utf-8")
    assert "NARRATIVE SKELETON — HARD RULE" in prompt
    assert "No new career, transaction, action, relationship or storyline" in prompt


@pytest.mark.parametrize("path", [PROMPT_FILE, NARRATIVE_SKELETON_PROMPT_FILE])
def test_modern_prompts_treat_animal_concepts_as_optional_alternatives(path):
    prompt = Path(path).read_text(encoding="utf-8")
    assert "optional alternatives, not a checklist" in prompt
    assert "strongest, clearest comic situation" in prompt
    assert "readers can readily picture" in prompt
    assert "use zero, one or two" not in prompt
    assert "Use at least one supplied animal" not in prompt


def test_narrative_skeleton_prompt_rejects_unknown_modes(monkeypatch):
    monkeypatch.setenv(NARRATIVE_SKELETON_PROMPT_ENV, "yes")
    with pytest.raises(ValueError, match=NARRATIVE_SKELETON_PROMPT_ENV):
        first_pass_prompt_file()
