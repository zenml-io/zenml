# PydanticAI + ZenML Sandbox

A multi-step ZenML pipeline that drives a [PydanticAI](https://ai.pydantic.dev) agent through a ZenML [Sandbox](../../docs/book/component-guide/sandboxes/README.md) backed by Modal. The pipeline plans, fans out subagents, and reduces — each subagent gets its own isolated sandbox session restored from a snapshot the parent prepared once.

## Pipeline shape

```
prep_step ──► snapshot ─┐
                        ├─► subagent_step.map() ──► reducer_step
planner_step ──► subtasks ┘
```

1. **`prep_step`** boots a sandbox, `pip install`s the scientific stack (numpy, scipy) once, and snapshots the filesystem into a `SandboxSnapshot` artifact (Modal Image id, materialized through ZenML's artifact store).
2. **`planner_step`** asks a small LLM to decompose the user's goal into three *independent* subtasks (system prompt enforces no shared filesystem / no cross-subagent dependencies, since each subagent runs in its own sandbox). The `.map()` fan-out itself handles any list length.
3. **`subagent_step`** (fanned out via `step.map(snapshot=unmapped(...), subtask=subtasks)`) — each instance restores from the shared snapshot, opens a fresh agent loop in that restored sandbox, and returns one partial answer.
4. **`reducer_step`** synthesizes the partial answers into a final response with another LLM call.

Wall clock on the smoke run: prep ~13 s, planner ~5 s, three parallel subagents ~90–200 s, reducer ~9 s — about **3.5 min total** vs ~11 min if every subagent re-installed deps from scratch.

## What's interesting here

- **The Sandbox component is the agent's tool.** The agent has four tools — `run_python`, `run_shell`, `list_files`, `read_file` — each of which calls `session.exec(...)` on the active stack's Sandbox via the flavor-agnostic `BaseSandbox` interface. Snapshots are an optional sandbox capability (Modal implements them today): where available, the heavy dependency install runs once and every subagent restores it for free; on flavors without snapshots the pipeline degrades gracefully — `prep_step` probes and returns nothing, and each subagent installs its own dependencies in a fresh session.
- **One sandbox session per subagent, many tool calls per session.** Every subagent step opens one `SandboxSession` and reuses it across all of its `run_python` / `run_shell` calls. Files written to `/tmp` and pip-installed packages persist between turns, so the agent can build up state across tool calls. (Imports / Python variables do *not* persist — each `run_python` is a fresh interpreter.)
- **Snapshot fan-out.** Heavy setup (pip install, dataset download, model warmup) runs once in `prep_step`; every fanned-out subagent boots from the snapshot for free. The snapshot is a normal ZenML artifact — cacheable, queryable, replayable.
- **Per-session log forwarding.** Each subagent's sandbox stdout/stderr surfaces in *its own* step log stream as a dedicated `sandbox:<session_id>` source. Step metadata records `sandbox.<session_id>.flavor` and (Uri-typed) `sandbox.<session_id>.dashboard_url` so the dashboard renders a clickable link to the Modal sandbox.
- **`step.map` + `unmapped`.** Fan-out is just `subagent_step.map(snapshot=unmapped(snap), subtask=subtasks)`. The snapshot is broadcast to all N steps; the subtasks zip 1:1. Zero bespoke infra.

## Prerequisites

1. A Modal account — authenticate with `modal token new` (writes `~/.modal.toml`) or export `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`. The Modal SDK reads these on import.
2. `OPENAI_API_KEY` in your environment (or swap the model in `agent.py`).
3. ZenML's Modal integration: `zenml integration install modal`.

## Setup

```bash
cd examples/sandbox_pydantic_ai
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt

zenml init
```

Create a ZenML secret carrying your OpenAI key (`zenml secret create` preserves the casing of the key names you pass):

```bash
zenml secret create openai --OPENAI_API_KEY=<your-openai-api-key>
```

Register the sandbox component. Modal credentials come either from the Modal SDK's ambient auth (`~/.modal.toml` or `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` env vars) or from the component itself (`zenml sandbox register ... --token_id=... --token_secret=...`). Prefer the component route when steps run on a remote orchestrator, since the orchestrator environment won't have your local Modal auth.

```bash
zenml sandbox register modal-sb \
  --flavor=modal \
  --secret=openai

zenml stack register sandbox-stack -o default -a default --sandbox modal-sb
zenml stack set sandbox-stack
```

If you're using a remote artifact store (S3 / GCS / Azure Blob), point `-a` at that — the `SandboxSnapshot` artifact crosses the prep → subagent boundary through the artifact store.

## Run

```bash
python run.py
```

Default query benchmarks three classic numerical-methods problems (Monte Carlo π, Simpson's rule, Newton's method) — each landed in its own subagent, each truly independent of the others.

Pass your own query:

```bash
python -c "from run import sandbox_pydantic_ai_pipeline; \
  sandbox_pydantic_ai_pipeline(query='Compare three sorting algorithms by runtime on 100k random ints.')"
```

Phrase tasks so they decompose into **independent** subtasks (each subagent sees a fresh filesystem — no inter-subagent state). If you ask the planner to coordinate (e.g. "step 1 writes a file, step 2 reads it") the subagents will fail; the planner system prompt enforces independence but a sufficiently leading user query can still confuse it.

Open the run on the dashboard URL printed to stdout, or load the final answer programmatically:

```python
from zenml.client import Client
run = Client().get_pipeline_run("<run-id-from-stdout>")
print(run.steps["reducer_step"].outputs["final_answer"][0].load())
```

> **Run as a script, not in a notebook.** PydanticAI's `run_sync` opens its own event loop and refuses to nest inside an existing one (Jupyter already has one).

## File layout

- `agent.py` — Four-tool PydanticAI agent (`run_python`, `run_shell`, `list_files`, `read_file`), the planner / reducer helper functions, and `run_agent_in_session(session, query)` that drives the agent against a caller-supplied session (so the pipeline can plug in a restored snapshot).
- `run.py` — `prep_step → planner_step → subagent_step.map() → reducer_step` dynamic pipeline.
- `requirements.txt` — pydantic-ai + zenml. The Modal SDK is pulled in by `zenml integration install modal`.

## Tuning knobs

- **Make subagents independent.** The planner's system prompt insists on no shared state; if you write a leading query that implies a pipeline, the planner may still produce dependent subtasks and you'll see "file not found" errors from subagents 2+.
- **Richer base image.** The default Modal image is `python:3.11-slim` — bare Python. The agent's system prompt teaches it to `pip install` on demand, and `prep_step` does this once and snapshots. To skip the snapshot dance, pass a pre-built sci-py image in `ModalSandboxSettings(image="ghcr.io/your-org/scipy-base:latest")` on the relevant step.

## Cloud orchestrators

The default `orchestrator: default` runs the agent steps on your local Python. To run on a remote orchestrator (Kubernetes, SageMaker, Vertex…), the pipeline's `DockerSettings` bakes the example's requirements into the step image. No extra env wiring is needed for the OpenAI key: the `--secret=openai` attached to the sandbox component is resolved into the step environment at runtime, on any orchestrator.

The Sandbox itself still runs on Modal regardless of the orchestrator — only step execution location changes.
