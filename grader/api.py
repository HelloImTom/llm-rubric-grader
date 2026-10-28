"""The REST API for managing tasks, marking answers and running evaluations.

Start it from the project folder with:

    uvicorn grader.api:app --reload

then open http://127.0.0.1:8000/docs to try every endpoint in the browser.
"""

import os
import sqlite3
from functools import cache

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from grader import db, reports
from grader.llm import Model, model_from_env
from grader.runner import run_tasks
from grader.scoring import grade_answer, validate_criterion

# Settings such as ANTHROPIC_API_KEY can live in a .env file.
load_dotenv()

app = FastAPI(title="LLM Rubric Grader")


class CriterionIn(BaseModel):
    description: str = Field(min_length=1)
    check_type: str
    params: dict = Field(default_factory=dict)
    points: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def check_it_can_run(self):
        validate_criterion(self.check_type, self.params)
        return self


class TaskIn(BaseModel):
    name: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    criteria: list[CriterionIn] = Field(min_length=1)


class AnswerIn(BaseModel):
    answer: str


class RunIn(BaseModel):
    # Leave this out to run every task.
    task_ids: list[int] | None = None


def get_conn():
    """Give each request its own database connection, closed when it's done."""
    conn = db.connect(os.environ.get("GRADER_DB", "grader.db"))
    try:
        yield conn
    finally:
        conn.close()


# Each model is built once and reused. The tests swap these functions for
# ones that return fake models.
@cache
def get_answer_model() -> Model:
    return model_from_env("ANSWER_MODEL")


@cache
def get_judge_model() -> Model:
    return model_from_env("JUDGE_MODEL")


@app.exception_handler(anthropic.AnthropicError)
def model_api_failed(request: Request, error: anthropic.AnthropicError) -> JSONResponse:
    # 502 says a service this API relies on failed, not that the request was wrong.
    return JSONResponse(status_code=502, content={"detail": f"The model API failed: {error}"})


def find_task(conn: sqlite3.Connection, task_id: int) -> dict:
    task = db.get_task(conn, task_id)
    if task is None:
        raise HTTPException(404, f"No task with id {task_id}")
    return task


@app.post("/tasks", status_code=201)
def create_task(task: TaskIn, conn: sqlite3.Connection = Depends(get_conn)):
    criteria = [criterion.model_dump() for criterion in task.criteria]
    try:
        task_id = db.add_task(conn, task.name, task.prompt, criteria)
    except sqlite3.IntegrityError:
        # The criteria are already validated, so the only rule left to break
        # is the unique task name.
        raise HTTPException(409, f'There is already a task called "{task.name}"') from None
    return db.get_task(conn, task_id)


@app.get("/tasks")
def list_tasks(conn: sqlite3.Connection = Depends(get_conn)):
    return db.list_tasks(conn)


@app.get("/tasks/{task_id}")
def get_task(task_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    return find_task(conn, task_id)


@app.post("/tasks/{task_id}/grade")
def grade_task_answer(
    task_id: int,
    body: AnswerIn,
    conn: sqlite3.Connection = Depends(get_conn),
    judge: Model = Depends(get_judge_model),
):
    """Mark an answer you supply, without saving anything. Useful for testing a rubric."""
    return grade_answer(find_task(conn, task_id), body.answer, judge)


@app.post("/runs", status_code=201)
def start_run(
    body: RunIn,
    conn: sqlite3.Connection = Depends(get_conn),
    model: Model = Depends(get_answer_model),
    judge: Model = Depends(get_judge_model),
):
    """Send tasks to the model, mark the answers and save the run. This can take a while."""
    try:
        run_id = run_tasks(conn, model, judge, body.task_ids)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    return reports.run_report(conn, run_id)


@app.get("/runs")
def list_runs(conn: sqlite3.Connection = Depends(get_conn)):
    return reports.list_runs(conn)


@app.get("/runs/{run_id}")
def get_run(run_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    report = reports.run_report(conn, run_id)
    if report is None:
        raise HTTPException(404, f"No run with id {run_id}")
    return report


@app.get("/runs/{run_id}/answers")
def get_run_answers(run_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    answers = reports.run_answers(conn, run_id)
    if answers is None:
        raise HTTPException(404, f"No run with id {run_id}")
    return answers
