---
description: Turn Harbor eval campaigns into training signal — regression gates, SFT from winning trajectories, rejection sampling, and eval-gated promotion.
icon: arrows-spin
---

# From evals to training

Evaluating an agent is rarely the end goal. The campaign you ran in [Run an eval campaign](run-a-campaign.md) produced more than a report: every trial left behind a reward, a full trajectory, token counts, and a cost — all versioned in your artifact store, all joined by a stable trial identity. That is training signal, and the loop that consumes it is the same loop ZenML has always run for ML: **evaluate → select → build a dataset → train → re-evaluate → promote**. Harbor scores one attempt; ZenML operationalizes the flywheel around it.

This page maps the loop onto the primitives you already have. Nothing here requires new framework features — each stage is a pipeline consuming the previous stage's artifacts.

## What a campaign leaves behind

Each shard's `HarborShardResult` carries two layers:

* A **flat summary** — per-trial `rewards`, `exception_type`, `n_input_tokens` / `n_output_tokens`, `cost_usd`, sandbox provenance (`sandbox_flavor`, `sandbox_docker_image` — the image that actually backed the trial, which only the environment bridge knows for tasks that pin a `docker_image`), and a `trial_identity`: a content hash of (pinned task coordinates, agent, model, kwargs, env, trial index). The task enters as its canonical `git+URL@COMMIT:SUBPATH` pin, so the same task hashes identically whether it came from a dataset expansion or a direct ref — this is the join key for every comparison below. Harbor's `task_checksum` (a content hash of the task definition itself) rides along as the content-addressed complement.
* The **archived job tree** — Harbor's full per-trial record, including the agent's rollout (for CLI agents like `claude-code`, the complete `stream-json` interaction log) and the verifier's output. `result.download_jobs_dir(target)` restores it on demand.

## SFT from winning trajectories

Rewards are labels. A campaign with `trials_per_cell > 1` is a filtered dataset generator: keep the trajectories that scored, discard the rest.

```python
@step
def build_sft_dataset(
    results: list[HarborShardResult],
) -> Annotated[list[dict], "sft_dataset"]:
    examples = []
    for shard in results:
        winning = {
            t.trial_name for t in shard.trials
            if (t.rewards or {}).get("reward", 0) >= 1.0
        }
        if not winning:
            continue
        jobs = shard.download_jobs_dir(Path(tempfile.mkdtemp()))
        for trial_dir in jobs.iterdir():
            if trial_dir.name in winning:
                rollout = (trial_dir / "agent" / "claude-code.txt").read_text()
                examples.append({"task": shard.spec.task.display_name, "rollout": rollout})
    return examples
```

From here it is the standard ZenML fine-tuning story: the dataset is a versioned artifact, the fine-tune step is whatever your training stack is (see the [LLMOps guide](https://docs.zenml.io/user-guides/llmops-guide) for finetuning pipelines), and — the part that closes the loop — the re-eval is the *same campaign* with the new model:

```python
agent_evals(
    dataset={"name": "terminal-bench-sample", "version": "2.0"},
    agents=[{"name": "claude-code", "model_name": finetuned_model_ref}],
)
```

Different `model_name` means different trial identities, so both generations of results coexist and compare cleanly.

## Rejection sampling and offline RL

`trials_per_cell` is a rollout generator with a reward oracle attached. Set it to 16, and each campaign cell yields 16 scored rollouts of the same task — exactly the input shape for best-of-N selection, rejection-sampling fine-tuning, or offline preference methods (winning vs. losing rollouts of the same task form natural preference pairs). The loop is a recurring pipeline:

1. Campaign with high `trials_per_cell` (sharding keeps each slice retryable and cached).
2. Selection step: filter or pair rollouts by reward.
3. Training step on the selected set.
4. Re-eval campaign with the updated model; the [regression gate](benchmark-ops.md#regression-gates) becomes your improvement meter.

Each iteration is one pipeline run, so the whole optimization history — which rollouts trained which checkpoint, which checkpoint scored what — is lineage you can walk, not tribal knowledge.

## Config and prompt optimization

Not every improvement loop touches weights. The campaign matrix treats distinct agent configurations as distinct experiments — `agent_kwargs` and `agent_env` are part of the trial identity — so sweeping system prompts, tool budgets, or skill sets is just a wider `agents` list:

```python
agents=[
    {"name": "claude-code", "model_name": "claude-sonnet-4-5", "kwargs": {...variant_a}},
    {"name": "claude-code", "model_name": "claude-sonnet-4-5", "kwargs": {...variant_b}},
]
```

The report gives each configuration its own row; `harbor.cost_usd` metadata turns it into reward-per-dollar. Wrap the sweep in an outer loop (grid, Optuna, an LLM proposing the next variant) and you have prompt optimization with full provenance.

## Eval-gated promotion

The last arrow in the loop is deployment. Attach campaign metrics to a [Model Control Plane](https://docs.zenml.io/concepts/models) version and promote on thresholds — the same gate pattern teams use for classic ML models, now keyed on agent benchmark scores:

```python
log_metadata(
    metadata={"benchmark": "terminal-bench-sample", "mean_reward": mean_reward},
    infer_model=True,
)
```

A model version that never beat the benchmark never reaches production, and the run that proved it is one click from the model page.

## Where this is heading

Harbor's own roadmap points the same direction — trace export and training-format standardization are active upstream topics. As those land, the `build_sft_dataset` sketch above becomes a parser swap, not an architecture change: the campaign artifacts already contain everything downstream training needs.
