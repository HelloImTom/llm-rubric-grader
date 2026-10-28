"""Send one prompt to the answer model and print the reply.

A quick way to check your API key works:

    python -m grader.ask "What is the capital of Australia?"
"""

import sys

from dotenv import load_dotenv

from grader.llm import model_from_env


def main() -> None:
    # Copies the settings in the .env file into the environment.
    load_dotenv()
    prompt = " ".join(sys.argv[1:]) or "Say hello in five words."
    print(model_from_env("ANSWER_MODEL").complete(prompt))


if __name__ == "__main__":
    main()
