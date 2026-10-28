"""Mark an answer against a task's rubric."""

from grader.checks import run_check
from grader.judge import ask_judge
from grader.llm import Model


def grade_answer(task: dict, answer: str, judge: Model | None = None) -> dict:
    """Run each criterion in the task's rubric against the answer and add up the points.

    The task needs a "prompt" and a list of "criteria". A criterion is a dict
    with "description", "check_type", "params" and "points". Any other keys,
    such as "id", are copied into its result so the caller can tell which
    result belongs to which criterion.

    Criteria with the check type "judge" are for things rules can't check,
    such as tone or accuracy. A model marks them, using the description as
    the requirement.
    """
    criteria = task["criteria"]
    if not criteria:
        raise ValueError("A rubric needs at least one criterion")

    results = []
    for criterion in criteria:
        if criterion["check_type"] == "judge":
            if judge is None:
                raise ValueError("This rubric has judge criteria, so it needs a judge model")
            passed, detail = ask_judge(judge, task["prompt"], answer, criterion["description"])
        else:
            passed, detail = run_check(criterion["check_type"], answer, criterion["params"])
        results.append({**criterion, "passed": passed, "detail": detail})

    earned = sum(result["points"] for result in results if result["passed"])
    possible = sum(criterion["points"] for criterion in criteria)
    return {
        "earned": earned,
        "possible": possible,
        "score": round(earned / possible, 3),
        "results": results,
    }
