---
description: Wrap a PydanticAI agent with the Kitaru adapter so every run is recorded as a replayable session.
icon: bolt
---

# Record an agent

Wrap your agent once and every run it makes is recorded as a **session** — every model call, every tool call, every decision, in order, with cost and token usage attached. That recording is the reason to do this: a run that actually happened becomes something you can replay against your real code with one thing changed — a cheaper model, a different prompt — and diff against the original. This page is where that recording gets made.

{% hint style="info" %}
A **session** is Kitaru's unit of recording: one agent run, stored as a sequence of nodes (model calls, tool calls) on the Kitaru server. Sessions come from two places — recorded live by an adapter, as on this page, or [imported from the traces you already collect](https://docs.zenml.io/kitaru/getting-started/import-your-traces) in Langfuse.
{% endhint %}

## One wrapper records every call

PydanticAI runs the agent loop. Kitaru records each step as it finishes. A single line connects the two:

```python
from kitaru.adapters.pydantic_ai import KitaruAgent

agent = KitaruAgent(base_agent, agent_id=AGENT_ID)
```

`base_agent` is a plain PydanticAI `Agent`. After wrapping, every model request and every tool call inside `agent.run_sync(...)` streams to the Kitaru server as nodes on a session. You did not rewrite the agent as a state machine, learn a graph DSL, or change your control flow. It's still ordinary Python with one wrapper.

## The full example

Register the agent once and export the connection — the id it prints is how sessions attach to the right agent:

```bash
export KITARU_API_URL=http://localhost:8000    # your Kitaru server
kitaru agent register investigator --command "python investigate.py"
export KITARU_AGENT_ID=<id printed above>
```

Here is a two-turn agent that runs a shell command, wrapped for recording:

```python
# investigate.py
import os
import uuid

from pydantic_ai import Agent
from kitaru.adapters.pydantic_ai import KitaruAgent

base_agent = Agent(
    "anthropic:claude-sonnet-4-5",
    system_prompt="You are a careful shell operator. Use the exec tool.",
)

@base_agent.tool_plain
def exec(command: str) -> str:
    import subprocess
    return subprocess.run(
        command, shell=True, capture_output=True, text=True
    ).stdout

agent = KitaruAgent(base_agent, agent_id=uuid.UUID(os.environ["KITARU_AGENT_ID"]))

if __name__ == "__main__":
    question = "How many Python files are in this repo?"
    facts = agent.run_sync(f"Gather facts for: {question}")
    answer = agent.run_sync(f"Given {facts.output}, answer: {question}")
    print(answer.output)
```

Run it and the agent behaves exactly as before — same output, same latency profile — while each turn lands on the server as a session.

## What the recording looks like

Once the run finishes, the session is a durable record you can inspect from the CLI:

```bash
kitaru session list --agent investigator      # every run, with its session id
kitaru session nodes <session-id> --include-payloads
```

Each node is one model request or tool call, with its inputs, outputs, timing, token usage, and cost. That list is the recording — the raw material [replay](replay-and-improve.md) reads back. The same read is two calls on the Python client:

```python
from kitaru.client import KitaruAPIClient

client = KitaruAPIClient()   # reads KITARU_API_URL / KITARU_API_KEY
sessions = await client.sessions.list()
nodes = await client.sessions.list_nodes(sessions.items[0].id, include_payloads=True)
```

## Already tracing? Import instead

If your agent already logs to Langfuse, you don't need the wrapper to get started: export the traces and import them, and each trace becomes a session exactly like the recorded ones — Langfuse stays your system of record, Kitaru gets a runnable copy. See [Import your traces](https://docs.zenml.io/kitaru/getting-started/import-your-traces).

## What you have now

Every run of your agent is now a faithful recording of what it actually did. But the recording is the real prize: you can take this exact run and replay it against your real code with **one thing changed** — a cheaper model, a different prompt — and diff the result against the original. No re-grading a transcript, no rebuilding a test harness: the run that happened *is* the test. That is what the next page is about.

Continue to [Replay and improve](replay-and-improve.md).
