---
description: Replay a real agent run with one thing changed to see what would have happened, then scale the winning change across recent runs.
icon: arrows-rotate
---

# Replay and improve

Once a run is recorded, you can replay it. Take a real run, change exactly one thing — a different model, a different prompt — re-execute it from a checkpoint, and diff the result against the original. Because the rest of the run reproduces faithfully, the difference you see is your change, not replay noise.

This is the part that other tooling can't do. An eval re-scores outputs after the fact. Replay re-executes the actual run from a durable checkpoint with one input swapped, so you find out what *would have happened* if you'd shipped the change. Then you scale that decision across recent runs and keep the version that wins.

{% hint style="info" %}
Replay works because every model call and tool call from the original run is a durable checkpoint. If you haven't recorded a run yet, start with the [durable agent](01-durable-agent.md) stage — that's the RUN beat this page builds on.
{% endhint %}

## You start with a recorded run

Every flow run returns an execution handle. Hold onto its `exec_id` — that's the anchor you replay from.

```python
exec = flow.run(task="triage ticket 4821").wait()
print(exec.exec_id)  # e.g. "exec_9f3a1c"
```

The run wrote a checkpoint for each step. Suppose the flow has a `decide` checkpoint where the agent picks an action. That's the point we'll fork from.

## Rerun: reproduce the run with no change

Before you change anything, prove that the run reproduces. Replay it from the `decide` checkpoint with no overrides:

```python
rerun = flow.replay(exec.exec_id, from_="decide")
```

This re-executes the run from `decide` forward, replaying recorded checkpoints faithfully. A clean rerun is your **control**: it should land on the same decision the original run did. If it doesn't reproduce, stop — see [Why three runs, not two](#why-three-runs-not-two) below.

## Replay: change exactly one thing

Now fork the same run with a single override. Same starting point, same inputs, one difference:

```python
forked = flow.replay(
    exec.exec_id,
    from_="decide",
    model="openai:gpt-5-nano",
    prompt_profile="trimmed_permissions",
)
```

Everything up to `decide` is replayed from the original checkpoints. From `decide` forward, the flow re-executes for real — but now with the cheaper model and the trimmed prompt. You're seeing what this run *would have done* under the change.

## Diff: did the decision move?

Compare the fork against your control rerun:

```python
delta = forked.diff(rerun)
print(delta)
```

The diff shows whether the decision changed, plus the cost and latency deltas. Because the control reproduced the baseline, any difference is attributable to your one change. That's the whole point: a trustworthy diff of a single variable.

### The CLI equivalent

The same loop runs from the terminal, which is what a coding agent or a CI job will use:

```bash
# Rerun (control): no overrides
kitaru executions replay --from decide exec_9f3a1c

# Forked replay: one thing changed, passed as JSON
kitaru executions replay --from decide exec_9f3a1c \
  --args '{"model": "openai:gpt-5-nano", "prompt_profile": "trimmed_permissions"}'
```

`--args` takes a JSON object of input overrides — the CLI mirror of the keyword arguments to `flow.replay(...)`.

## Why three runs, not two

It's tempting to think of replay as two runs: the original and your changed one. It's actually three, and the middle one is what makes the result trustworthy.

| Run | What it is | Role |
|---|---|---|
| **Observed** | The original recorded run | What actually happened |
| **Reproduced** | `flow.replay(..., from_="decide")` with no change | The control — proves replay is faithful |
| **Forked** | `flow.replay(..., from_="decide", model=...)` | Your change |

You diff **Forked** against **Reproduced**, not against **Observed**. The reproduced run is the control that isolates your variable. If the reproduced run doesn't match the observed baseline — a nondeterministic tool, an external state change, time-dependent output — then the replay isn't faithful, and a diff built on it is untrustworthy. Don't act on it. Fix the source of nondeterminism first, or pin it, then replay.

## Improve: scale the decision across a cohort

One replay tells you what a change did to one run. To decide whether to ship it, run the same change across a batch of recent runs and measure the aggregate.

{% hint style="info" %}
The `cohort`, `experiment`, `Recipe`, and metric helpers below are an **example pattern** built on the SDK primitives above (`flow.replay` and `diff`). They show one way to structure a cohort experiment; they aren't a separate core API.
{% endhint %}

```python
from kitaru_recipes import cohort, Recipe, cost, latency, quality_judge

# Take the last 50 runs of this flow as the cohort.
batch = cohort(flow, last=50)

# Define the one change to test, and how to score it.
recipe = Recipe(
    change={"model": "openai:gpt-5-nano", "prompt_profile": "trimmed_permissions"},
    from_="decide",
    metrics=[cost, latency, quality_judge],
)

result = batch.experiment(recipe)
print(result.summary())
```

For each run in the cohort, the experiment does the same rerun-then-fork-then-diff loop and aggregates the metrics: total cost, p50/p95 latency, and a quality score from an LLM judge. You get a side-by-side that answers the real question — does the cheaper model hold quality across realistic traffic, or only on the one run you happened to look at?

Keep the version that wins. Reject it if quality drops more than cost does.

{% hint style="warning" %}
**Roadmap, not yet shipped:** overriding a *specific* tool call to return a fake value or to fail (per-tool-call `output=` / `raise_=` mocks) is planned but not available today. The shipped overrides are flow-level inputs like `model` and `prompt_profile`. Don't write code against per-tool-call mocks yet.
{% endhint %}

## Let an agent drive it

Everything on this page — rerun, replay, diff, cohort experiments — is exposed over both the CLI and an MCP server. That means a coding agent (Claude Code, Codex, Cursor) can drive the loop itself: pull a recent run, propose a change, replay it against the control, read the diff, and decide whether to widen it to a cohort.

Point your agent at Kitaru's MCP server and it can hill-climb toward a cheaper, safer agent on its own — running the same experiments you'd run by hand, just faster and over more runs. See the [Kitaru MCP server reference](https://docs.zenml.io/kitaru/agent-native/mcp-server) for the available tools.
