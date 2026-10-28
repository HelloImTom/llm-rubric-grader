"""The checks a rubric criterion can use.

Every check takes the answer as its first argument, followed by its own
parameters, and returns a pair: whether the answer passed, and a short
note for the report saying why.
"""

import json
import re

from grader.wordlists import AI_PHRASES, AMERICAN_SPELLINGS

CheckResult = tuple[bool, str]

EM_DASH = "\u2014"

# A word is a run of letters or digits. Apostrophes and hyphens are allowed
# inside a word, so "don't" and "well-known" count once and a bullet point
# marker does not count at all.
WORD = re.compile(r"\w+(?:['\u2019-]\w+)*")


def count_words(text: str) -> int:
    return len(WORD.findall(text))


def includes(answer: str, text: str) -> CheckResult:
    if text.lower() in answer.lower():
        return True, f'Contains "{text}"'
    return False, f'Missing "{text}"'


def excludes(answer: str, text: str) -> CheckResult:
    if text.lower() in answer.lower():
        return False, f'Contains "{text}"'
    return True, f'Does not contain "{text}"'


def min_words(answer: str, limit: int) -> CheckResult:
    count = count_words(answer)
    return count >= limit, f"{count} words (minimum {limit})"


def max_words(answer: str, limit: int) -> CheckResult:
    count = count_words(answer)
    return count <= limit, f"{count} words (maximum {limit})"


def matches(answer: str, pattern: str) -> CheckResult:
    if re.search(pattern, answer):
        return True, f'Matches "{pattern}"'
    return False, f'Does not match "{pattern}"'


def valid_json(answer: str, keys: list[str] | None = None) -> CheckResult:
    try:
        data = json.loads(answer)
    except json.JSONDecodeError as error:
        return False, f"Not valid JSON: {error.msg}"
    if keys:
        if not isinstance(data, dict):
            return False, "Expected a JSON object"
        missing = [key for key in keys if key not in data]
        if missing:
            return False, "Missing keys: " + ", ".join(missing)
    return True, "Valid JSON"


def british_spelling(answer: str) -> CheckResult:
    words = set(re.findall(r"[a-z]+", answer.lower()))
    found = sorted(word for word in words if word in AMERICAN_SPELLINGS)
    if found:
        fixes = ", ".join(f"{word} ({AMERICAN_SPELLINGS[word]})" for word in found)
        return False, f"American spellings: {fixes}"
    return True, "No American spellings"


def no_em_dashes(answer: str) -> CheckResult:
    count = answer.count(EM_DASH)
    if count:
        return False, f"Em dashes found: {count}"
    return True, "No em dashes"


def no_ai_phrases(answer: str) -> CheckResult:
    # Models often use curly apostrophes, so straighten them before matching.
    text = answer.lower().replace("\u2019", "'")
    found = [phrase for phrase in AI_PHRASES if phrase.lower() in text]
    if found:
        return False, "Stock phrases: " + ", ".join(found)
    return True, "No stock phrases"


CHECKS = {
    "includes": includes,
    "excludes": excludes,
    "min_words": min_words,
    "max_words": max_words,
    "matches": matches,
    "valid_json": valid_json,
    "british_spelling": british_spelling,
    "no_em_dashes": no_em_dashes,
    "no_ai_phrases": no_ai_phrases,
}


def run_check(check_type: str, answer: str, params: dict) -> CheckResult:
    if check_type not in CHECKS:
        raise ValueError(f"Unknown check type: {check_type}")
    return CHECKS[check_type](answer, **params)
