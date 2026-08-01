from web.routes.hebrew import _diagnostic_answer_matches


def test_diagnostic_answer_matching_handles_pointed_hebrew():
    assert _diagnostic_answer_matches("בְּרֵאשִׁית", "בְּרֵאשִׁ֖ית")
    assert not _diagnostic_answer_matches("ברא", "בְּרֵאשִׁית")
    assert not _diagnostic_answer_matches("שׂ", "שׁ")
    assert not _diagnostic_answer_matches("ב", "בּ")
    assert _diagnostic_answer_matches("ָ", "ָ")


def test_diagnostic_answer_matching_rejects_empty_answers():
    assert not _diagnostic_answer_matches("", "א")
