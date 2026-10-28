"""The shapes of the JSON the API accepts, checked by Pydantic.

The examples are what the /docs page fills in when you click "Try it out".
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grader.scoring import validate_criterion

EXAMPLE_TASK = {
    "name": "tea-in-one-sentence",
    "prompt": "Describe a good cup of tea in one sentence, using British English.",
    "criteria": [
        {
            "description": "25 words or fewer",
            "check_type": "max_words",
            "params": {"limit": 25},
            "points": 1,
        },
        {
            "description": "British spelling",
            "check_type": "british_spelling",
            "points": 1,
        },
        {
            "description": "Reads like something a person would actually say",
            "check_type": "judge",
            "points": 2,
        },
    ],
}


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
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_TASK]})

    name: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    criteria: list[CriterionIn] = Field(min_length=1)


class AnswerIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"answer": "Strong, with a splash of milk, in a warm mug."}]}
    )

    answer: str


class RunIn(BaseModel):
    """Leave out task_ids to run every task."""

    model_config = ConfigDict(json_schema_extra={"examples": [{}]})

    task_ids: list[int] | None = None
