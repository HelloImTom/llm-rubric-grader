import anthropic
import pytest
from fastapi.testclient import TestClient

from grader import db
from grader.api import app, get_answer_model, get_conn, get_judge_model
from grader.llm import FakeModel
from grader.schemas import EXAMPLE_TASK

TASK = {
    "name": "capital",
    "prompt": "What is the capital of Australia, and why was it chosen?",
    "criteria": [
        {
            "description": "Names the capital",
            "check_type": "includes",
            "params": {"text": "Canberra"},
            "points": 3,
        },
        {
            "description": "Says why Canberra was chosen",
            "check_type": "judge",
            "points": 2,
        },
    ],
}


@pytest.fixture
def client(tmp_path):
    """An API client wired to a temporary database and fake models."""

    def temporary_db():
        conn = db.connect(tmp_path / "api.db")
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_conn] = temporary_db
    app.dependency_overrides[get_answer_model] = lambda: FakeModel("Canberra, as a compromise.")
    app.dependency_overrides[get_judge_model] = lambda: FakeModel("PASS\nIt gives the reason.")
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_a_task_can_be_created_and_read_back(client):
    response = client.post("/tasks", json=TASK)
    assert response.status_code == 201
    task = response.json()
    assert task["name"] == "capital"
    assert [criterion["check_type"] for criterion in task["criteria"]] == ["includes", "judge"]

    assert client.get(f"/tasks/{task['id']}").json() == task
    assert client.get("/tasks").json() == [
        {"id": task["id"], "name": "capital", "criteria_count": 2, "total_points": 5}
    ]


def test_the_root_sends_you_to_the_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_the_example_on_the_docs_page_works(client):
    assert client.post("/tasks", json=EXAMPLE_TASK).status_code == 201


def test_an_unknown_task_is_a_404(client):
    assert client.get("/tasks/99").status_code == 404


def test_task_names_must_be_unique(client):
    client.post("/tasks", json=TASK)
    assert client.post("/tasks", json=TASK).status_code == 409


@pytest.mark.parametrize(
    "criterion, message",
    [
        ({"description": "x", "check_type": "spellcheck"}, "Unknown check type"),
        ({"description": "x", "check_type": "max_words"}, "Bad params for max_words"),
        (
            {"description": "x", "check_type": "matches", "params": {"pattern": "("}},
            "Bad params for matches",
        ),
        (
            {"description": "x", "check_type": "judge", "params": {"text": "y"}},
            "take no params",
        ),
        (
            {"description": "x", "check_type": "includes", "params": {"text": "y"}, "points": 0},
            "greater than 0",
        ),
    ],
)
def test_a_broken_criterion_is_rejected_before_anything_is_saved(client, criterion, message):
    response = client.post("/tasks", json={**TASK, "criteria": [criterion]})
    assert response.status_code == 422
    assert message in response.text
    assert client.get("/tasks").json() == []


def test_a_task_needs_at_least_one_criterion(client):
    assert client.post("/tasks", json={**TASK, "criteria": []}).status_code == 422


def test_grade_marks_an_answer_without_saving_it(client):
    task_id = client.post("/tasks", json=TASK).json()["id"]

    response = client.post(f"/tasks/{task_id}/grade", json={"answer": "It's Sydney."})

    assert response.status_code == 200
    # Only the judge criterion passes, and the fake judge passes everything.
    assert response.json()["earned"] == 2
    assert client.get("/runs").json() == []


def test_a_run_can_be_started_and_read_back(client):
    client.post("/tasks", json=TASK)

    response = client.post("/runs", json={})

    assert response.status_code == 201
    run = response.json()
    assert run["model"] == "fake"
    assert run["score"] == 1.0
    assert client.get("/runs").json()[0]["id"] == run["id"]
    assert client.get(f"/runs/{run['id']}").json() == run

    answers = client.get(f"/runs/{run['id']}/answers").json()
    assert answers[0]["text"] == "Canberra, as a compromise."
    assert [result["passed"] for result in answers[0]["results"]] == [True, True]


def test_running_an_unknown_task_is_a_400(client):
    response = client.post("/runs", json={"task_ids": [99]})
    assert response.status_code == 400
    assert "No task with id 99" in response.text


def test_an_unknown_run_is_a_404(client):
    assert client.get("/runs/99").status_code == 404
    assert client.get("/runs/99/answers").status_code == 404


def test_a_model_api_failure_is_a_502(client):
    class BrokenModel(FakeModel):
        def complete(self, prompt):
            raise anthropic.AnthropicError("the API is down")

    client.post("/tasks", json=TASK)
    app.dependency_overrides[get_answer_model] = lambda: BrokenModel("")

    response = client.post("/runs", json={})

    assert response.status_code == 502
    assert "the API is down" in response.text
