from types import SimpleNamespace

from grader.llm import DEFAULT_MODEL, AnthropicModel, model_from_env


class StubMessages:
    """Stands in for client.messages and records each request it's given."""

    def __init__(self, response):
        self.response = response
        self.requests = []

    def create(self, **request):
        self.requests.append(request)
        return self.response


def stub_client(blocks, stop_reason="end_turn"):
    response = SimpleNamespace(content=blocks, stop_reason=stop_reason)
    return SimpleNamespace(messages=StubMessages(response))


def test_complete_sends_one_user_message_and_returns_the_text():
    thinking = SimpleNamespace(type="thinking", thinking="")
    text = SimpleNamespace(type="text", text="Canberra.")
    client = stub_client([thinking, text])
    model = AnthropicModel("claude-opus-5-5", client=client)

    assert model.complete("What is the capital of Australia?") == "Canberra."

    request = client.messages.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"] == {"effort": "medium"}
    assert request["messages"] == [
        {"role": "user", "content": "What is the capital of Australia?"}
    ]


def test_a_refusal_is_recorded_plainly():
    model = AnthropicModel("claude-opus-5-5", client=stub_client([], stop_reason="refusal"))
    assert model.complete("Anything") == "[The model declined to answer]"


def test_model_from_env_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.delenv("ANSWER_MODEL", raising=False)
    assert model_from_env("ANSWER_MODEL").name == DEFAULT_MODEL


def test_model_from_env_reads_the_variable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setenv("JUDGE_MODEL", "claude-haiku-5-5")
    assert model_from_env("JUDGE_MODEL").name == "claude-haiku-5-5"
