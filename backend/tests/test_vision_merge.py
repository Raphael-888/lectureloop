from app.retrieval.vision_merge import merge_page_elements


def test_drops_slide_number_and_captures_it():
    elements = [
        {"type": "text", "order": 1, "content": "7"},
        {"type": "heading", "order": 2, "content": "A heading"},
        {"type": "text", "order": 3, "content": "Some body text."},
    ]

    result = merge_page_elements(elements)

    assert result.slide_no == 7
    assert "7" not in result.rich_text.split("\n")[0]
    assert result.rich_text == "A heading\nSome body text."


def test_inline_formula_joins_surrounding_text_with_dollar_signs():
    elements = [
        {"type": "text", "order": 1, "content": "Given "},
        {"type": "inline_formula", "order": 2, "latex": "x \\in \\mathbb{R}"},
        {"type": "text", "order": 3, "content": ", define the loss."},
    ]

    result = merge_page_elements(elements)

    assert result.rich_text == "Given $x \\in \\mathbb{R}$, define the loss."
    assert "x \\in \\mathbb{R}" in result.formulas


def test_adjacent_text_without_separator_still_gets_a_space():
    elements = [
        {"type": "text", "order": 1, "content": "is linear in"},
        {"type": "inline_formula", "order": 2, "latex": "w"},
        {"type": "text", "order": 3, "content": "If you expand it"},
    ]

    result = merge_page_elements(elements)

    assert result.rich_text == "is linear in $w$ If you expand it"


def test_standalone_formula_gets_its_own_block_line():
    elements = [
        {"type": "heading", "order": 1, "content": "Risk"},
        {"type": "formula", "order": 2, "latex": "J = \\frac{1}{n}", "uncertain": []},
        {"type": "text", "order": 3, "content": "after the formula"},
    ]

    result = merge_page_elements(elements)

    assert result.rich_text.splitlines() == [
        "Risk",
        "$$J = \\frac{1}{n}$$",
        "after the formula",
    ]
    assert result.formulas == ["J = \\frac{1}{n}"]


def test_figure_and_code_blocks():
    elements = [
        {"type": "figure", "order": 1, "description": "A scatter plot"},
        {"type": "code_marker", "order": 2, "content": "Code", "visibility": "collapsed"},
        {"type": "code", "order": 3, "content": "print(1)"},
    ]

    result = merge_page_elements(elements)

    assert result.rich_text == "[Figure: A scatter plot]\n```\nprint(1)\n```"
    assert result.figures == ["A scatter plot"]


def test_first_heading_becomes_title_later_headings_stay_inline():
    elements = [
        {"type": "heading", "order": 1, "content": "Main title"},
        {"type": "text", "order": 2, "content": "intro"},
        {"type": "heading", "order": 3, "content": "Subsection"},
    ]

    result = merge_page_elements(elements)

    assert result.title == "Main title"
    assert "Subsection" in result.rich_text.splitlines()


def test_uncertain_fields_are_flattened_across_elements():
    elements = [
        {
            "type": "formula",
            "order": 1,
            "latex": "a = b",
            "uncertain": ["symbol may be c"],
        },
        {
            "type": "figure",
            "order": 2,
            "description": "a chart",
            "uncertain": ["axis label unclear"],
        },
    ]

    result = merge_page_elements(elements)

    assert result.uncertain == ["symbol may be c", "axis label unclear"]


def test_empty_elements_produce_empty_content():
    result = merge_page_elements([])

    assert result.rich_text == ""
    assert result.title is None
    assert result.slide_no is None
