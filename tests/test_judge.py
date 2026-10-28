import pytest

from grader.judge import ask_judge, parse_verdict
from grader.llm import FakeModel


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("PASS\nIt mentions both.", (True, "It mentions both.")),
        ("FAIL\nIt never mentions writes.", (False, "It never mentions writes.")),
        ("PASS: It mentions both.", (True, "It mentions both.")),
        ("**FAIL** Far too long.", (False, "Far too long.")),
        ("pass", (True, "No reason given")),
    ],
)
def test_parse_verdict(reply, expected):
    assert parse_verdict(reply) == expected


def test_an_unclear_verdict_counts_as_a_fail():
    passed, detail = parse_verdict("The answer is mostly fine.")
    assert not passed
    assert detail == "Unclear verdict from the judge: The answer is mostly fine."


def test_an_empty_reply_counts_as_a_fail():
    assert parse_verdict("") == (False, "The judge gave an empty reply")


def test_the_judge_sees_the_task_the_answer_and_one_item():
    model = FakeModel("FAIL\nIt doesn't mention writes.")
    result = ask_judge(
        model,
        task="Explain what a database index is.",
        answer="An index makes lookups faster.",
        item="Says that indexes slow down writes",
    )

    assert result == (False, "It doesn't mention writes.")
    prompt = model.prompts[0]
    assert "<task>\nExplain what a database index is.\n</task>" in prompt
    assert "<answer>\nAn index makes lookups faster.\n</answer>" in prompt
    assert "<item>\nSays that indexes slow down writes\n</item>" in prompt
