from evaluation.metrics import content_word_recall, word_error_rate


def test_word_error_rate_is_zero_for_matching_reference():
    assert word_error_rate("Water moves.", "Water moves.") == 0


def test_word_error_rate_counts_edits_and_handles_empty_reference():
    assert word_error_rate("Water moves.", "Water flows.") == 0.5
    assert word_error_rate("", "Added.") == 1


def test_content_word_recall_measures_source_overlap():
    assert content_word_recall("ATP is produced.", "ATP is released.") == 2 / 3
