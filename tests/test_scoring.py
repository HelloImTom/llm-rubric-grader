import pytest

from grader.scoring import grade_answer

RUBRIC = [
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
]


def test_full_marks():
    report = grade_answer("Canberra.", RUBRIC)
    assert report["earned"] == 4
    assert report["possible"] == 4
    assert report["score"] == 1.0


def test_points_are_weighted():
    answer = "The capital of Australia is Canberra, not Sydney as many people assume."
    report = grade_answer(answer, RUBRIC)
    assert report["earned"] == 3
    assert report["score"] == 0.75


def test_each_result_says_what_happened():
    report = grade_answer("Sydney.", RUBRIC)
    first = report["results"][0]
    assert first["description"] == "Names the capital"
    assert first["passed"] is False
    assert first["detail"] == 'Missing "Canberra"'


def test_a_rubric_needs_criteria():
    with pytest.raises(ValueError, match="at least one criterion"):
        grade_answer("Anything", [])
