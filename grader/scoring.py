"""Mark an answer against a rubric."""

from grader.checks import run_check


def grade_answer(answer: str, criteria: list[dict]) -> dict:
    """Run each criterion against the answer and add up the points.

    A criterion is a dict with "check_type", "params" and "points". Any other
    keys, such as "description" or "id", are copied into its result so the
    caller can tell which result belongs to which criterion.
    """
    if not criteria:
        raise ValueError("A rubric needs at least one criterion")

    results = []
    for criterion in criteria:
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
