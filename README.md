# LLM Rubric Grader

Sends prompts to a language model and marks each answer against a rubric, one criterion at a time, the way an examiner works through a mark scheme.

Some criteria are plain rules: a word limit, a phrase that must appear, valid JSON, British spelling, no em dashes. Others need judgement, such as "explains the trade-off", so a second model marks them PASS or FAIL and gives its reason. Every mark is stored in SQLite with that reason, and SQL reports show where a model does well and where it falls down.

Built with Python, FastAPI, SQLite, pytest and Anthropic's Claude API.

## What a result looks like

The prompt: *Explain what a database index is to a junior developer, in under 120 words. Use British English.*

Claude Opus 5.5 answered, and the rubric marked it like this:

| Criterion | Check | Points | Result |
|---|---|---|---|
| Under 120 words | `max_words` | 1 | Pass: 118 words (maximum 120) |
| British spelling | `british_spelling` | 1 | Pass |
| No em dashes | `no_em_dashes` | 1 | Pass |
| No stock AI phrases | `no_ai_phrases` | 1 | Pass |
| Says that indexes slow down writes or take up extra space | `judge` | 2 | Pass: the answer says indexes "take up storage and slow down inserts, updates and deletes" |

Score: 6 out of 6.

## Getting started

You'll need Python 3.11 or later.

```
git clone https://github.com/YOUR-USERNAME/llm-rubric-grader.git
cd llm-rubric-grader
python -m venv .venv
```

Activate the virtual environment (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS and Linux), then install the dependencies:

```
pip install -r requirements.txt
```

## Running the tests

```
pytest
```

The tests use a fake model and a temporary database, so they need no API key and cost nothing.

## Running an evaluation

1. Copy `.env.example` to `.env` and put your Anthropic API key after `ANTHROPIC_API_KEY=`. Git ignores `.env`, so the key stays out of the repository.
2. Check the key works: `python -m grader.ask "What is the capital of Australia?"`
3. Load the example tasks: `python -m grader.load_tasks`
4. Start the API: `uvicorn grader.api:app`
5. Open http://127.0.0.1:8000/docs. Under `POST /runs`, click **Try it out**, then **Execute**. When it finishes, the report appears under **Server response**.
6. To see each answer with every mark and its reason, use `GET /runs/{run_id}/answers` with the run's id.

The five example tasks make eight calls to the model (one answer per task, plus one per judge criterion), which costs a few cents with Claude Opus 5.5. To change models, set `ANSWER_MODEL` and `JUDGE_MODEL` in `.env`; `claude-haiku-5-5` is far cheaper.

## The API

| Method and path | What it does |
|---|---|
| `POST /tasks` | Save a task and its rubric |
| `GET /tasks` | List tasks |
| `GET /tasks/{id}` | Show one task and its rubric |
| `POST /tasks/{id}/grade` | Mark an answer you supply, without saving it |
| `POST /runs` | Send tasks to the model, mark the answers and save the run |
| `GET /runs` | List runs with their overall scores, newest first |
| `GET /runs/{id}` | A run's scores: overall, by task and by check type |
| `GET /runs/{id}/answers` | Each answer in a run, with every mark and its reason |

## Writing a rubric

A task is a prompt plus a list of criteria. Each criterion has a description, a check type, settings for that check (`params`) and the points it's worth. [examples/tasks.json](examples/tasks.json) has five worked examples.

| Check type | Params | Passes when the answer |
|---|---|---|
| `includes` | `text` | contains the text, ignoring case |
| `excludes` | `text` | doesn't contain the text |
| `min_words`, `max_words` | `limit` | has at least, or at most, that many words |
| `matches` | `pattern` | matches the regular expression |
| `valid_json` | `keys` (optional) | is valid JSON, and an object with those keys if any are given |
| `british_spelling` | none | uses none of the American spellings on a built-in list |
| `no_em_dashes` | none | contains no em dashes |
| `no_ai_phrases` | none | avoids stock phrases such as "delve" |
| `judge` | none | meets the description, as decided by the judge model |

Rubrics are checked when they're saved, so an unknown check type, a misspelt param or a broken regular expression is rejected straight away.

## How it works

| File | Job |
|---|---|
| `grader/checks.py` | The rule-based checks |
| `grader/judge.py` | Asks a model to mark one judgement criterion |
| `grader/scoring.py` | Marks an answer against a whole rubric and adds up the points |
| `grader/llm.py` | The Anthropic client, plus a fake model for the tests |
| `grader/runner.py` | Runs tasks through a model and saves the results |
| `grader/schema.sql`, `grader/db.py` | The tables, and saving and loading tasks and runs |
| `grader/reports.py` | SQL that turns saved results into scores |
| `grader/api.py`, `grader/schemas.py` | The FastAPI app, and the shape of the JSON it accepts |

## Design decisions

- Rules wherever a rule will do. They're exact, free and easy to audit, so the judge model only handles what rules can't.
- The judge sees one criterion at a time, with the answer fenced off in tags and an instruction to treat it as text rather than instructions. Anything other than a clear PASS counts as a fail, so points need evidence.
- A run talks to the model first and saves everything in one transaction at the end. A failure part way through leaves no half-finished run, and the database isn't locked while waiting on the API.
- A run's overall score is the average of its task scores, so each task counts equally however many points its rubric has.
- Refused requests aren't retried on a fallback model. A refusal is a result worth recording, and a fallback would mix models within one run.

## Limitations

- A refusal is short, so it can still pass criteria such as "no em dashes". A stricter version would score refusals as zero.
- The spelling check only knows the words on its list, and it treats -ize endings as American, although Oxford spelling accepts them.
- A run keeps the request open until it finishes. A production version would put runs on a queue.
- The judge can be wrong. The next step would be marking a sample by hand and measuring how often the judge agrees.
