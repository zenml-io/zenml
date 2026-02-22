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
  uv run scripts/test_sandboxes_pydantic.py

Optional:
  export PYDANTIC_AI_MODEL="openai:gpt-4o-mini"   # default
  export QUERY="Compute the 30th Fibonacci number and show the stdout."
  export ZENML_SANDBOX_IMAGE="python:3.12"
  export ZENML_SANDBOX_TIMEOUT="300"
  export ZENML_EMIT_SANDBOX_NOISE="1"              # default: on
  export ZENML_SANDBOX_NOISE_LINES="16"            # default: 16

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


def _is_truthy(value: str) -> bool:
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _emit_sandbox_noise(sb: Any, lines: int) -> None:
    """Emit deterministic stdout/stderr lines inside the sandbox.

    This makes dashboard validation easier by guaranteeing noisy sandbox logs
    (including stderr) even if the LLM tool call is concise.
    """
    safe_lines = max(1, min(lines, 200))
    noise_code = (
        "import platform, sys, time\n"
        "print('=== SANDBOX NOISE START ===')\n"
        "print(f'[sandbox-noise][meta] python={platform.python_version()}')\n"
        f"for i in range({safe_lines}):\n"
        "    print(f'[sandbox-noise][stdout] i={i:03d} square={i*i}')\n"
        "    print(f'[sandbox-noise][stderr] i={i:03d} cube={i*i*i}', file=sys.stderr)\n"
        "    time.sleep(0.01)\n"
        "print('=== SANDBOX NOISE END ===')\n"
    )
    result = sb.run_code(noise_code, timeout_seconds=120, check=False)
    print(
        "[local-step] sandbox probe emitted",
        {
            "exit_code": result.exit_code,
            "stdout_chars": len(result.stdout),
            "stderr_chars": len(result.stderr),
            "lines": safe_lines,
        },
    )


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
        emit_noise = _is_truthy(os.getenv("ZENML_EMIT_SANDBOX_NOISE", "1"))
        noise_lines = int(os.getenv("ZENML_SANDBOX_NOISE_LINES", "16"))
        if emit_noise:
            _emit_sandbox_noise(sb, lines=noise_lines)

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
