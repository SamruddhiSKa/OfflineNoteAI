import spacy

from nlp.preprocessing import preprocess_notes


def test_preprocessing_preserves_paragraphs_and_segments_sentences():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    result = preprocess_notes(
        "  First rough sentence. Second sentence!\r\n\r\nAnother paragraph.  ", nlp
    )

    assert result.paragraphs == (
        ("First rough sentence.", "Second sentence!"),
        ("Another paragraph.",),
    )
    assert len(result.sentences) == 3
