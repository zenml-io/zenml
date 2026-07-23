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
from kitaru import KitaruClient

client = KitaruClient()
control = client.executions.get(rerun.exec_id)
candidate = client.executions.get(forked.exec_id)

# Compare their decision fields, per-checkpoint outputs, cost, and latency.
```

Because the control reproduced the baseline, any difference between it and the candidate is attributable to your one change. That's the whole point: a trustworthy comparison of a single variable.

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

The PydanticAI replay example in the kitaru repo (`examples/end_to_end/pydantic_replay_fork`) wraps this loop as `run_cohort`: for each recent run it reproduces the baseline, replays the variant, and scores the pair with bring-your-own metrics.

```python
from cohort import run_cohort
from utils import cost, latency, quality_judge

# exec_ids: recent runs of your flow (e.g. from KitaruClient.executions.list)
report = run_cohort(
    exec_ids,
    baseline_model="openai:gpt-5-mini",
    variant_model="openai:gpt-5-nano",
    variant_prompt_profile="trimmed_permissions",
    metrics=[cost, latency, quality_judge],
)
report.summary()      # per-metric baseline-vs-variant deltas + an "is it better?" verdict
report.regressions()  # the metrics (and decision changes) that got worse
```

{% hint style="info" %} `run_cohort` and the metric callables live in the example, not in the `kitaru` package — they're a pattern built on the real `flow.replay` and `KitaruClient`. Copy or adapt them; metrics are just `metric(baseline, variant) -> MetricDelta` callables, so you bring your own.
{% endhint %}

For each run, the cohort reproduces and replays the same way, then aggregates: total cost, latency, and a quality score from an LLM judge. You get the answer to the real question — does the cheaper model hold quality across realistic traffic, or only on the one run you happened to look at?

Keep the version that wins. Reject it if quality drops more than cost does.

{% hint style="warning" %}
**Roadmap, not yet shipped:** overriding a *specific* tool call to return a fake value or to fail (per-tool-call `output=` / `raise_=` mocks) is planned but not available today. The shipped overrides are flow-level inputs like `model` and `prompt_profile`. Don't write code against per-tool-call mocks yet.
{% endhint %}

## Let an agent drive it

Replay runs over both the CLI and an MCP server. That means a coding agent (Claude Code, Codex, Cursor) can drive the loop itself: pull a recent run, propose a change, replay it against the control, compare the results, and decide whether to widen it to a cohort.

Point your agent at Kitaru's MCP server and it can hill-climb toward a cheaper, safer agent on its own — running the same experiments you'd run by hand, just faster and over more runs. See the [Kitaru MCP server reference](https://docs.zenml.io/kitaru/agent-native/mcp-server) for the available tools.
