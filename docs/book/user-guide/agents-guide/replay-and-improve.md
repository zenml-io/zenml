---
description: Replay a real agent run with one thing changed to see what would have happened, then scale the winning change across a cohort of recent runs.
icon: arrows-rotate
---

# Replay and improve

Replay is why the recording exists. Take a run that actually happened, change exactly one thing — a different model, a different prompt — re-execute it against your real code, and diff the result against the original. Because the rest of the run reproduces faithfully, the difference you see is your change, not replay noise.

This is the part that other tooling can't do. An eval re-grades outputs after the fact. Replay re-executes the actual run with one input swapped, so you find out what *would have happened* if you'd shipped the change. Then you scale that decision across a cohort of recent runs and keep the version that wins.

{% hint style="info" %}
Replay answers your agent's tool calls from the recorded session — the whole reason a run gets recorded. If you haven't recorded one yet, start with the [record stage](01-durable-agent.md), which mints the session this page replays. Two more things replay needs: a registered agent version with a run command (replay re-runs your real code, which no recording contains), and a [worker](https://docs.zenml.io/kitaru/concepts/workers) running in an environment that can execute it (`kitaru worker start`).
{% endhint %}

## Three runs, not two

It's tempting to think of replay as two runs: the original and your changed one. It's actually three, and the middle one is what makes the result trustworthy.

| Run | What it is | Role |
|---|---|---|
| **Observed** | The original recorded session | What actually happened |
| **Reproduced** | Replay with no change | The control — proves replay is faithful |
| **Forked** | Replay with exactly one thing changed | Your change |

You diff **Forked** against **Reproduced**, not against **Observed**. The reproduced run is the control that isolates your variable: because it replays the same recording with nothing swapped, it should land exactly where the observed run did.

**If the reproduced run doesn't match the observed baseline, stop.** A nondeterministic tool, an external state change, a time-dependent output — any of these means replay isn't faithful for this agent, and a diff built on it is untrustworthy. Don't act on it. Fix the source of nondeterminism first (answer the tool from the recording, pin the value), then replay. Everything below assumes the reproduced run checks out.

## You start with a recorded session

```bash
kitaru session list --agent investigator
```

Hold onto the session id of the run you care about — the failing ticket, the expensive one. That's the anchor you replay from. You also need at least one [evaluator](https://docs.zenml.io/kitaru/concepts/evaluators) — every replay is evaluated, so define what "good" means first. The built-in `cost` and `latency` evaluators are available immediately; a domain check is a few lines of Python:

```bash
kitaru evaluator scaffold decision-check     # writes decision_check_evaluator.py
kitaru evaluator register decision-check \
  --script decision_check_evaluator.py --entrypoint evaluate
```

## Reproduce: replay with no change

Before you change anything, prove that the run reproduces. Create a replay with no override — recorded tool calls are answered from the session, and `on_miss="fail"` guarantees nothing unrecorded ever executes:

```python
from kitaru.api_models.v1.replay import ReplayCreateRequest
from kitaru.api_models.v1.replay_config import (
    EvaluatorConfig, HistoryConfig, ToolPolicy,
)
from kitaru.client import KitaruAPIClient

RECORDED_TOOLS = ToolPolicy(default=HistoryConfig(scope="baseline", on_miss="fail"))

client = KitaruAPIClient()
control = await client.replays.create(
    ReplayCreateRequest(
        baseline_session_id=SESSION_ID,          # from `kitaru session list`
        evaluators=[EvaluatorConfig(evaluator="decision-check")],
        tool_policy=RECORDED_TOOLS,
        evaluate_baselines=True,                 # evaluate the original too
    )
)
```

The replay re-runs your agent's real code on a worker, producing a new session (`origin: replay`). This reproduced run is your **control** — it should land on the same decision the observed run did, and `evaluate_baselines=True` means both sides carry evaluations you can compare directly. If they disagree, stop (see [Three runs, not two](#three-runs-not-two) above).

## Fork: change exactly one thing

Now fork the same session with a single override. Same recording, same tool policy, one difference:

```python
from kitaru.api_models.v1.replay import ReplayOverride

forked = await client.replays.create(
    ReplayCreateRequest(
        baseline_session_id=SESSION_ID,
        override=ReplayOverride(model={"anthropic:claude-sonnet-4-5": "openai:gpt-5-nano"}),
        evaluators=[EvaluatorConfig(evaluator="decision-check")],
        tool_policy=RECORDED_TOOLS,
    )
)
```

The agent re-executes for real — but every model request that asked for the original model now gets the cheaper one, while recorded tool calls are still answered from the session. You're seeing what this run *would have done* under the change. Prompt and code changes work the same way: override the prompt, or register your working tree as a new agent version and replay against it. Change one variable at a time if you want the diff to attribute cleanly — the [override and tool-policy selectors](https://docs.zenml.io/kitaru/guides/replay-and-overrides) cover narrower targeting.

## Diff: did the decision move?

Each replay links its baseline and result sessions. Read the evaluations on both sides and compare:

```python
replay = await client.replays.get(forked.id)
# replay.baseline_session_id → the original, replay.result_session_id → the fork
```

Pull each session's evaluations (`client.evaluations.list(...)` filtered by session) and its cost rollup, and the comparison is concrete: did `decision-check` still pass, and what did the run cost? Because the reproduced control matched the observed baseline, any difference between control and fork is attributable to your one change. That's the whole point: a trustworthy comparison of a single variable.

## Improve: scale the decision across a cohort

One replay tells you what a change did to one run. To decide whether to ship it, run the same change across a batch of recent runs and read the aggregate. That's a [cohort](https://docs.zenml.io/kitaru/concepts/cohorts) (an immutable set of sessions) plus an [experiment](https://docs.zenml.io/kitaru/concepts/experiments) (the change, named):

```bash
# Freeze the population — selection by tag, filter, or explicit ids
kitaru cohort create investigator-regression --agent investigator \
  --filter '{"field": "agent_id", "op": "eq", "value": "<agent-id>"}' \
  --display-version week-32

# Name the change: the override, the tool policy, the evaluators
kitaru experiment create cheaper-model \
  --evaluator decision-check@latest --evaluator cost@latest \
  --override '{"model": {"anthropic:claude-sonnet-4-5": "openai:gpt-5-nano"}}' \
  --tool-policy '{"default": {"type": "history", "scope": "cohort_version", "on_miss": "fail"}}'

# Replay the whole population, both sides evaluated
kitaru experiment run start cheaper-model \
  --cohort-version <cohort-version-id> \
  --agent investigator@1 \
  --evaluate-baselines --wait --timeout 1800
```

Workers fan out one replay per session. When the run settles, every session in the cohort has a baseline column and a fork column: pass rates, cost, latency, both sides. Keep the change if it holds up across the cohort; reject it if quality drops more than cost does. The cohort version is immutable, so the numbers stay checkable — and the cohort that caught a failure becomes the regression gate that keeps it caught: `--wait` exits nonzero on failure, which makes the same command a CI gate.

## Let an agent drive it

Replay runs over both the CLI (`--output json` on every command) and an [MCP server](https://docs.zenml.io/kitaru/agent-native/mcp-server) with capability-gated tools. That means a coding agent (Claude Code, Codex, Cursor) can drive the loop itself: pull a recent session, reproduce it as a control, propose a change, fork it, compare evaluations, and decide whether to widen it to a cohort — the same steps you'd run by hand, just faster and over more runs. Give it the discipline this page describes — reproduce before you trust a diff, change one variable, keep the cohort as evidence — and it runs your experiments without inventing its own.
