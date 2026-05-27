# PydanticAI + ZenML Sandbox

A minimal example showing a [PydanticAI](https://ai.pydantic.dev) agent that uses a ZenML [Sandbox](../../docs/book/component-guide/sandboxes/README.md) component to execute the Python code it generates as a tool. The agent reasons in natural language, writes Python when it needs to compute something, and the Sandbox runs that code in an isolated environment — the agent process never executes LLM-generated code directly.

## What's interesting here

- **The Sandbox component is the agent's tool.** `agent.run_python(code)` calls `session.exec(["python", "-u", "-c", code])` on the active stack's Sandbox. Switch the stack's sandbox flavor (Modal, future Agent Substrate, etc.) and the agent gets a different execution backend without code changes.
- **One Session, many tool calls.** The agent loop opens one `SandboxSession` and reuses it across every `run_python` invocation. The container's filesystem (files, installed packages) persists between turns — each call is a fresh Python interpreter though, so variables and imports do *not* carry over and the agent must write self-contained scripts.
- **Streaming stdout into the step log.** When the Modal flavor's `forward_logs_to_step` setting resolves `True` (the default when `base_image == STEP_IMAGE`), the live Session opens a ZenML `LoggingContext` on `__enter__` and each output line surfaces in the step's log stream as a dedicated `sandbox:<session_id>` source. With the flavor's default image, the setting resolves `False` — the agent still sees the captured stdout from the tool's return value, but it doesn't land in the step log. Override per-step via `ModalSandboxSettings(forward_logs_to_step=True)` if you want it on.

## Prerequisites

1. A Modal account (or another Sandbox flavor once they ship): `modal token new`.
2. `OPENAI_API_KEY` in your environment (or swap the model in `agent.py`).
3. The ZenML Modal integration: `zenml integration install modal`.

## Setup

```bash
cd examples/sandbox_pydantic_ai
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

Default query: *"What's the sum of the first 100 prime numbers? Write Python to compute it."* The agent writes a sieve, runs it in the sandbox, parses the stdout, and answers in natural language. Pass your own:

```bash
python -c "from run import sandbox_pydantic_ai_pipeline; sandbox_pydantic_ai_pipeline(query='Plot a sine wave and tell me the peak value.')"
```

> **Run as a script, not in a notebook.** PydanticAI's `run_sync` spins up its own event loop and refuses to nest inside an existing one (Jupyter has one).

## File layout

- `agent.py` — PydanticAI `Agent` with a single `run_python(code: str) -> CodeResult` tool that wraps `SandboxSession.exec`. Carries the live session via `RunContext.deps`. Stdout/stderr are fully drained and byte-capped (truncation marker appended) to avoid hanging Modal's `wait()` on un-emptied buffers.
- `run.py` — Single-step ZenML pipeline that calls `run_agent(query)`. The agent loop lives entirely inside one step; see `examples/agent_framework_integrations/langgraph/` if you want a multi-step decomposition.
- `requirements.txt` — pydantic-ai + zenml + modal.

## Switching sandbox flavors

The example doesn't import anything Modal-specific — it goes through `Client().active_stack.sandbox` and the `BaseSandbox` interface. To use a different flavor, just change your stack:

```bash
zenml sandbox register my-other-sandbox --flavor=<other_flavor>
zenml stack update --sandbox my-other-sandbox
```

The agent code is identical.

## Cloud orchestrators

The setup above uses the `default` orchestrator (the agent step runs in your local Python). To run on a remote orchestrator (Kubernetes, SageMaker, Vertex...), add `DockerSettings` to the pipeline so the step image carries `pydantic-ai` and `OPENAI_API_KEY`:

```python
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",
    environment={"OPENAI_API_KEY": os.environ["OPENAI_API_KEY"]},
)

@pipeline(settings={"docker": docker_settings})
def sandbox_pydantic_ai_pipeline(...): ...
```

The Sandbox still runs on its own backend (Modal) — only the orchestration changes.
