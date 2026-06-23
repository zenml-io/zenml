---
description: Wrap a PydanticAI agent in a Kitaru flow so every model and tool call becomes a durable checkpoint.
icon: bolt
---

# Run a durable agent

Wrap your agent in a Kitaru flow and every model call and tool call is recorded as a durable checkpoint. If the process dies at step N, the retry resumes from step N. You don't re-pay for the calls that already finished.

This is the foundation. Recording every step durably is what later lets you replay a real run with one thing changed. We'll get there at the end of this page; first, make a run survive a crash.

{% hint style="info" %}
A Kitaru **flow** is a dynamic ZenML pipeline. A **checkpoint** is like a step. Agents and pipelines run on the same stacks, the same server, the same dashboard.
{% endhint %}

## The problem: a crash costs you twice

Most agent tasks are not a single model call. The agent reasons, calls a tool, reads the result, reasons again, and finishes a few turns later. Every turn is a real API call: real money, real seconds.

Now the process dies mid-task. Not a bug in your agent: a deploy restarts the worker, Kubernetes reschedules the pod, the box runs out of RAM. The job retries from the top.

A plain in-process agent loop kept the finished turns in memory, and that memory died with the process. So the retry re-runs every turn it already completed: the same model calls, the same cost, the same latency, all to rebuild a result you had a minute ago. On a ten-turn task that dies near the end, you pay for almost the entire run twice.

## The fix: one wrapper

PydanticAI runs the agent loop. Kitaru records each step as it finishes, so a retry picks up where the crash hit. A single line connects the two:

```python
from kitaru.adapters.pydantic_ai import KitaruAgent

agent = KitaruAgent(agent, checkpoint_strategy="calls")
```

`agent` is a plain PydanticAI `Agent`. After wrapping, every model request and every tool call inside `agent.run_sync(...)` becomes its own checkpoint. The instant a call finishes, Kitaru writes its output to durable storage. When a retry reaches a call that already finished, Kitaru returns the saved output instead of hitting the model again.

You did not rewrite the agent as a state machine, learn a graph DSL, or change your control flow. It's still ordinary Python with one wrapper.

## The full example

Here is a two-turn agent that runs a shell command, wrapped in a Kitaru flow. A `FORCE_FAILURE` flag makes the flow crash on purpose between the two turns so you can watch the recovery.

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
    exec_ = investigate.run("How many Python files are in this repo?").wait()
    print(exec_.exec_id, exec_.output)
```

## Run it

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

The first run pays for turn 1 and dies. The second run gets turn 1 back for nothing and only spends on the work that never finished. The retry does not rebuild work that already succeeded. The second bill is gone.

## `checkpoint_strategy`

The example passes `checkpoint_strategy="calls"`: every model request and every tool call gets its own checkpoint and its own cache key. A flow that crashed after the third call resumes by replaying only the calls after the third. This is the default and what you want in production.

There is also `checkpoint_strategy="turn"`, where each `agent.run_sync()` turn becomes a single checkpoint. It produces fewer, coarser checkpoints, which can be handy when you're learning and want clean log output. Durability is the same; the call strategy just gives you finer-grained cache entries and dashboard rows.

## What you have now

Every model call and tool call in your run is recorded as a durable checkpoint. A crash no longer throws away finished work, and a retry no longer re-pays for it.

Because every step is recorded, you can now take this exact run and replay it with **one thing changed** — a different model, a different prompt — and diff the result against the original. That is where Kitaru goes from durable to useful.

Continue to [Replay and improve](replay-and-improve.md).
