---
description: Wrap a PydanticAI agent in a Kitaru flow so every model and tool call becomes a durable checkpoint.
icon: bolt
---

# Record a durable agent

Wrap your agent in a Kitaru flow and every model call and tool call is recorded as a durable, replayable execution. That recording is the reason to do this: a run that actually happened becomes something you can replay against your real code with one thing changed — a cheaper model, a different prompt — and diff against the original. Your production runs turn into the test bed you improve against, and this page is where that test bed gets minted.

The same recording buys you crash recovery for free. If the process dies at step N, the retry resumes from step N and you don't re-pay for the calls that already finished. But the durable checkpoint is doing double duty: it's both the recovery mechanism and the recording that [replay](replay-and-improve.md) reads back.

{% hint style="info" %}
A Kitaru **flow** is a dynamic ZenML pipeline. A **checkpoint** is like a step. Agents and pipelines run on the same stacks, the same server, the same dashboard.
{% endhint %}

## One wrapper records every call

PydanticAI runs the agent loop. Kitaru records each step as it finishes. A single line connects the two:

```python
from kitaru.adapters.pydantic_ai import KitaruAgent

agent = KitaruAgent(agent, checkpoint_strategy="calls")
```

`agent` is a plain PydanticAI `Agent`. After wrapping, every model request and every tool call inside `agent.run_sync(...)` becomes its own checkpoint. The instant a call finishes, Kitaru writes its output to durable storage — a permanent record of what that call did, keyed so a later run can look it up.

You did not rewrite the agent as a state machine, learn a graph DSL, or change your control flow. It's still ordinary Python with one wrapper.

## The full example

Here is a two-turn agent that runs a shell command, wrapped in a Kitaru flow. A `FORCE_FAILURE` flag makes the flow crash on purpose between the two turns — we'll use it further down to watch a recorded run recover.

```python
import os
from pydantic_ai import Agent
from kitaru import flow
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

@flow
def investigate(question: str) -> str:
    agent = KitaruAgent(base_agent, checkpoint_strategy="calls")

    turn_1 = agent.run_sync(f"Gather facts for: {question}")

    if os.getenv("FORCE_FAILURE"):
        raise RuntimeError("simulated crash before turn 2")

    turn_2 = agent.run_sync(f"Given {turn_1.output}, answer: {question}")
    return turn_2.output

if __name__ == "__main__":
    handle = investigate.run("How many Python files are in this repo?")
    answer = handle.wait()
    print(handle.exec_id, answer)
```

`investigate.run(...)` starts the execution and returns a handle; `handle.wait()` blocks until it finishes and returns the flow's result. `handle.exec_id` — a value like `kr-9f3a1c` — is the durable record of this run. Save it: it's the anchor you replay from later.

## What the recording looks like

Once the run finishes, each checkpoint is a durable row you can inspect — in the dashboard, or from the CLI and client. List your runs:

```bash
kitaru executions list          # every run, with its exec_id
```

Then open one and read back the calls it recorded:

```python
import kitaru

client = kitaru.KitaruClient()
execution = client.executions.get("kr-9f3a1c")   # the exec_id printed above
checkpoints = execution.list_checkpoints()        # one row per recorded model or tool call
```

Every model request and tool call from the run is there, each with its recorded output. That list is the recording — the raw material [replay](replay-and-improve.md) reads back.

## Crash recovery comes free

Because each finished call is already in durable storage, a crash stops being expensive. Most agent tasks are several turns — reason, call a tool, reason again — and each turn is a real API call: real money, real seconds. When the process dies mid-task (a deploy restarts the worker, Kubernetes reschedules the pod, the box runs out of RAM), a plain in-process loop loses every finished turn with it and re-runs them all on retry. With the recording in place, the retry serves the finished calls straight from storage and only runs what never completed.

Crash on purpose, then re-run for real and watch the finished work come back for free.

{% stepper %}
{% step %}
**Crash between the two turns.**

```bash
FORCE_FAILURE=1 uv run python investigate.py
```

Turn 1 does its real model and shell work, and each call is written to durable storage. Then the flow raises before turn 2 starts. You see the failure printed.
{% endstep %}

{% step %}
**Re-run, this time for real.**

```bash
uv run python investigate.py
```

Turn 1's calls are served straight from durable storage (no model call, basically instant). Turn 2 runs fresh. The flow returns the combined result.
{% endstep %}
{% endstepper %}

What you should see across the two runs:

| | First run (`FORCE_FAILURE=1`) | Second run |
|---|---|---|
| Turn 1 calls | run, several LLM + tool calls | replayed from storage, instant, $0 |
| Turn 2 calls | never run (flow raised first) | run fresh |
| Outcome | failure | result printed, only turn 2 paid for |

The first run pays for turn 1 and dies. The second run gets turn 1 back for nothing and only spends on the work that never finished. The retry does not rebuild work that already succeeded, and the second bill is gone.

## `checkpoint_strategy`

The example passes `checkpoint_strategy="calls"`: every model request and every tool call gets its own checkpoint and its own cache key. A flow that crashed after the third call resumes by replaying only the calls after the third. This is the default and what you want in production.

There is also `checkpoint_strategy="turn"`, where each `agent.run_sync()` turn becomes a single checkpoint. It produces fewer, coarser checkpoints, which can be handy when you're learning and want clean log output. Durability is the same; the call strategy just gives you finer-grained cache entries and dashboard rows.

## What you have now

Every model call and tool call in your run is now a durable, replayable execution — a faithful recording of what your agent actually did. Crash recovery came along for free: a crash no longer throws away finished work, and a retry no longer re-pays for it.

But the recording is the real prize. You can take this exact run and replay it against your real code with **one thing changed** — a cheaper model, a different prompt — and diff the result against the original. No re-scoring a transcript, no rebuilding a test harness: the run that happened *is* the test. That is where Kitaru goes from durable to useful, and it's what the next page is about.

Continue to [Replay and improve](replay-and-improve.md).
