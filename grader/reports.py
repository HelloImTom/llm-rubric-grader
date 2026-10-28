"""Read-only SQL that turns saved results into scores.

A run's score is the average of its task scores, so every task counts
equally however many points its rubric has.
"""

import sqlite3


def run_report(conn: sqlite3.Connection, run_id: int) -> dict | None:
    """Score one run overall, by task and by check type.

    Returns None if there's no run with that id.
    """
    run = conn.execute(
        "SELECT id, model, judge, created_at FROM runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if run is None:
        return None

    overall = conn.execute(
        """
        SELECT COUNT(*) AS tasks, ROUND(AVG(1.0 * earned / possible), 3) AS score
        FROM answer_scores
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()

    by_task = conn.execute(
        """
        SELECT
            tasks.id,
            tasks.name,
            answer_scores.earned,
            answer_scores.possible,
            ROUND(1.0 * answer_scores.earned / answer_scores.possible, 3) AS score
        FROM answer_scores
        JOIN tasks ON tasks.id = answer_scores.task_id
        WHERE answer_scores.run_id = ?
        ORDER BY tasks.id
        """,
        (run_id,),
    ).fetchall()

    # Lowest pass rate first, so the model's weak spots are at the top.
    by_check = conn.execute(
        """
        SELECT
            criteria.check_type,
            COUNT(*) AS checked,
            SUM(results.passed) AS passed,
            ROUND(AVG(results.passed), 3) AS pass_rate
        FROM answers
        JOIN results ON results.answer_id = answers.id
        JOIN criteria ON criteria.id = results.criterion_id
        WHERE answers.run_id = ?
        GROUP BY criteria.check_type
        ORDER BY pass_rate, criteria.check_type
        """,
        (run_id,),
    ).fetchall()

    return {
        **dict(run),
        **dict(overall),
        "by_task": [dict(row) for row in by_task],
        "by_check": [dict(row) for row in by_check],
    }


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    """Every run with its overall score, newest first, so models can be compared."""
    rows = conn.execute(
        """
        SELECT
            runs.id,
            runs.model,
            runs.judge,
            runs.created_at,
            COUNT(answer_scores.answer_id) AS tasks,
            ROUND(AVG(1.0 * answer_scores.earned / answer_scores.possible), 3) AS score
        FROM runs
        LEFT JOIN answer_scores ON answer_scores.run_id = runs.id
        GROUP BY runs.id
        ORDER BY runs.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]
