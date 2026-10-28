"""Send tasks to a model, mark the answers and save the run."""

import sqlite3

from grader import db
from grader.llm import Model
from grader.scoring import grade_answer


def run_tasks(
    conn: sqlite3.Connection,
    model: Model,
    judge: Model | None = None,
    task_ids: list[int] | None = None,
) -> int:
    """Answer and mark each task, save the run and return its id.

    Every task is run unless task_ids picks out particular ones.
    """
    if task_ids is None:
        task_ids = [task["id"] for task in db.list_tasks(conn)]
    if not task_ids:
        raise ValueError("There are no tasks to run")

    tasks = []
    for task_id in task_ids:
        task = db.get_task(conn, task_id)
        if task is None:
            raise ValueError(f"No task with id {task_id}")
        tasks.append(task)

    # Talk to the model first and write to the database only at the end, in
    # one transaction. A failure part way through then leaves no half-finished
    # run behind, and the database isn't locked while waiting on the API.
    answers = []
    for task in tasks:
        text = model.complete(task["prompt"])
        report = grade_answer(task, text, judge)
        answers.append({"task_id": task["id"], "text": text, "results": report["results"]})

    return db.save_run(conn, model.name, judge.name if judge else None, answers)
