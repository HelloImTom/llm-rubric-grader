"""SQLite storage for the grader."""

import json
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the database, creating the tables first if they don't exist."""
    conn = sqlite3.connect(path)
    # Lets rows be read by column name, like a dict.
    conn.row_factory = sqlite3.Row
    # SQLite only enforces foreign keys when asked, once per connection.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def add_task(
    conn: sqlite3.Connection, name: str, prompt: str, criteria: list[dict]
) -> int:
    """Save a task and its rubric, and return the new task's id.

    Everything happens in one transaction, so if any criterion is rejected
    the task isn't saved either.
    """
    with conn:
        cursor = conn.execute(
            "INSERT INTO tasks (name, prompt) VALUES (?, ?)",
            (name, prompt),
        )
        task_id = cursor.lastrowid
        conn.executemany(
            """
            INSERT INTO criteria (task_id, description, check_type, params, points)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    task_id,
                    criterion["description"],
                    criterion["check_type"],
                    json.dumps(criterion["params"]),
                    criterion["points"],
                )
                for criterion in criteria
            ],
        )
    return task_id


def get_task(conn: sqlite3.Connection, task_id: int) -> dict | None:
    """Return a task with its rubric, or None if there's no task with that id."""
    task = conn.execute(
        "SELECT id, name, prompt FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if task is None:
        return None

    rows = conn.execute(
        """
        SELECT id, description, check_type, params, points
        FROM criteria
        WHERE task_id = ?
        ORDER BY id
        """,
        (task_id,),
    ).fetchall()
    criteria = [{**dict(row), "params": json.loads(row["params"])} for row in rows]
    return {**dict(task), "criteria": criteria}


def list_tasks(conn: sqlite3.Connection) -> list[dict]:
    """List every task with the size of its rubric and the points available."""
    rows = conn.execute(
        """
        SELECT
            tasks.id,
            tasks.name,
            COUNT(criteria.id) AS criteria_count,
            COALESCE(SUM(criteria.points), 0) AS total_points
        FROM tasks
        LEFT JOIN criteria ON criteria.task_id = tasks.id
        GROUP BY tasks.id
        ORDER BY tasks.id
        """
    ).fetchall()
    return [dict(row) for row in rows]
