# B3 — Harbor→RL trajectory exporter (2026-07-09)

Spike findings for Track B / B3 (`framework_breakout.md`). Branch `spike/b3-exporter` off `spike/b1-harbor-k8s` (which forks PR #5029); like B1, this branch merges nowhere — this document is the deliverable. Everything ran against the staging Pro server (project `rl-spike`), stack `rl-spike-harbor-k8s` (local orchestrator, local artifact store, Kubernetes sandbox on the staging EKS cluster), Python 3.14 venv with Harbor 0.8.0.

## What was built

`export_episodes.py` next to the example: a ZenML pipeline that converts the shard artifacts of finished `harbor_agent_evals` campaign runs into one accumulating dataset artifact named `rl_episode_candidates`.

```
python export_episodes.py <campaign_run_name_or_id> [more runs...]
```

One record per trial, keyed by #5029's sha256 `trial_identity` (reused verbatim, no second identity scheme), carrying: pinned task ref (`git+URL@COMMIT:SUBPATH`), agent + model, reward dict + primary reward, errored flag, sandbox flavor/image (best-effort — see finding 3), source run id/name, token/cost/timing fields, and a `TrajectoryRef` = (shard artifact version id, trial dir name). The reference alone restores the full trajectory: load the shard artifact, `download_jobs_dir()`, cd into the trial dir — verified end-to-end (agent log, verifier log, `reward.txt` all present).

Accumulation is append-only: each export consumes the latest `rl_episode_candidates` version as an input and appends new records, deduplicated on `(trial_identity, shard_artifact_version_id)`. Keying dedupe on the artifact version (not the source run) means a cache-hit campaign rerun — same artifact versions, new run — adds nothing, while a genuine re-execution of the same campaign cell (new artifact version) lands as a new joinable record. Both behaviors were exercised (see ledger below).

## Verdict on the B3 question

**Yes — the lineage edge from an eval run to a training-data artifact is expressible today, and a human can follow it in the dashboard — but only after routing around two platform gaps** (findings 1a/1b). The export run's `normalize_shard` steps consume the *original* shard artifact versions produced by the campaign run (verified by ID: campaign outputs ≡ export inputs), so each shard artifact now shows two consumers — the campaign's own report step and the later export run — and each dataset version chains to its predecessor through the `previous` input. "This reward came from this verifier at this task version, and here is the resulting training example" holds end-to-end, with one honest exception: *which sandbox image* the trial ran in is not currently recorded anywhere (finding 3).

Stop-condition check: everything was read from documented surfaces — the integration's own `HarborShardResult`/`HarborTrialResult` models and `download_jobs_dir()`. No Harbor internals were scraped. **Keep.**

## Demonstration ledger (dataset versions on staging, project `rl-spike`)

| Version | Action | Result |
|---|---|---|
| v1 | export B1 hermetic head-to-head (`70317b92`) | 6 records (oracle 1.0 ×3, nop 0.0 ×3) |
| v2 | export B1 terminal-bench run (`af243613`) | +6 → 12 records, 12 identities |
| v3 | re-export `70317b92` (idempotency) | +0 |
| v4 | export B1's cache-hit rerun (`b8e66f96`) | +0 (same artifact versions — dedupe key does its job) |
| v5 | export fresh chess-best-move campaign via direct `git+` ref | +2 records — but **join failed**, 14 identities (finding 2) |
| v6 | export fresh *uncached* chess-best-move campaign via the dataset route | +2 → 16 records, still 14 identities: identities `578b5292…`/`8072cc62…` now each hold 2 attempts from 2 campaign runs, joinable by identity |

v6 is the regression-suite property working: the same pinned task + agent config, attempted in campaigns run 70 minutes apart, lands as two records under one identity with independent trajectories.

## Findings

### 1a — a `List[ArtifactVersionResponse]` step input is silently a parameter (BREAKAGE-grade)

The natural single-step exporter — `export(shard_results: List[HarborShardResult])` fed with artifact versions fetched by `Client().get_pipeline_run(...)` — fails with `StepInterfaceError`. `BaseStep._parse_call_args` (`src/zenml/steps/base_step.py:455-486`) resolves a *single* `ArtifactVersionResponse` into a real (loaded, lineage-recorded) input, and recognizes `List[StepArtifact]`, but a list of artifact version responses falls through to the plain-parameters branch: raw response objects reach the step function, no loading, no lineage. Historical-artifact fan-in is exactly what any "consume a previous run's outputs" pipeline needs.

### 1b — `.map()` cannot map over historical artifacts

The second-choice shape, `normalize_shard.map(shard=shard_artifacts)`, is explicitly unsupported: `expand_mapped_inputs` (`src/zenml/execution/pipeline/dynamic/utils.py:423-459`) only maps over `OutputArtifact`s of the current run and raises "No inputs to map over found" for anything else — its own warning text says mapping over non-step-output artifacts "is currently not supported."

**Workaround that works (and is fine at this scale):** a plain Python loop in the dynamic pipeline function calling the step once per artifact version — single artifact-version inputs resolve correctly. Cost: one step run per shard instead of one mapped fan-out; at 89-task scale that is 89+1 exporter steps, which collides with E3's fixed-cost-per-step finding. Escalation: should list-of-artifact-version inputs and/or map-over-history be supported? Both look like input-resolution plumbing, not architecture.

### 2 — the sha256 `trial_identity` join key breaks across task-specification routes (core, #5029)

`trial_identity` hashes `TaskRef.model_dump(exclude_none=True)`. Harbor's dataset resolver stamps `source: "terminal-bench-sample"` into the ref; a user-supplied `git+URL@COMMIT:SUBPATH` ref for the *byte-identical pinned task* doesn't carry it. Same task, same agent, same trial index → different identity (dataset ledger v5). Related: local-path tasks hash their absolute path, so identities are checkout- and machine-specific (B1's `tasks/hello` trials can never join mine). Escalation: hash only the canonical pin coordinates — `to_string()` (git_url + commit + subpath, or path) — or normalize the ref before hashing. Until then, "regression suite" joins only work if every campaign specifies tasks the same way.

### 3 — no sandbox-image provenance anywhere (core, sharpened from B1)

The Harbor job archive records neither the sandbox flavor nor the resolved image: the trial `config.json` shows only the bridge's `import_path`, and `result.json` has no image field. The exporter falls back to the sandbox component config of the producing run's stack, and that fallback is *provably wrong* for image-pinned tasks: the chess-best-move records say `sandbox_image: python:3.11-slim` (the component default) while the trial actually ran in the Terminal-Bench image via B1's `docker_image` translation patch. B3's product claim — "this reward came from this task in this sandbox image" — cannot be made truthfully today. Escalation: the bridge (or `run_harbor_shard`) should record the resolved flavor + image into the shard/trial result at execution time; it is the one party that knows.

### 4 — `task_checksum` exists in the archive but not in the flat summary (one-line lift)

Harbor's trial `result.json` carries `task_checksum`, a content hash of the task itself — a natural content-addressed complement to the coordinate-based identity (it would also solve the local-path half of finding 2). `HarborTrialResult.from_harbor` doesn't surface it, so using it requires unpacking every archive. Worth a one-line addition to the integration model.

### 5 — small UX residue

Explicitly passing `previous=None` (and the per-shard provenance dicts) into steps of a dynamic pipeline uploads each as an unnamed `external_*` artifact — six junk artifact versions per export run cluttering the lineage view. Cosmetic, but it makes the "human follows the lineage" story noisier than it should be.

## Design decisions (for whoever productizes this)

- **Trajectory by reference, not by copy.** Records point at (shard artifact version, trial dir); the heavy job archive stays where the materializer put it. The dataset stays KB-sized and the pointer survives because artifact versions are immutable.
- **Dedupe key `(trial_identity, shard_artifact_version_id)`.** Identity = what was attempted; artifact version = which physical execution. Cache hits add nothing; real re-attempts accumulate.
- **Errored trials are kept, flagged** (`errored`, `exception_type`), not dropped — whether failures belong in a training set is the consumer's call, and B1's finding 2 (errored trials invisible to receipts) argues for keeping them loud.
- **Primary reward = the `reward` key** of Harbor's reward dict (what verifiers write to `reward.txt`), falling back to a single-entry dict's only value.
- Not built, per the spec's own scoping: the stub `grpo_update` consumer, and anything multi-step (the integration still rejects multi-step tasks with `NotImplementedError`).

## Escalation questions collected (for the Hamza/Michael conversation)

1. Should list-of-artifact-version step inputs / map-over-historical-artifacts be platform features? (Finding 1a/1b — the blocker between "lineage is expressible" and "lineage is natural to express".)
2. Should `trial_identity` hash canonical pin coordinates only? (Finding 2 — without this, #5029's cross-run join key silently fragments.)
3. Who records sandbox flavor/image into the trial result? (Finding 3 — today nobody can answer "which image produced this reward", which undercuts both the eval story and the training-data story.)
