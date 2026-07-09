# RL spike: GRPO post-training on ZenML

A toy-but-real RL loop, built entirely as one ZenML dynamic pipeline: a small
Qwen model is post-trained (GRPO + LoRA) to write better **ZenML dynamic
pipelines**. The model quality is not the point — the point is the
**breakage report**: where ZenML works, chafes, or breaks for RL workloads.
Read [`BREAKAGE_LOG.md`](BREAKAGE_LOG.md) for the findings,
[`PLAN.md`](PLAN.md) for the assignment and locked design decisions, and
[`IMPLEMENTATION_NOTES.md`](IMPLEMENTATION_NOTES.md) for what got built and
every deviation from the plan.

## Terms you need (30 seconds)

If you know ZenML but not RL post-training, these five terms cover
everything in this example:

- **Episode / rollout**: one attempt — the model gets a task prompt and
  produces one candidate `pipeline.py`. Single-turn: no follow-ups.
- **Group**: `group_size` independent attempts at the *same* task, sampled
  with temperature so they differ. GRPO's learning signal is *within-group
  comparison* — which attempts beat their siblings.
- **GRPO** (Group Relative Policy Optimization): the training algorithm.
  Each episode's **advantage** = its reward minus the group's mean (scaled
  by the group's spread). Above-average completions get pushed up,
  below-average pushed down. Consequence worth remembering: if all
  attempts in a group score the same, the group teaches nothing.
- **LoRA adapter**: a small set of add-on weight matrices (MBs, not GBs)
  trained instead of the full model. It's the only thing that changes
  between iterations, which is why it works as a regular ZenML artifact.
- **logprobs**: for each generated token, the log-probability the model
  assigned to it when sampling. TRL needs them to weight its loss; they
  ride along in every episode record.

## The loop

```
load_tasks ──► init_lora (adapter v0)
                  │
   ┌──────────────▼──────────────── per iteration ────────────┐
   │ generate_rollouts   ONE step, vLLM offline batch (GPU)    │
   │        │            or the dry-run stub (CPU)             │
   │        ▼                                                  │
   │ run_episode.map     one sandbox session per completion:   │
   │        │            run the generated pipeline.py against │
   │        │            a throwaway local ZenML store, score  │
   │        │            it 0-1 (reward computed IN-sandbox)   │
   │        ▼                                                  │
   │ grpo_update         ONE TRL GRPOTrainer optimizer step;   │
   │        │            emits adapter v(N+1)                  │
   │        ▼                                                  │
   │ log_iteration_metrics                                     │
   └───────┴── adapter v(N+1) feeds the next iteration ────────┘
```

Key properties:

- **Single-turn episodes** — one completion per episode, by design (avoids
  TRL's multi-turn importance-sampling problem, see PLAN.md §2).
- **TRL is a library, not an orchestrator** — its experimental
  `rollout_func` hook (pinned `trl==1.7.1`) returns the *pre-generated,
  pre-scored* episodes, so TRL only does advantages/loss/gradient.
- **Two serving modes** — `offline` keeps the original proof path:
  generation uses vLLM's offline batch API inside the step, with the LoRA
  adapter passed per call (`LoRARequest`). `warm_vllm` is the next
  architecture: one raw Kubernetes vLLM Deployment stays warm on GPU 1,
  `grpo_update` trains on GPU 2, a ZenML step hot-loads each new LoRA
  adapter artifact into the server before the next rollout, and a cleanup
  step deletes the raw Kubernetes Deployment/Service on normal completion.
- **Reward is computed inside the sandbox** where the generated pipeline
  actually runs: +0.3 parses/imports, +0.4 defines a pipeline and runs
  green, +0.3 declarative spec checks (step count, required API, expected
  output value). See `sandbox_scripts/score_pipeline.py`.

## Layout

| Path | What it is |
|---|---|
| `tasks/tasks.jsonl` | 50 "write a ZenML dynamic pipeline that X" tasks + machine-checkable specs |
| `prompts.py` | System prompt with the slim dynamic-pipelines cheatsheet |
| `generation.py` | `VLLMGenerator` (GPU offline) / `StubGenerator` (dry run) behind one interface |
| `serving/` | Raw Kubernetes vLLM Deployment helpers + HTTP rollout client for `--serving-mode warm_vllm` |
| `stub_completions/` | Canned completions at four quality tiers for the dry run |
| `sandbox_scripts/score_pipeline.py` | Self-contained in-sandbox runner + reward scorer |
| `steps/` | Pipeline steps for task loading, rollout generation, sandbox scoring, GRPO training, metrics, and warm-vLLM lifecycle control |
| `pipelines/rl_spike_pipeline.py` | The dynamic pipeline (the diagram above) |
| `run.py` | Entrypoint |
| `restore_sandbox.py` | Reopen a failed episode's sandbox from its snapshot (see `SNAPSHOTS.md`) |
| `tests/test_reward.py` | Exact expected reward per canned completion |
| `tests/test_snapshot.py` | Snapshot-on-failure helper behavior across flavors |
| `SNAPSHOTS.md` | Snapshot support matrix, restore demo, and gap list (task F1) |

## Run the dry run (no GPU, ~2-3 min on an Apple Silicon laptop)

The dry run replaces vLLM with canned completions (one perfect, one that
runs but computes the wrong thing, one that crashes at runtime, one with a
syntax error — so every GRPO group has reward variance) but keeps
**everything else real**: real sandbox sessions, real in-sandbox reward
computation, and a real `GRPOTrainer` optimizer step on CPU with
`Qwen/Qwen3-0.6B` that saves a real LoRA adapter which the next iteration
actually loads.

```bash
# from examples/rl_spike, with the zenml repo venv active
uv pip install -r requirements.txt

# a stack with a sandbox component (local flavor is fine):
zenml sandbox register local_sandbox --flavor=local   # if none exists
zenml stack register rl-spike-local -o default -a default -sb local_sandbox --set

python run.py --dry-run
```

Note on the artifact store: the team's `rl-spike-local` stack on the
staging server uses the shared **`s3` artifact store** instead of the
local default, so dry-run artifacts and logs are visible to everyone in
the dashboard (project `rl-spike`) — useful for a distributed team
reviewing runs by link. Verified working 2026-07-08 (~45s slower per
dry run from upload time). A purely local `-a default` stack works too
if you don't need shared visibility.

Expected: a `rl_spike` run with 2 iterations × (1 generation step + 12
mapped episode steps + 1 training step + 1 metrics step), mean reward
exactly **0.4458** per iteration (deterministic tiers: 1.0 / 0.75 or 0.5 /
0.2 / 0.0 under the Stage-3+ reward weights 0.2 parse + 0.3 runs-green +
0.5 spec clauses), `flat_groups: 0`, and an `iteration_report` markdown
artifact per iteration. The training step uses Apple MPS if available (~8s per
optimizer step); on pure CPU it takes ~45 minutes per step — it works, but
you want the MPS path.

Reward unit tests (asserts exact scores for every canned completion):

```bash
pytest tests/test_reward.py -v
```

Failure forensics: add `--snapshot-on-failure` to snapshot each failing
episode's sandbox filesystem before teardown and restore it later with
`restore_sandbox.py` — Modal sandbox flavor only; on kubernetes/local
the episode records an honest `snapshot_error` instead. Details, support
matrix, and a worked demo in `SNAPSHOTS.md`.

## Run for real (GPU)

Stage 3 of the spike — requires CUDA GPUs, `vllm` installed, and a stack
whose sandbox can run untrusted-ish generated code. The original offline
path needs one 24GB GPU and reloads vLLM in every generation step. The
The new warm-server path needs two GPUs: one held by vLLM, one for TRL
training. It currently assumes only one warm-vLLM run per Kubernetes
namespace because the raw Deployment and Service names are fixed for the
spike. Not verified yet; see `GPU_SETUP.md` before attempting.

```bash
# Original one-GPU proof path: vLLM loads inside generate_rollouts each iteration.
python run.py --iterations 5 --group-size 8 --num-tasks 50 \
  --serving-mode offline

# Agreed next path: warm vLLM server + ZenML adapter artifact hot-loads.
python run.py --iterations 5 --group-size 8 --num-tasks 50 \
  --serving-mode warm_vllm
```

## Cost/timing capture

ZenML tracks none of this natively (that's a finding), so every step logs
wall-clock and token counts into its metadata (`engine_load_seconds`,
`generation_seconds`, per-episode sandbox timings, `train_seconds`), and
each iteration's totals land in the `iteration_report` artifact.
