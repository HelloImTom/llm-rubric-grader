import sqlite3

import pytest

from grader import db

CRITERIA = [
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


def test_a_task_comes_back_with_its_rubric(conn):
    task_id = db.add_task(conn, "capital", "What is the capital of Australia?", CRITERIA)
    task = db.get_task(conn, task_id)

    assert task["name"] == "capital"
    assert task["prompt"] == "What is the capital of Australia?"
    descriptions = [criterion["description"] for criterion in task["criteria"]]
    assert descriptions == ["Names the capital", "Ten words or fewer"]
    # params go in as JSON text and come back out as a dict
    assert task["criteria"][1]["params"] == {"limit": 10}


def test_an_unknown_task_is_none(conn):
    assert db.get_task(conn, 999) is None


def test_list_tasks_totals_each_rubric(conn):
    db.add_task(conn, "capital", "What is the capital of Australia?", CRITERIA)
    db.add_task(conn, "draft", "A task with no rubric yet", [])

    assert db.list_tasks(conn) == [
        {"id": 1, "name": "capital", "criteria_count": 2, "total_points": 4},
        {"id": 2, "name": "draft", "criteria_count": 0, "total_points": 0},
    ]


def test_task_names_must_be_unique(conn):
    db.add_task(conn, "capital", "First version", CRITERIA)
    with pytest.raises(sqlite3.IntegrityError):
        db.add_task(conn, "capital", "Second version", CRITERIA)


def test_a_rejected_criterion_rolls_back_the_whole_task(conn):
    zero_points = [{**CRITERIA[0], "points": 0}]  # breaks CHECK (points > 0)
    with pytest.raises(sqlite3.IntegrityError):
        db.add_task(conn, "capital", "What is the capital of Australia?", zero_points)
    assert db.list_tasks(conn) == []


def test_deleting_a_task_deletes_its_criteria(conn):
    task_id = db.add_task(conn, "capital", "What is the capital of Australia?", CRITERIA)
    with conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    remaining = conn.execute("SELECT COUNT(*) FROM criteria").fetchone()[0]
    assert remaining == 0
