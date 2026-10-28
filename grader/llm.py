"""The models the grader talks to.

Anything with a name and a complete() method counts as a model, so the real
API client and the fake one below can be swapped for each other.
"""

from typing import Protocol


class Model(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


class FakeModel:
    """Gives the same reply every time, so tests never call a real API.

    It keeps every prompt it's sent, so a test can check what the model saw.
    """

    name = "fake"

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply
