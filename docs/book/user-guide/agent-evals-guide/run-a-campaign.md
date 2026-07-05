---
description: Run Harbor agent-eval campaigns as ZenML pipelines on your sandbox.
icon: gauge-high
---

# Run an eval campaign

[Harbor](https://www.harborframework.com/) is an agent-evaluation framework: a *task* is one containerized problem with a verifier, a *trial* is one agent attempt on one task, and a *job* runs a set of trials. The `harbor` integration runs Harbor eval campaigns as ZenML pipelines: ZenML owns the outer orchestration — matrix expansion, per-shard steps, retries, caching, artifacts, reports — while Harbor keeps the trial eval kernel (task loading, agent loop, verifier, reward). Every trial's container is backed by whatever [Sandbox](https://docs.zenml.io/stacks) flavor is on your active stack.

```bash
zenml integration install harbor -y   # requires Python 3.12+
```

## A campaign in ~10 lines

```python
from zenml import pipeline
from zenml.integrations.harbor.steps import (
    build_harbor_matrix,
    build_harbor_report,
    run_harbor_shard,
)


@pipeline(dynamic=True)
def agent_evals(tasks: list[str], agents: list[dict], trials_per_cell: int = 3) -> None:
    shards = build_harbor_matrix(
        tasks=tasks, agents=agents, trials_per_cell=trials_per_cell
    )
    results = run_harbor_shard.map(shard=shards)
    build_harbor_report(results=results)
```

`build_harbor_matrix` expands the campaign into *shards* — up to `trials_per_step` trials of one (task, agent, configuration) cell. Each shard runs as one mapped step and one Harbor job, with Harbor fanning the shard's trials out concurrently inside the step (`n_concurrent_trials`). Tasks can be local task directories, pinned `git+URL@COMMIT:SUBPATH` refs, or a whole registry dataset:

```python
agent_evals(
    dataset={"name": "terminal-bench-sample", "version": "2.0", "n_tasks": 3},
    agents=[{"name": "oracle"}],
)
```

Datasets expand through Harbor's own resolver, so task sets and commit pins match `harbor run` exactly, and each shard fetches only its own pinned task at runtime.

## Why shards are the retry and cache unit

Shards are packed so that one shard never mixes campaign cells, and every trial carries a stable content-based identity (task + agent + model + kwargs + env + index). Step caching is left enabled on `run_harbor_shard`: rerunning an identical campaign cache-hits every shard that already completed and executes only failed or new ones — extending a campaign (more trials, more tasks, another agent) reruns just the delta.

How caching, error handling, and cross-run comparison compose into a recurring benchmark is the subject of [Benchmark operations](benchmark-ops.md).

## What lands where

* Each shard produces a `HarborShardResult` artifact: a flat summary (per-trial rewards, errors, tokens, cost) plus Harbor's full job directory — agent and verifier logs, trajectories — archived in the artifact store. `result.download_jobs_dir(target)` restores the tree on demand; loading the artifact never unpacks it eagerly.
* Each shard step logs `harbor.*` metadata (task, agent, model, trial counts, mean reward, cost), making campaigns queryable: `client.list_run_steps(pipeline_run_id=..., run_metadata=["harbor.mean_reward:lt:1"])`.
* `build_harbor_report` renders a Markdown campaign report — one row per cell with mean rewards and cost totals — on the run page.

## Running real LLM agents

Harbor's agents read their provider key from the **host** environment and inject it into the sandbox — `claude-code` reads `ANTHROPIC_API_KEY`, `terminus-2` reads the key matching its litellm model prefix. The model rides the agent spec:

```python
agent_evals(
    dataset={"name": "terminal-bench-sample", "version": "2.0", "n_tasks": 1},
    agents=[{"name": "claude-code", "model_name": "claude-sonnet-4-5"}],
)
```

Token usage and cost flow into the trial results, the `harbor.cost_usd` step metadata, and the report's cost column. The hermetic `oracle` agent (runs each task's reference solution) and `nop` agent (does nothing) need no keys — useful for validating a campaign setup before spending tokens. As with any sandbox environment value, the key is readable by code running inside the sandbox.

## The environment bridge

Trials execute through `ZenMLSandboxEnvironment`, an implementation of Harbor's environment interface that routes `start`/`exec`/`upload`/`download`/`stop` through `Client().active_stack.sandbox`. It is a regular Harbor environment provider, so it also works outside ZenML pipelines:

```bash
harbor run --environment-import-path zenml.integrations.harbor.environment:ZenMLSandboxEnvironment ...
```

Known limitations, preserved deliberately: Harbor resource requests (`cpus`/`memory_mb`/`gpus`) are not translated to sandbox settings, tasks with `allow_internet=false` are refused, `exec(user=...)` is ignored, task-level `docker_image` overrides are Modal-only, and multi-step tasks or separate verifier sandboxes are rejected with `NotImplementedError`. The sandbox image must provide `bash`, `timeout`(1), and `tar`.

## Learn more

* The [harbor_agent_evals example](https://github.com/zenml-io/zenml/tree/main/examples/harbor_agent_evals) — a runnable campaign with an oracle-vs-nop head-to-head default and real Terminal-Bench invocations.
* [Harbor's documentation](https://www.harborframework.com/docs) and dataset registry (`harbor dataset list`).
