import pytest

from grader.llm import FakeModel
from grader.scoring import grade_answer, validate_criterion

TASK = {
    "prompt": "What is the capital of Australia? Answer in one short sentence.",
    "criteria": [
        {
            "description": "Names the capital",
            "check_type": "includes",
            "params": {"text": "Canberra"},
            "points": 3,
        },
        {
            "description": "Ten words or fewer",
            "check_type": "max_words",
            "params": {"limit": 10},
            "points": 1,
        },
    ],
}

JUDGED_TASK = {
    "prompt": "Explain what a database index is in two sentences.",
    "criteria": [
        {
            "description": "Says that indexes slow down writes",
            "check_type": "judge",
            "params": {},
            "points": 2,
        },
    ],
}


def test_full_marks():
    report = grade_answer(TASK, "Canberra.")
    assert report["earned"] == 4
    assert report["possible"] == 4
    assert report["score"] == 1.0


def test_points_are_weighted():
    answer = "The capital of Australia is Canberra, not Sydney as many people assume."
    report = grade_answer(TASK, answer)
    assert report["earned"] == 3
    assert report["score"] == 0.75


def test_each_result_says_what_happened():
    report = grade_answer(TASK, "Sydney.")
    first = report["results"][0]
    assert first["description"] == "Names the capital"
    assert first["passed"] is False
    assert first["detail"] == 'Missing "Canberra"'


def test_a_rubric_needs_criteria():
    with pytest.raises(ValueError, match="at least one criterion"):
        grade_answer({"prompt": "Anything", "criteria": []}, "Anything")


def test_judge_criteria_go_to_the_judge_model():
    judge = FakeModel("PASS\nIt says inserts get slower.")
    answer = "An index speeds up reads but slows down inserts."
    report = grade_answer(JUDGED_TASK, answer, judge)

    assert report["score"] == 1.0
    assert report["results"][0]["detail"] == "It says inserts get slower."
    assert len(judge.prompts) == 1


def test_judge_criteria_need_a_judge_model():
    with pytest.raises(ValueError, match="needs a judge model"):
        grade_answer(JUDGED_TASK, "Any answer")


@pytest.mark.parametrize(
    "check_type, params",
    [
        ("includes", {"text": "Canberra"}),
        ("max_words", {"limit": 120}),
        ("valid_json", {"keys": ["title", "author"]}),
        ("british_spelling", {}),
        ("judge", {}),
    ],
)
def test_validate_criterion_accepts_working_criteria(check_type, params):
    validate_criterion(check_type, params)  # raises if anything is wrong


@pytest.mark.parametrize(
    "check_type, params, message",
    [
        ("spellcheck", {}, "Unknown check type"),
        ("max_words", {}, "Bad params for max_words"),
        ("max_words", {"limit": "ten"}, "Bad params for max_words"),
        ("includes", {"txt": "Canberra"}, "Bad params for includes"),
        ("matches", {"pattern": "("}, "Bad params for matches"),
        ("judge", {"text": "Canberra"}, "take no params"),
    ],
)
def test_validate_criterion_rejects_broken_criteria(check_type, params, message):
    with pytest.raises(ValueError, match=message):
        validate_criterion(check_type, params)
