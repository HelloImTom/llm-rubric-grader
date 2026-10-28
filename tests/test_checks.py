import pytest

from grader.checks import (
    EM_DASH,
    british_spelling,
    count_words,
    excludes,
    includes,
    matches,
    max_words,
    min_words,
    no_ai_phrases,
    no_em_dashes,
    run_check,
    valid_json,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello world", 2),
        ("Don't count this twice", 4),
        ("A well-known fact", 3),
        ("- first point\n- second point", 4),
        ("", 0),
    ],
)
def test_count_words(text, expected):
    assert count_words(text) == expected


def test_includes_ignores_case():
    assert includes("The capital is Canberra.", "canberra") == (True, 'Contains "canberra"')


def test_includes_names_what_is_missing():
    assert includes("The capital is Sydney.", "Canberra") == (False, 'Missing "Canberra"')


def test_excludes():
    passed, detail = excludes("Great question! The answer is 42.", "great question")
    assert not passed
    assert detail == 'Contains "great question"'

    passed, _ = excludes("The answer is 42.", "great question")
    assert passed


def test_word_limits_include_the_boundary():
    answer = "one two three"
    assert max_words(answer, limit=3) == (True, "3 words (maximum 3)")
    assert min_words(answer, limit=3) == (True, "3 words (minimum 3)")
    assert max_words(answer, limit=2)[0] is False
    assert min_words(answer, limit=4)[0] is False


def test_matches_uses_regular_expressions():
    letter = "Dear Ms Patel,\nThank you for your order."
    assert matches(letter, r"^Dear ") == (True, 'Matches "^Dear "')
    assert matches("Hi there,", r"^Dear ")[0] is False


def test_valid_json_accepts_an_object_with_the_right_keys():
    answer = '{"title": "Pride and Prejudice", "author": "Jane Austen", "year": 1813}'
    assert valid_json(answer, keys=["title", "author", "year"]) == (True, "Valid JSON")


def test_valid_json_lists_missing_keys():
    passed, detail = valid_json('{"title": "Emma"}', keys=["title", "author", "year"])
    assert not passed
    assert detail == "Missing keys: author, year"


def test_valid_json_rejects_code_fences():
    # Models often wrap JSON in a markdown fence even when asked not to.
    passed, detail = valid_json('```json\n{"title": "Emma"}\n```')
    assert not passed
    assert detail.startswith("Not valid JSON")


def test_valid_json_needs_an_object_when_keys_are_given():
    assert valid_json('["title"]', keys=["title"]) == (False, "Expected a JSON object")


def test_british_spelling_suggests_fixes():
    passed, detail = british_spelling("My favorite color is gray.")
    assert not passed
    assert detail == "American spellings: color (colour), favorite (favourite), gray (grey)"


def test_british_spelling_passes_british_text():
    assert british_spelling("My favourite colour is grey.") == (True, "No American spellings")


def test_british_spelling_matches_whole_words_only():
    # "Honorary" has no u in British English either, so the entry for
    # "honor" must not catch it.
    assert british_spelling("She was given an honorary degree.")[0] is True


def test_no_em_dashes():
    assert no_em_dashes("Hyphens - like these - are fine.") == (True, "No em dashes")

    passed, detail = no_em_dashes(f"It works{EM_DASH}mostly{EM_DASH}well.")
    assert not passed
    assert detail == "Em dashes found: 2"


def test_no_ai_phrases_lists_what_it_finds():
    passed, detail = no_ai_phrases("Let's delve into it. I hope this helps!")
    assert not passed
    assert detail == "Stock phrases: delve, I hope this helps"


def test_no_ai_phrases_handles_curly_apostrophes():
    passed, detail = no_ai_phrases("It\u2019s important to note that indexes take up space.")
    assert not passed
    assert "It's important to note" in detail


def test_no_ai_phrases_passes_plain_writing():
    passed, _ = no_ai_phrases("Indexes speed up reads but slow down writes.")
    assert passed


def test_run_check_passes_params_to_the_check():
    assert run_check("max_words", "one two", {"limit": 5}) == (True, "2 words (maximum 5)")


def test_run_check_rejects_unknown_types():
    with pytest.raises(ValueError, match="Unknown check type"):
        run_check("spellcheck", "anything", {})
