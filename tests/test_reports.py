from grader import db, reports
from grader.llm import FakeModel
from grader.runner import run_tasks

# Two tasks with rubrics of different sizes, so how scores are averaged matters.
CAPITAL = [
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
APOLOGY = [
    {
        "description": "Says sorry",
        "check_type": "includes",
        "params": {"text": "sorry"},
        "points": 1,
    },
    {
        "description": "No em dashes",
        "check_type": "no_em_dashes",
        "params": {},
        "points": 1,
    },
]


def add_tasks(conn):
    db.add_task(conn, "capital", "What is the capital of Australia?", CAPITAL)
    db.add_task(conn, "apology", "Apologise for a late delivery.", APOLOGY)


def test_run_report_scores_overall_by_task_and_by_check(conn):
    add_tasks(conn)
    # The same reply to both tasks: right for the first, half right for the second.
    run_id = run_tasks(conn, FakeModel("Canberra."))

    report = reports.run_report(conn, run_id)

    assert report["model"] == "fake"
    assert report["by_task"] == [
        {"id": 1, "name": "capital", "earned": 4, "possible": 4, "score": 1.0},
        {"id": 2, "name": "apology", "earned": 1, "possible": 2, "score": 0.5},
    ]
    # Each task counts equally: (1.0 + 0.5) / 2, not 5 points out of 6.
    assert report["tasks"] == 2
    assert report["score"] == 0.75
    assert report["by_check"] == [
        {"check_type": "includes", "checked": 2, "passed": 1, "pass_rate": 0.5},
        {"check_type": "max_words", "checked": 1, "passed": 1, "pass_rate": 1.0},
        {"check_type": "no_em_dashes", "checked": 1, "passed": 1, "pass_rate": 1.0},
    ]


def test_an_unknown_run_has_no_report(conn):
    assert reports.run_report(conn, 99) is None


def test_list_runs_puts_the_newest_first(conn):
    add_tasks(conn)
    first = FakeModel("Canberra.")
    first.name = "model-a"
    second = FakeModel("Sorry, it's Canberra.")
    second.name = "model-b"
    run_tasks(conn, first)
    run_tasks(conn, second)

    summary = [(run["model"], run["tasks"], run["score"]) for run in reports.list_runs(conn)]
    assert summary == [("model-b", 2, 1.0), ("model-a", 2, 0.75)]
