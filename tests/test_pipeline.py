import spacy
import pytest

from nlp.pipeline import improve_notes


class FakeRewriter:
    def __init__(self, outputs=None):
        self.inputs = []
        self.outputs = outputs or []

    def count_tokens(self, text):
        return len(text.split())

    def rewrite(self, text, max_new_tokens):
        self.inputs.append(text)
        if self.outputs:
            return self.outputs.pop(0)
        return text


def make_nlp():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def test_improve_notes_rewrites_and_flags_changed_formula():
    rewriter = FakeRewriter(["Force equals mass times acceleration: F = mb."])

    result = improve_notes(
        "Force equals mass times acceleration: F=ma.",
        make_nlp(),
        rewriter,
    )

    assert result.improved == "Force equals mass times acceleration: F = mb."
    assert result.sentence_count == 1
    assert any("f=ma" in warning.casefold() for warning in result.warnings)


def test_paragraph_boundaries_are_preserved():
    rewriter = FakeRewriter()

    result = improve_notes(
        "First idea.\n\nSecond idea.",
        make_nlp(),
        rewriter,
    )

    assert rewriter.inputs == ["First idea.", "Second idea."]
    assert result.improved == "First idea.\n\nSecond idea."


def test_repeated_sentences_are_preserved_and_flagged():
    text = "The result is important. The result is important."
    result = improve_notes(text, make_nlp(), FakeRewriter())
    assert result.improved == text
    assert any("Repeated sentences remain" in warning for warning in result.warnings)


def test_long_paragraph_is_chunked_without_losing_sentence_order():
    text = "One short sentence. Two short sentence. Three short sentence."
    rewriter = FakeRewriter()
    result = improve_notes(
        text, make_nlp(), rewriter, max_input_tokens=5
    )
    assert rewriter.inputs == ["One short sentence.", "Two short sentence.", "Three short sentence."]
    assert result.improved == text


def test_formula_spacing_does_not_trigger_review_warning():
    result = improve_notes(
        "Force is F=ma.",
        make_nlp(),
        FakeRewriter(["Force is F = ma."]),
    )

    assert not any("formula" in warning.casefold() for warning in result.warnings)


def test_missing_recognized_technical_term_is_flagged():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns([{"label": "PRODUCT", "pattern": "ATP"}])

    result = improve_notes(
        "ATP is produced.",
        nlp,
        FakeRewriter(["Energy is produced."]),
    )

    assert any("atp" in warning.casefold() for warning in result.warnings)


def test_oversized_sentence_fails_instead_of_truncating():
    with pytest.raises(ValueError, match="exceeds the local model input limit"):
        improve_notes(
            "one two three four.",
            make_nlp(),
            FakeRewriter(),
            max_input_tokens=2,
        )


def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="Enter or upload"):
        improve_notes("", make_nlp(), FakeRewriter())


def test_improve_notes_without_model_dir_argument():
    """Regression: improve_notes must not require a model_dir keyword argument."""
    rewriter = FakeRewriter(["The lab timetable needs revision."])
    result = improve_notes(
        "the lab timetable need revision.",
        make_nlp(),
        rewriter,
    )
    assert result.improved == "The lab timetable needs revision."
    assert result.sentence_count == 1
