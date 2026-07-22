---
description: Replay a real agent run with one thing changed to see what would have happened, then scale the winning change across recent runs.
icon: arrows-rotate
---

# Replay and improve

Replay is why the recording exists. Take a run that actually happened, change exactly one thing — a different model, a different prompt — re-execute it against your real code, and diff the result against the original. Because the rest of the run reproduces faithfully, the difference you see is your change, not replay noise.

This is the part that other tooling can't do. An eval re-scores outputs after the fact. Replay re-executes the actual run with one input swapped, so you find out what *would have happened* if you'd shipped the change. Then you scale that decision across a filtered set of recent runs and keep the version that wins. The runs you already have in production are the test bed.

{% hint style="info" %}
Replay reads back the durable checkpoints written on the original run — that's the whole reason a run gets recorded. If you haven't recorded one yet, start with the [durable agent](01-durable-agent.md) stage, which mints the recording this page replays.
{% endhint %}

## Three runs, not two

It's tempting to think of replay as two runs: the original and your changed one. It's actually three, and the middle one is what makes the result trustworthy.

| Run | What it is | Role |
|---|---|---|
| **Observed** | The original recorded run | What actually happened |
| **Reproduced** | Replay with no change | The control — proves replay is faithful |
| **Forked** | Replay with exactly one thing changed | Your change |

You diff **Forked** against **Reproduced**, not against **Observed**. The reproduced run is the control that isolates your variable: because it replays the same recording with nothing swapped, it should land exactly where the observed run did.

**If the reproduced run doesn't match the observed baseline, stop.** A nondeterministic tool, an external state change, a time-dependent output — any of these means replay isn't faithful for this flow, and a diff built on it is untrustworthy. Don't act on it. Fix the source of nondeterminism first (guard the side effect, pin the value), then replay. Everything below assumes the reproduced run checks out.

The rest of this page walks the three runs in order: hold a recorded run, reproduce it as your control, fork it with one change, and diff.

## You start with a recorded run

Every flow run returns a handle. Hold onto its `exec_id` — that's the anchor you replay from.

```python
handle = flow.run(task="triage ticket 4821")
handle.wait()
print(handle.exec_id)  # e.g. "kr-9f3a1c"
```

The run wrote a checkpoint for each step. Suppose the flow has a `decide` checkpoint where the agent picks an action. That's the point we'll fork from.

## Reproduce: rerun with no change

Before you change anything, prove that the run reproduces. Replay it from the `decide` checkpoint with no overrides:

```python
baseline = flow.replay("kr-9f3a1c", at="decide")
baseline_exec_id = baseline.results[0].replay_exec_id
```

`at="decide"` re-executes the run from the `decide` checkpoint forward, reusing every recorded checkpoint upstream of it. The call returns a `ReplaySubmission`; `results[0].replay_exec_id` is the new execution it produced. This reproduced run is your **control** — it should land on the same decision the observed run did. If it doesn't, stop (see [Three runs, not two](#three-runs-not-two) above).

## Fork: change exactly one thing

Now fork the same run with a single override. Same starting point, same recorded upstream, one difference:

```python
forked = flow.replay(
    "kr-9f3a1c",
    at="decide",
    flow_overrides={"model": "openai:gpt-5-nano"},
)
forked_exec_id = forked.results[0].replay_exec_id
```

Everything up to `decide` is replayed from the original checkpoints. From `decide` forward, the flow re-executes for real — but now with the cheaper model. You're seeing what this run *would have done* under the change.

`flow_overrides` sets top-level flow inputs for the replay run, so this works when your flow exposes `model` as a parameter its checkpoints read. Other flow inputs go the same way — `flow_overrides={"model": "openai:gpt-5-nano", "prompt_profile": "trimmed_permissions"}` — but change one variable at a time if you want the diff to attribute cleanly. To target a single checkpoint or a single model call instead of a flow input, use `checkpoint_overrides` or `invocation_overrides`; see [Replay and Overrides](https://docs.zenml.io/kitaru/guides/replay-and-overrides) for the selector rules.

## Diff: did the decision move?

Compare the observed run, the reproduced control, and the fork in one call:

```python
import kitaru

execution_diff = kitaru.diff("kr-9f3a1c", baseline_exec_id, forked_exec_id)
print(execution_diff.urls)
```

`kitaru.diff` takes the original execution and the replays to compare against it, and reports the per-checkpoint differences plus compare URLs for the dashboard. Because the reproduced control matches the observed baseline, any difference between it and the fork is attributable to your one change. That's the whole point: a trustworthy comparison of a single variable.

### The CLI equivalent

The same loop runs from the terminal, which is what a coding agent or a CI job will use:

```bash
# Reproduce (control): no overrides
kitaru executions replay kr-9f3a1c --at decide

# Fork: one thing changed, passed as JSON
kitaru executions replay kr-9f3a1c --at decide \
  --flow-overrides '{"model": "openai:gpt-5-nano"}'

# Diff the original against its replay children
kitaru executions diff kr-9f3a1c <REPLAY_EXEC_ID>
```

`--flow-overrides` takes a JSON object of flow-input overrides — the CLI mirror of the keyword argument to `flow.replay(...)`. `--checkpoint-overrides` and `--invocation-overrides` cover the narrower selectors.

## Improve: scale the decision across a cohort

One replay tells you what a change did to one run. To decide whether to ship it, run the same change across a batch of recent runs and read the aggregate.

Start from a **filter over runs that actually happened** — recent executions of the flow you want to change:

```python
import kitaru

client = kitaru.KitaruClient()
recent = client.executions.list(flow="triage")   # filter to the runs you care about
exec_ids = [e.exec_id for e in recent]
```

Replay all of them at once with the same override and a shared tag. `flow.replay` accepts a list of executions; the tag labels the replay children so you can find them together:

```python
flow.replay(
    exec_ids,
    at="decide",
    flow_overrides={"model": "openai:gpt-5-nano"},
    tag="cheaper-model-trial",
    on_error="collect",   # keep going if one run can't replay
)
```

Then read the whole batch as one diff matrix. `diff_cohort` (also exported as `diff_matrix`) takes the original exec IDs and auto-discovers each one's replay children, so you get an original-vs-replay row per run:

```python
from kitaru.diff import diff_cohort

matrix = diff_cohort(exec_ids)
for row in matrix.rows:
    print(row)   # one original execution compared against its replay child
```

The same summary is available from the CLI with `kitaru executions diff-matrix <ID_1> <ID_2> ...`. Scan the rows for the thing you care about — did any restricted decision flip, did cost or latency move the wrong way — across realistic traffic rather than the one run you happened to look at.

The outcome is a decision backed by runs that actually happened: keep the change if it holds up across the cohort, reject it if quality drops more than cost does. **The diff matrix is your regression evidence** — it's the record of what the change did to real runs, so keep it attached to the change you ship.

{% hint style="warning" %}
**Roadmap, not yet shipped:** forcing a *specific* recorded call to fail (a per-call `raise_` mock, for testing error handling on a historical run) is planned but not available today. What *is* shipped: overriding a checkpoint or a single call's `input`, `output`, `code`, or `model` through `checkpoint_overrides` / `invocation_overrides`. Don't write code against a per-call failure mock yet.
{% endhint %}

## Let an agent drive it

Replay runs over both the CLI and an MCP server. That means a coding agent (Claude Code, Codex, Cursor) can drive the loop itself: pull a recent run, reproduce it as a control, propose a change, fork the run, diff the two, and decide whether to widen it to a cohort — the same steps you'd run by hand, just faster and over more runs.

Point your agent at Kitaru's MCP server and it can hill-climb toward a cheaper, safer agent on its own. Give it the discipline this page describes — reproduce before you trust a diff, change one variable, keep the matrix as evidence — and it runs your experiments without inventing its own. See the [Kitaru MCP server reference](https://docs.zenml.io/kitaru/agent-native/mcp-server) for the available tools.
