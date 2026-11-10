from app.retrieval.page_types import classify_page_type


def test_blank_when_both_text_and_rich_text_are_empty():
    assert classify_page_type(5, title=None, text="  \n", rich_text="") == "blank"


def test_first_page_is_title_even_with_content():
    assert classify_page_type(1, title="Anything", text="x", rich_text="x") == "title"


def test_outcomes_keyword():
    assert classify_page_type(2, "Outcomes", "x", "x") == "outcomes"
    assert classify_page_type(2, "Learning Objectives", "x", "x") == "outcomes"


def test_quiz_keywords():
    assert classify_page_type(10, "Quick check", "x", "x") == "quiz"
    assert classify_page_type(10, "Quiz time", "x", "x") == "quiz"
    assert classify_page_type(10, "Exercise 1", "x", "x") == "quiz"


def test_outlook_keywords():
    assert classify_page_type(30, "Looking ahead", "x", "x") == "outlook"
    assert classify_page_type(30, "Next steps", "x", "x") == "outlook"


def test_references_keywords():
    assert classify_page_type(36, "References", "x", "x") == "references"
    assert classify_page_type(36, "Bibliography", "x", "x") == "references"


def test_defaults_to_content():
    assert classify_page_type(8, "Some topic", "body text", "body text") == "content"


def test_no_title_defaults_to_content_when_not_blank():
    assert classify_page_type(8, None, "body text", "body text") == "content"
