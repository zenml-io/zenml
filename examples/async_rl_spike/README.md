# Async RL spike: disaggregated GRPO post-training on ZenML

A toy-but-real RL loop, split into **two pipelines that run as separate
processes** and coordinate only through a shared directory on disk. A small
Qwen model is post-trained (GRPO + LoRA) to write better ZenML dynamic
pipelines. The model quality is not the point. The point is exercising an
**asynchronous, disaggregated** RL topology on ZenML: generation and
training decoupled, a bounded pool of policy versions, and graceful
retirement of stale ones.

## Terms you need (30 seconds)

- **Episode / rollout**: one attempt. The model gets a task prompt and
  produces one candidate `pipeline.py`. Single-turn, no follow-ups.
- **Group**: `group_size` independent attempts at the same task, sampled
  with temperature so they differ. GRPO's learning signal is the
  within-group comparison.
- **GRPO**: the training algorithm. Each episode's advantage is its reward
  minus the group mean.
- **LoRA adapter**: a few-MB add-on trained instead of the full model. A
  "version" here is one adapter directory plus a liveness marker.
- **logprobs**: the per-token log-probabilities the model assigned when it
  sampled a completion, computed against the version it generated with.
  These are what make the off-policy correction possible (see below).

## The two pipelines

- **Trainer** (`pipelines/trainer_pipeline.py`): bootstraps version 0, then
  loops `max_train_steps` times calling `train_step`. Each `train_step`
  pulls the freshest in-window rollout groups off the queue, runs one GRPO
  optimizer step, publishes a new adapter version, and retires versions
  past the staleness window. It owns the whole version lifecycle. TRL is a
  library, not an orchestrator: its `rollout_func` hook returns the
  pre-generated, pre-scored episodes, so TRL only does advantages, loss,
  and the gradient step.
- **Rollout** (`pipelines/rollout_pipeline.py`): waits for version 0, then
  continuously spins up `num_parallel` generator steps per wave. Each
  generator reads the current version, generates one group against it,
  scores it inside a sandbox (reward computed where the generated pipeline
  actually runs), and enqueues it. A generator whose version is retired
  mid-flight drops its group instead of crashing.

## Shared directory layout

Both pipelines take the same `--run-name`, which resolves to a
sub-directory of the active stack's artifact store. Every read and write
goes through ZenML's `fileio`, so weights, queue, and markers all live in
the artifact store and the same code coordinates over S3 or GCS the moment
the stack points there.

```
<artifact_store>/<run_name>/
  versions/v{n}/adapter/   + v{n}/LIVE (servable) | v{n}/RETIRED (shutting down)
  current                  atomic pointer: newest live version
  rollouts/pending/        generators drop complete groups here
  rollouts/claimed/        trainer moves a group here while consuming it
  STOP                     presence = drain and exit
```

Weights are staged local<->store around each step because torch reads and
writes local paths. Coordination files are read and written in place via
`fileio`.

A "version" stands in for a deployed vLLM instance. Here it is just a LoRA
adapter directory plus a `LIVE` marker. `max_versions` is the staleness
window: rollouts generated against a version older than the window are
dropped, and a version that ages out is retired, which is what makes
in-flight generation against it fail gracefully.

## Off-policy correction

Overlapping generation with training makes rollouts slightly off-policy: a
group is generated against version K but trained into version M (K <= M,
bounded by `max_versions`). This is handled, not ignored:

- Every episode carries the per-token `logprobs` from the version it was
  generated against. `train_step` hands those to TRL as the behavior
  policy, and GRPO computes the importance ratio against the current policy
  and applies PPO-style clipping. The trainer logs mean and max staleness
  per step so you can watch it.
- `max_versions` is the staleness bound: groups older than the window are
  dropped at claim time.
- Not covered yet: there is no KL-to-reference penalty (`beta=0`), and
  there is no correction for an inference-vs-training logprob mismatch
  (there is none while the stub computes logprobs with the training-side
  forward pass; it becomes relevant when a real vLLM server is swapped in).

## Run it (dry run, no GPU)

The dry run swaps vLLM for canned completions (one perfect, one that runs
but computes the wrong thing, one that crashes, one syntax error, so every
GRPO group has reward variance) but keeps everything else real: real
sandbox sessions, real in-sandbox reward, and a real `GRPOTrainer` step on
CPU/MPS with `Qwen/Qwen3-0.6B` saving real adapter versions.

```bash
# from this directory, with a Python env that has the deps:
uv pip install -r requirements.txt

# a stack with a sandbox component (local flavor is fine):
zenml sandbox register local_sandbox --flavor=local   # if none exists
zenml stack register rl-spike-local -o default -a default -sb local_sandbox --set

# two terminals, same --run-name (both resolve it against the active stack):
python run_trainer.py  --run-name async_rl_run --group-size 2 --max-train-steps 3 --max-versions 2
python run_rollouts.py --run-name async_rl_run --group-size 2 --num-parallel 2 --max-waves 12
```

`--group-size` must match on both sides (it is the GRPO group). The trainer
bootstraps v0; the rollout pipeline waits for it, then generates against
whatever version is current. When the trainer reaches `--max-train-steps`,
it writes `STOP`, and the rollout pipeline drains its current wave and
exits.

Reward unit tests (exact scores for every canned completion):

```bash
pytest tests/test_reward.py -v
```

## The knobs that matter

- **`--max-versions`** is the staleness bound. `1` is (near) on-policy:
  only the newest version is ever live, so a generator against an older one
  aborts the moment a new version lands. Larger values keep more generators
  productive across version flips at the cost of training on staler
  rollouts.
- **`--num-parallel`** is how many generators run per wave. It fills the
  sandbox-scoring idle time.
- **`--groups-per-step`** is the target GRPO batch size per optimizer step.

## Transition to remote

Coordination already runs through `fileio` against the stack's artifact
store, so pointing the stack at S3 or GCS moves weights, queue, and markers
off the local disk with no code change. Two things still need work for a
real distributed run: generation moves to a vLLM server (the local adapter
directory becomes a served version), and the atomicity the pointer and
queue rely on has to be reconsidered. `rename` is atomic on local disk but
copy-then-delete on object storage, so `current` and the enqueue/claim
handoff need a real backend (a DB row or a queue) once writers are on
different machines.

## Layout

| Path | What it is |
|---|---|
| `tasks/tasks.jsonl` | 50 "write a ZenML dynamic pipeline that X" tasks + machine-checkable specs |
| `prompts.py` | System prompt with the slim dynamic-pipelines cheatsheet |
| `generation.py` | `VLLMGenerator` (GPU) / `StubGenerator` (dry run) behind one interface |
| `stub_completions/` | Canned completions at four quality tiers for the dry run |
| `sandbox_scripts/score_pipeline.py` | Self-contained in-sandbox runner + reward scorer |
| `async_shared.py` | Version registry, rollout queue, and markers over the artifact store via `fileio` |
| `async_training.py` | One GRPO optimizer step as a plain function |
| `async_scoring.py` | Sandbox scoring for the rollout pipeline |
| `steps/` | `init_lora`, `publish_initial_version`, `train_step`, `generate_and_enqueue` |
| `pipelines/` | `trainer_pipeline`, `rollout_pipeline` |
| `run_trainer.py` / `run_rollouts.py` | The two entrypoints |
| `tests/test_reward.py` | Exact expected reward per canned completion |
