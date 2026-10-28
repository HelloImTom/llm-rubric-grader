"""Load tasks from a JSON file into the database.

    python -m grader.load_tasks                  (loads examples/tasks.json)
    python -m grader.load_tasks my_tasks.json

Tasks already in the database are skipped by name, so it's safe to run more
than once.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

from grader import db
from grader.schemas import TaskIn


def load_tasks(conn: sqlite3.Connection, path: str | Path) -> list[str]:
    """Save each task in the file that isn't already saved, and return their names.

    Every task is checked before any are saved, using the same rules as the
    API, so a mistake anywhere in the file means nothing is added.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks = [TaskIn.model_validate(task) for task in raw]

    saved = {task["name"] for task in db.list_tasks(conn)}
    added = []
    for task in tasks:
        if task.name in saved:
            continue
        criteria = [criterion.model_dump() for criterion in task.criteria]
        db.add_task(conn, task.name, task.prompt, criteria)
        saved.add(task.name)
        added.append(task.name)
    return added


def main() -> None:
    load_dotenv()
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/tasks.json"
    conn = db.connect(os.environ.get("GRADER_DB", "grader.db"))
    try:
        added = load_tasks(conn, path)
    finally:
        conn.close()
    print(f"New tasks added: {', '.join(added) or 'none'}")


if __name__ == "__main__":
    main()
