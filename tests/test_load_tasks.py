import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from grader import db
from grader.load_tasks import load_tasks

EXAMPLES = Path(__file__).parent.parent / "examples" / "tasks.json"


def test_every_example_task_loads(conn):
    names = [task["name"] for task in json.loads(EXAMPLES.read_text(encoding="utf-8"))]
    assert load_tasks(conn, EXAMPLES) == names
    assert [task["name"] for task in db.list_tasks(conn)] == names


def test_tasks_already_saved_are_skipped(conn):
    load_tasks(conn, EXAMPLES)
    assert load_tasks(conn, EXAMPLES) == []


def test_one_bad_task_means_nothing_is_added(conn, tmp_path):
    good = {
        "name": "greeting",
        "prompt": "Say hello.",
        "criteria": [{"description": "Short", "check_type": "max_words", "params": {"limit": 5}}],
    }
    bad = {
        "name": "broken",
        "prompt": "Say hello.",
        "criteria": [{"description": "Spelt right", "check_type": "spellcheck"}],
    }
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps([good, bad]), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_tasks(conn, path)
    assert db.list_tasks(conn) == []
