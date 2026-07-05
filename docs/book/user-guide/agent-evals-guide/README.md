---
description: Run agent-eval campaigns as pipelines — benchmarks, baselines, regression gates, and the path from eval results into training.
icon: gauge-high
---

# Agent evals guide

Frameworks like [Harbor](https://www.harborframework.com/) have made the hard part of agent evaluation tractable: defining a containerized task, running an agent against it, and scoring the attempt. What they deliberately leave to you is everything *around* a single scored attempt — and that's where evaluation efforts usually stall. One `harbor run` is easy. A benchmark you trust enough to gate releases on is an operations problem:

* **Scale**: a real campaign is tasks × agents × models × trials — hundreds or thousands of containerized attempts per run.
* **Failure**: at that fan-out, something always breaks. Losing a whole campaign to one hung container, or rerunning everything to retry the failed 5%, makes nightly benchmarks too expensive to keep.
* **Comparison**: scores only matter against last night, the baseline model, or the other configuration — which requires results that are versioned, joinable, and queryable, not scattered across log directories.
* **Consequence**: an eval that doesn't gate a release or feed the next training run is a dashboard nobody reads.

This guide shows how to run agent evals as ZenML pipelines: Harbor keeps the trial eval kernel (task loading, agent loop, verifier, reward), while ZenML owns the campaign — matrix expansion, per-shard steps with retries and caching, versioned artifacts, queryable metadata, reports, and lineage from a benchmark score back to the exact trials that produced it.

## What's in this guide

1. [Run an eval campaign](run-a-campaign.md) — install the integration, compose a campaign pipeline in ~10 lines, run local tasks and registry benchmarks (Terminal-Bench and friends), and evaluate real LLM agents with cost tracking.
2. [Benchmark operations](benchmark-ops.md) — the recurring-campaign playbook: rerun only what failed, extend campaigns incrementally, join results across runs by trial identity, and fail the pipeline when an agent regresses.
3. [From evals to training](evals-to-training.md) — treat campaign results as training signal: SFT datasets from winning trajectories, rejection-sampling loops, config sweeps, and eval-gated promotion through the Model Control Plane.

Everything in this guide runs on the [Sandbox](../../component-guide/sandboxes/README.md) stack component — trials execute in whatever isolated backend your stack provides (Modal, Kubernetes, ...) without Harbor knowing the difference. The [harbor_agent_evals example](https://github.com/zenml-io/zenml/tree/main/examples/harbor_agent_evals) is the runnable companion: a hermetic head-to-head that needs no API keys, plus real Terminal-Bench invocations.
