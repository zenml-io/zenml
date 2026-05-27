# PydanticAI + ZenML Sandbox

A minimal example showing a [PydanticAI](https://ai.pydantic.dev) agent that uses a ZenML [Sandbox](../../docs/book/component-guide/sandboxes/README.md) component to execute the Python code it generates as a tool. The agent reasons in natural language, writes Python when it needs to compute something, and the Sandbox runs that code in an isolated environment — the agent process never executes LLM-generated code directly.

## What's interesting here

- **The Sandbox component is the agent's tool.** `agent.run_python(code)` calls `session.exec(["python", "-c", code])` on the active stack's Sandbox. Switch the stack's sandbox flavor (Modal, future Agent Substrate, etc.) and the agent gets a different execution backend without code changes.
- **One Session, many tool calls.** The agent loop opens one `SandboxSession` and reuses it across every `run_python` invocation, so files written by earlier code persist for later turns.
- **Streaming stdout** lands in the step's log stream as a dedicated `sandbox:<session_id>` source when the flavor wires `forward_logs_to_step` (Modal does).

## Prerequisites

1. A Modal account (or another Sandbox flavor once they ship): `modal token new`.
2. `OPENAI_API_KEY` in your environment (or swap the model in `agent.py`).
3. The ZenML Modal integration: `zenml integration install modal`.

## Setup

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt

zenml init
zenml sandbox register modal-sb --flavor=modal
zenml stack register sandbox-stack -o default -a default --sandbox modal-sb
zenml stack set sandbox-stack
```

## Run

```bash
export OPENAI_API_KEY=sk-...
python run.py
```

Default query: *"What's the sum of the first 100 prime numbers? Write Python to compute it."* The agent will write a sieve, run it in the sandbox, parse the stdout, and answer in natural language. Pass your own:

```bash
python -c "from run import sandbox_pydantic_ai_pipeline; sandbox_pydantic_ai_pipeline(query='Plot a sin wave from 0 to 2π and tell me the peak value.')"
```

## File layout

- `agent.py` — PydanticAI `Agent` with a single `run_python(code: str) -> CodeResult` tool that wraps `SandboxSession.exec`. Carries the live session via `RunContext.deps`.
- `run.py` — ZenML pipeline + step that calls `run_agent(query)`.
- `requirements.txt` — pydantic-ai + zenml + modal.

## Switching sandbox flavors

The example doesn't import anything Modal-specific — it goes through `Client().active_stack.sandbox` and the `BaseSandbox` interface. To use a different flavor, just change your stack:

```bash
zenml sandbox register my-other-sandbox --flavor=<other_flavor>
zenml stack update --sandbox my-other-sandbox
```

The agent code is identical.
