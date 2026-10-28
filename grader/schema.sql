-- A task is a prompt to send to the model. Its rubric is the set of
-- criteria that belong to it.
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL UNIQUE,
    prompt     TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Each criterion uses one check from checks.py, or "judge" for one that a
-- model marks. Its settings are stored as JSON text.
CREATE TABLE IF NOT EXISTS criteria (
    id          INTEGER PRIMARY KEY,
    task_id     INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    description TEXT    NOT NULL,
    check_type  TEXT    NOT NULL,
    params      TEXT    NOT NULL DEFAULT '{}',
    points      INTEGER NOT NULL DEFAULT 1 CHECK (points > 0)
);

-- A run sends tasks to one model, and records which model did the judging.
CREATE TABLE IF NOT EXISTS runs (
    id         INTEGER PRIMARY KEY,
    model      TEXT    NOT NULL,
    judge      TEXT,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- The model's answer to one task within a run.
CREATE TABLE IF NOT EXISTS answers (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    text    TEXT    NOT NULL,
    UNIQUE (run_id, task_id)
);

-- How one answer did against one criterion.
CREATE TABLE IF NOT EXISTS results (
    answer_id    INTEGER NOT NULL REFERENCES answers (id) ON DELETE CASCADE,
    criterion_id INTEGER NOT NULL REFERENCES criteria (id) ON DELETE CASCADE,
    passed       INTEGER NOT NULL CHECK (passed IN (0, 1)),
    detail       TEXT    NOT NULL,
    PRIMARY KEY (answer_id, criterion_id)
);

-- SQLite doesn't index foreign keys by itself, and a rubric is always loaded
-- by task. The other lookups are covered by the UNIQUE and PRIMARY KEY
-- constraints above, which come with their own indexes.
CREATE INDEX IF NOT EXISTS criteria_task_id ON criteria (task_id);

-- Points earned and available for each answer. The reports build on this
-- view, so the rule for adding up points lives in one place.
CREATE VIEW IF NOT EXISTS answer_scores AS
SELECT
    answers.id AS answer_id,
    answers.run_id,
    answers.task_id,
    SUM(CASE WHEN results.passed = 1 THEN criteria.points ELSE 0 END) AS earned,
    SUM(criteria.points) AS possible
FROM answers
JOIN results ON results.answer_id = answers.id
JOIN criteria ON criteria.id = results.criterion_id
GROUP BY answers.id;
