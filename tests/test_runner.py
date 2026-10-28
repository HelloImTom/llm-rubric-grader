import pytest

from grader import db
from grader.llm import FakeModel
from grader.runner import run_tasks

RUBRIC = [
    {
        "description": "Names the capital",
        "check_type": "includes",
        "params": {"text": "Canberra"},
        "points": 3,
    },
    {
        "description": "Says why Canberra was chosen",
        "check_type": "judge",
        "params": {},
        "points": 2,
    },
]
PROMPT = "What is the capital of Australia, and why was it chosen?"


def count_runs(conn):
    return conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]


def test_a_run_saves_each_answer_with_its_results(conn):
    task_id = db.add_task(conn, "capital", PROMPT, RUBRIC)
    model = FakeModel("Canberra, as a compromise between Sydney and Melbourne.")
    judge = FakeModel("PASS\nIt gives the reason.")

    run_id = run_tasks(conn, model, judge)

    run = conn.execute("SELECT model, judge FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert dict(run) == {"model": "fake", "judge": "fake"}
    answer = conn.execute(
        "SELECT id, task_id, text FROM answers WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert answer["task_id"] == task_id
    assert answer["text"] == "Canberra, as a compromise between Sydney and Melbourne."
    results = conn.execute(
        "SELECT passed, detail FROM results WHERE answer_id = ? ORDER BY criterion_id",
        (answer["id"],),
    ).fetchall()
    assert [tuple(row) for row in results] == [
        (1, 'Contains "Canberra"'),
        (1, "It gives the reason."),
    ]


def test_the_model_is_sent_each_prompt(conn):
    db.add_task(conn, "first", "Question one", RUBRIC[:1])
    db.add_task(conn, "second", "Question two", RUBRIC[:1])
    model = FakeModel("Canberra.")

    run_tasks(conn, model)

    assert model.prompts == ["Question one", "Question two"]


def test_task_ids_pick_which_tasks_run(conn):
    first = db.add_task(conn, "first", "Question one", RUBRIC[:1])
    db.add_task(conn, "second", "Question two", RUBRIC[:1])
    model = FakeModel("Canberra.")

    run_tasks(conn, model, task_ids=[first])

    assert model.prompts == ["Question one"]


def test_an_unknown_task_stops_the_run_before_the_model_is_called(conn):
    model = FakeModel("Canberra.")
    with pytest.raises(ValueError, match="No task with id 99"):
        run_tasks(conn, model, task_ids=[99])
    assert model.prompts == []
    assert count_runs(conn) == 0


def test_a_failure_part_way_through_saves_nothing(conn):
    db.add_task(conn, "capital", PROMPT, RUBRIC)
    # There's no judge model, so marking fails after the model has answered.
    with pytest.raises(ValueError, match="needs a judge model"):
        run_tasks(conn, FakeModel("Canberra."))
    assert count_runs(conn) == 0


def test_there_must_be_something_to_run(conn):
    with pytest.raises(ValueError, match="no tasks"):
        run_tasks(conn, FakeModel("Canberra."))
