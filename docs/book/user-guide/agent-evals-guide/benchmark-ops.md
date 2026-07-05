---
description: Operate recurring benchmarks — rerun only what failed, extend campaigns incrementally, and gate on regressions.
icon: rotate
---

# Benchmark operations

A benchmark you run once is a demo. A benchmark you run every night, trust when it breaks, and compare across weeks is infrastructure. This page is the operations playbook for recurring campaigns: what reruns, what caches, how results join across runs, and how a score drop becomes a failed pipeline instead of a quiet dashboard change.

## Rerun only what failed

Every shard step is cached on its content: the shard's trial identities, the step code, and its parameters. Rerunning an identical campaign therefore cache-hits every shard that already completed and executes only the ones that didn't — after an infrastructure hiccup kills 5% of a 500-trial campaign, the rerun costs 5%, not 100%.

The same mechanics make campaigns *extendable*. Raise `trials_per_cell`, add an agent, add tasks: only the shards whose trial identities are new execute; everything already answered stays answered. Identities are content-based, so this works across invocation styles too — a CLI rerun cache-hits shards a programmatic run produced.

One caveat to internalize: an **errored** trial (an infrastructure failure — sandbox unreachable, image pull failed — as opposed to a low reward) still *completes* its shard by default, and that completed result gets cached. For unattended campaigns, pass `fail_on_trial_error=True`:

```python
run_harbor_shard.map(shard=shards, fail_on_trial_error=True)
```

Now an errored shard fails its step — no cache entry, so the next run re-executes exactly the errored slices. Before raising, the step rescues the shard result and its full log archive as a manual artifact named `harbor_shard_result_<shard_id>_failed`; load it and call `download_jobs_dir()` to debug what broke. Combine with step retries for transient flakiness:

```python
from zenml.config.retry_config import StepRetryConfig

run_harbor_shard.with_options(retry=StepRetryConfig(max_retries=2, delay=10))
```

## Nightly campaigns

A recurring benchmark is just the campaign pipeline on a trigger — CI cron is the simplest reliable option, and because of the caching semantics above, a nightly run that overlaps yesterday's campaign only pays for what changed. (Scheduling *dynamic* pipelines natively is orchestrator-dependent; triggering the run from CI sidesteps that entirely.)

## Query results across runs

Each shard step logs flat `harbor.*` metadata — task, agent, model, trial counts, mean reward, cost — which makes campaigns queryable without loading artifacts:

```python
from zenml.client import Client

losing = Client().list_run_steps(
    pipeline_run_id=run_id,
    run_metadata=["harbor.mean_reward:lt:1"],
)
```

For anything deeper, load the `HarborShardResult` artifacts: per-trial rewards, exceptions, token counts, and the archived Harbor job trees.

## Regression gates

Because trial identities are stable across runs, tonight's campaign joins directly against any baseline run of the same campaign — and a reward drop can fail the pipeline:

```python
@step
def regression_gate(
    current: list[HarborShardResult], baseline_run_id: str, tolerance: float = 0.05
) -> None:
    baseline = {}
    run = Client().get_pipeline_run(baseline_run_id)
    for name, step_ in run.steps.items():
        if name.startswith("map:run_harbor_shard:"):
            for t in step_.outputs["harbor_shard_result"][0].load().trials:
                baseline[t.trial_identity] = t.rewards or {}

    for shard in current:
        for t in shard.trials:
            then = baseline.get(t.trial_identity, {}).get("reward")
            now = (t.rewards or {}).get("reward")
            if then is not None and now is not None and now < then - tolerance:
                raise RuntimeError(
                    f"Regression on {t.task_name}: {then:.2f} -> {now:.2f}"
                )
```

Append it after `run_harbor_shard.map(...)` and the campaign becomes a gate: visible when it fails, attached to the exact trials that regressed, and alertable like any failed pipeline. Promote a run to "baseline" by tagging it or recording its id wherever your team keeps release state — the join needs nothing more than the run id.

The same join powers side-by-side comparison beyond gating: two models on the same campaign share task identities per cell, so "where did the fine-tune help and where did it hurt" is a dictionary merge, not a data-wrangling project.

Next: campaign results are also training signal — [From evals to training](evals-to-training.md).
