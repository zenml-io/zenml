# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic-ai-slim[openai]>=0.0.13",
#   # If you are not running this inside a local checkout of your ZenML sandbox branch,
#   # install ZenML from your sandbox commit/branch. Example:
#   # "zenml @ git+https://github.com/zenml-io/zenml@<YOUR_SANDBOX_COMMIT>",
# ]
# ///
"""
Minimal: PydanticAI agent tool-calls into a ZenML sandbox.

Run:
  export OPENAI_API_KEY="..."
  uv run pydanticai_zenml_sandbox_minimal.py

Optional:
  export PYDANTIC_AI_MODEL="openai:gpt-4o-mini"   # default
  export QUERY="Compute the 30th Fibonacci number and show the stdout."
  export ZENML_SANDBOX_IMAGE="python:3.12"
  export ZENML_SANDBOX_TIMEOUT="300"

ZenML prerequisite:
  Your active ZenML stack must include a sandbox component (Modal/Daytona/Monty).
"""

import os
from typing import Any

from pydantic_ai import Agent
from zenml import pipeline, step
from zenml.steps import get_step_context


def _require_env(var: str) -> str:
    value = os.getenv(var, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {var}")
    return value


def _model_str() -> str:
    # Keep it cheap by default; override with PYDANTIC_AI_MODEL if you want.
    return os.getenv("PYDANTIC_AI_MODEL", "openai:gpt-4o-mini").strip()


@step(sandbox=True)
def agent_step(query: str) -> str:
    _require_env("OPENAI_API_KEY")

    ctx = get_step_context()
    sandbox = ctx.sandbox
    if sandbox is None:
        raise RuntimeError(
            "No sandbox component found on the active ZenML stack.\n"
            "Attach one via:\n"
            "  zenml sandbox register <name> --flavor=<modal|daytona|monty>\n"
            "  zenml stack update <stack> --sandbox <name>"
        )

    image = os.getenv("ZENML_SANDBOX_IMAGE", "python:3.12")
    timeout_seconds = int(os.getenv("ZENML_SANDBOX_TIMEOUT", "300"))

    with sandbox.session(image=image, timeout_seconds=timeout_seconds) as sb:

        def run_python(code: str) -> dict[str, Any]:
            """Execute Python inside the ZenML sandbox session and return stdout/stderr/exit_code."""
            result = sb.run_code(code, timeout_seconds=120, check=False)
            return {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        agent = Agent(
            _model_str(),
            instructions=(
                "You MUST call the tool `run_python` exactly once.\n"
                "Put ALL Python you need into that single call.\n"
                "In your final answer, include:\n"
                "1) a short explanation of what you computed\n"
                "2) the raw sandbox stdout verbatim (as a code block)\n"
                "Do not claim you ran code unless it appears in stdout."
            ),
            tools=[run_python],
        )

        result = agent.run_sync(query)
        return result.output


@pipeline(enable_cache=False)
def sandbox_agent_pipeline(query: str) -> str:
    return agent_step(query)


if __name__ == "__main__":
    default_query = (
        "Compute the 30th Fibonacci number iteratively (not recursively). "
        "Also print the Python version. Then show the stdout."
    )
    sandbox_agent_pipeline(query=os.getenv("QUERY", default_query))
