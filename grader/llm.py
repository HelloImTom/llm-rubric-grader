"""The models the grader talks to.

Anything with a name and a complete() method counts as a model, so the real
API client and the fake one below can be swapped for each other.
"""

import os
from typing import Protocol

import anthropic

DEFAULT_MODEL = "claude-opus-5-5"


class Model(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


class AnthropicModel:
    """Sends a prompt to a Claude model through Anthropic's Messages API."""

    def __init__(
        self,
        name: str,
        effort: str = "medium",
        client: anthropic.Anthropic | None = None,
    ):
        self.name = name
        self.effort = effort
        if client is None:
            # Reads the key from the ANTHROPIC_API_KEY environment variable.
            client = anthropic.Anthropic()
        self.client = client

    def complete(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.name,
            # Thinking counts towards this limit too, so leave plenty of room.
            max_tokens=16000,
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": prompt}],
        )
        # Record a refusal plainly, so it shows up in the results rather than
        # looking like an empty answer.
        if response.stop_reason == "refusal":
            return "[The model declined to answer]"
        # The reply is a list of blocks, which can include the model's thinking
        # as well as its answer, so keep only the text.
        return "".join(block.text for block in response.content if block.type == "text")


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


def model_from_env(variable: str) -> AnthropicModel:
    """Build the model named in an environment variable, such as ANSWER_MODEL."""
    return AnthropicModel(os.environ.get(variable, DEFAULT_MODEL))
