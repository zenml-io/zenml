# Agentic RL with ZenML: prime-rl + verifiers + Harbor, with receipts

This example runs the agentic-RL stack the ecosystem converged on —
[prime-rl](https://github.com/PrimeIntellect-ai/prime-rl) (GRPO trainer),
[verifiers](https://github.com/PrimeIntellect-ai/verifiers) (environments),
[Harbor](https://www.harborframework.com) (task format + eval campaigns) —
with ZenML owning what none of them record: **the sandbox the rollouts run
in, the gate in front of the GPU, and the lineage behind it.**

The thesis, executable: *your sandbox provider is a stack component, and
your environment version is an artifact.* The trainer stays ONE opaque step
— prime-rl owns its loop — but every rollout still becomes a row: reward ↔
sandbox session ↔ scorer image ↔ checkpoint. ZenML does **not** orchestrate
the RL loop, draw live training curves (wandb does that), or improve GPU
throughput; it makes runs cheap to be wrong in (a cached gate), honest (a
crashed scorer is an *errored trial*, never a fake `0.0`), and reproducible.

## Setup — honestly, three environments

**Env A — the pipeline venv** (Python ≥ 3.12, forced by harbor):

```bash
cd examples/agentic_rl
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e "../..[local]"    # zenml from the repo checkout
uv pip install -r requirements.txt  # harbor, click, pandas
```

**Env B — the taskset and scorer image** (one-time, a few minutes):

```bash
python scripts/gen_taskset.py          # 64 Harbor task dirs into tasks/
docker build -t zenml-rl-scorer:0.1 docker/
```

Generate the taskset once and leave it: Harbor hashes task paths into
trial identity, so regenerating invalidates shard caching and
before/after joins.

Every task in `tasks/` pins this image, making the scorer environment part
of the task's identity. The verifier inside it is `score_pipeline.py`,
byte-identical to the RL spike's. For remote stacks, push it to a registry
your sandbox flavor can pull from.

**Env C — a prime-rl checkout** (tier 1 only; 15–40 min first run —
torch/vllm/flash-attn):

```bash
git clone https://github.com/PrimeIntellect-ai/prime-rl ~/prime-rl
cd ~/prime-rl && git submodule update --init --recursive && uv sync --all-extras
uv pip install -e <this example>/verifiers_env   # the taskset package
```

**Stack** (the line this example exists to justify):

```bash
zenml sandbox register rl-docker --flavor=docker --image=zenml-rl-scorer:0.1
zenml stack register agentic-rl -o default -a default -sb rl-docker --set
```

Swap `--flavor=docker` for `kubernetes` or `modal` later — same pipelines,
zero code changes.

## Tier 0: the hermetic smoke (no API keys, no GPU)

```bash
python run.py --smoke
```

Oracle (replays each task's committed solution, reward 1.0) vs nop (does
nothing, reward 0.0) on three easy tasks, through real sandbox containers
and the real verifier. Steady-state this is minutes and cents; the first
run adds the image pull, and reruns cache-hit completed shards.

It proves the taskset, the verifier shim, the sandbox stack component, the
eval fan-out, and the gate — which checks **errors before rewards**. An
errored shard logs no `harbor.mean_reward` at all, so a reward-only gate
would read a broken campaign as passing. Break it on purpose (point a task
at a bad image, or drop `zenml` from the scorer image): the run reports
**errored trials**, not reward 0.0 — the distinction this example exists to
make.

## Tier 0.5: real agents

```bash
export OPENAI_API_KEY=...   # or the key your agent needs
python run.py --eval --agent terminus-2 --model gpt-5-nano --trials 3
```

Full 64-task campaign, one mapped shard step per slice, per-shard retries
and caching, `harbor.*` metadata queryable per step.

## Tier 0.75: verifiers-native eval, same receipts

```bash
python -c "
import sys; sys.path.insert(0, '.')
from pipelines import agentic_rl_verifiers_eval
agentic_rl_verifiers_eval(
    prime_rl_dir='~/prime-rl', eval_config='configs/eval.toml',
    output_dir='eval-output')
"
```

`uv run eval` executes as a CommandStep inside the prime-rl checkout (where
verifiers lives — the pipeline venv never needs it, and verifiers' signal
handlers never run inside a ZenML worker thread), and the **same ingest
step** turns its traces.jsonl into the same rollout table: one ingester,
eval and training both. `--no-push` is always passed, so eval runs never
leave for the Prime platform unless you send them yourself.

## Tier 1: train (2 GPUs)

```bash
python run.py --train --prime-rl-dir ~/prime-rl
```

The DAG: `preflight_sandbox → train_prime_rl → ingest_rollout_traces →
find_checkpoint → lineage report`.

- `train_prime_rl` is a **CommandStep** (`uv run --project ~/prime-rl rl @
  configs/rl.toml --output-dir ... --ckpt`): one opaque node, watch
  prime-rl's own logs. prime-rl defaults to **2 GPUs** (one inference, one
  trainer); single-GPU is not a documented prime-rl path.
- Rollout programs execute on **your ZenML sandbox** — the taskset package
  patches verifiers' runtime dispatch (`verifiers_env/.../patch.py` explains
  why a patch, and why it rides the `docker` config type).
- `ingest_rollout_traces` parses prime-rl's per-rollout `traces.jsonl` into
  **one table artifact** — rewards, sandbox ids, timings, tool defs. NOT
  advantages/tokens: `to_record()` drops training tensors upstream, so the
  file tier cannot carry them.
- The report walks one rollout end to end: reward → sandbox session →
  checkpoint. If a hop is missing, the claim isn't real.

`output_dir` must be readable by the ingest step: same machine locally,
shared storage (RWX PV) on Kubernetes.

**After-eval (`--after-eval`, opt-in).** Adds a `serve_checkpoint →
probe_policy_service → stop_policy_service` leg. `serve_checkpoint` stands
the checkpoint up as a run-scoped `KubernetesPodService` running `vllm
serve`, whose persisted handle answers "which checkpoint is this server
serving" (launch command + `checkpoint_dir` input edge). The full leg —
**Harbor agents actually evaluating the served policy** — stays **cut**
(needs an endpoint-calling Harbor agent plus sandbox egress, neither exists
yet), so `probe_policy_service` is honest scaffolding: it hits
`{url}/v1/models` from the step, not from a sandbox.

## Scale beyond one node

Who launches training depends on how many nodes you need — single-node K8s
(this pipeline's CommandStep pod), SLURM (prime-rl's `[slurm]`, ZenML
bookends), or K8s multi-node (this pipeline's CommandStep +
`KubernetesStepOperatorSettings(node_count=N)` for SPMD ranks and
named `KubernetesPodService` services for prime-rl's inference/orchestrator processes). The guide
walks each shape with the full stack prerequisites: *Run prime-rl on your
own Kubernetes, with receipts*
(`docs/book/user-guide/agent-evals-guide/prime-rl-on-kubernetes.md`).

## CI

This example is deliberately **not** wired into the weekly
`agent_framework_integrations` example CI: tier 0 needs a Docker daemon and
a locally built scorer image, which that harness's runners don't guarantee.
Run `pytest tests/ -q` (hermetic, no daemon needed) plus `python run.py
--smoke` on a Docker-equipped machine instead.

## If you are a solo researcher running one experiment

Use `uv run rl @ rl.toml` and wandb directly — this example adds friction
you don't need. It pays off at campaigns, comparisons, teams, and the
moment someone has to answer for a number after the fact.

## Layout

```
agentic_rl/
├── run.py                  # click CLI: --smoke / --eval / --train
├── pipelines/              # eval (tier 0) + train (tier 1) + verifiers eval
├── steps/                  # gate, ingest, checkpoint, serve, report
├── tasks/                  # 64 Harbor task dirs (git-ignored; generated
│                           #   once by scripts/gen_taskset.py — keep them,
│                           #   don't regenerate: task paths are hashed
│                           #   into trial identity / shard caching)
├── docker/                 # scorer image (score_pipeline.py verbatim)
├── verifiers_env/          # the taskset package prime-rl loads
│   └── src/zenml_pipeline_writing/
│       ├── runtime.py      # ZenMLSandboxRuntime (upstream-PR shape)
│       ├── patch.py        # runtime selection until the PR lands
│       └── taskset.py      # tasks + in-sandbox reward + forensics
├── configs/rl.toml         # prime-rl config
└── scripts/gen_taskset.py
```

## Version pins (recorded 2026-07-15 — both ecosystems move weekly)

`harbor>=0.18,<0.19`; `verifiers` as vendored by prime-rl (v1 API, 0.2.x);
prime-rl from `main` (git-only, no releases); zenml from this repo. The
traces.jsonl schema was reshaped within the five days before this example
was written — re-verify against your pins before building on it.
