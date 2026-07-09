# C2 — the pipeline-writing task as a `verifiers` environment

Task C2 from `../framework_breakout.md` (Track C): port the spike's task to
Prime Intellect's `verifiers` package and answer the sandbox-reward collision
question — our reward runs *inside* a ZenML Sandbox session where the
generated code executes; verifiers rubric reward functions run in the eval
process. Does a rubric that opens a ZenML Sandbox session per completion even
compose?

## Verdict: it composes, and it parallelizes

`compare_rewards.py` pushed identical canned completions
(`../stub_completions/`, 5 tasks x up to 4 quality tiers = 18 cases) through
both reward paths:

- **baseline** — `../sandbox_scripts/score_pipeline.py` invoked directly as a
  subprocess, exactly as `../tests/test_reward.py` does (the spike's ground
  truth).
- **rubric** — the same completions scored through verifiers' real scoring
  machinery (`Rubric.score_group`), where each score opens a ZenML Sandbox
  session (local flavor) and runs the same scorer inside it.

Result (2026-07-09, `verifiers==0.1.14`, `results/comparison.json`): **18/18
exact reward matches**. The baseline pass ran the cases sequentially in
62.8s; the rubric pass scored them concurrently (4 sandbox sessions at a
time, `C2_MAX_SANDBOXES`) in 22.9s. ZenML Sandbox sessions opened from
inside verifiers' async event loop work, and they overlap cleanly.

Per the task's stop condition this is a *keep*: the rubric-opens-a-Sandbox
path directly enables C1 (mapped eval campaign) and C3 (`vf.RLTrainer`
inside a step), both of which reuse this environment
(`zenml_pipeline_env.load_environment()`).

## What composition costs (the mechanics)

Two things made it work; both are things any "bring your own sandboxed
reward" user would have to know:

1. **Blocking calls must move off the event loop.** verifiers scores all
   rollouts concurrently on one asyncio loop; ZenML's session API is
   synchronous. The rubric wraps each score in `asyncio.to_thread`, bounded
   by a semaphore (unbounded sandbox fan-out is how the spike's 429
   findings happened — BREAKAGE_LOG 12/15). Without the thread hop, one
   running pipeline would freeze scoring for every other rollout.
2. **verifiers silently converts scorer crashes into reward 0.0.**
   `Rubric._call_individual_reward_func` catches any exception from a
   reward function, logs it, and scores 0.0
   (`verifiers/rubrics/rubric.py`, v0.1.14). That conflates "bad
   completion" with "harness broke" — the exact ambiguity the spike's
   `run_episode` step keeps apart with its `error`/`infra_error` split,
   after BREAKAGE_LOG entry 16 (hours lost to a 0.0 that meant "node had
   no disk"). The rubric here catches its own failures and records them in
   `state["infra_error"]` before returning 0.0, so the two zeros stay
   distinguishable. A user who doesn't do this gets entry-16 archaeology
   back.

## The "safer sandbox lifecycle" question (verifiers v0.1.10+)

The breakout doc asked what sandbox concept verifiers now has natively and
whether ZenML Sandbox could slot behind it. Answered by reading v0.1.14
source:

- verifiers now has **two** sandbox layers, and both are hardwired to Prime
  Intellect's paid sandbox cloud (`prime-sandboxes`):
  - `envs/sandbox_env.py` (`SandboxEnv`): per-rollout sandbox with retry,
    `@vf.cleanup` destruction, and batched teardown. Imports
    `prime_sandboxes.SandboxClient` at module import and raises if it isn't
    installed. Notably their sandbox serves the *agent's tool calls during
    rollout*, not reward scoring — the docstring tells you to cache anything
    reward functions need into state in `post_rollout`, **before** the
    sandbox is destroyed, because rubric functions run after it's gone. Our
    inverted shape (sandbox opened *by the rubric, for scoring*) is not a
    pattern they have.
  - the new `v1` API (Taskset/Harness, where the Harbor integration lives):
    a genuinely nicer object model — `SandboxLease` duck-types its client
    (any object with `execute_command` / `upload_bytes` / `read_file` /
    `delete` coroutines satisfies it) — but the lease factory
    (`v1/utils/sandbox_utils.py::create_sandbox_lease`) constructs
    `prime_sandboxes.AsyncSandboxClient()` unconditionally. No provider
    registry, no factory argument.
- **Could ZenML Sandbox slot behind it?** Mechanically yes: the v1 contract
  is five duck-typed async methods, and ZenML's session API maps onto all
  of them. But there is no injection point today — slotting ZenML in means
  forking one factory function or monkeypatching. That's the
  product-boundary evidence: the distance between "ZenML Sandbox as a
  verifiers backend" and reality is one hardcoded import, upstream.

## Escalation questions for Hamza (collected per the batch rules)

1. verifiers' sandbox provider is one hardcoded `prime_sandboxes` import
   away from being pluggable, and the v1 lease contract is small. Do we
   want an upstream PR (or a published shim) making ZenML Sandbox a
   provider, before that contract ossifies around Prime's cloud?
2. "Bring your own sandboxed reward" in a verifier-first framework costs:
   a thread hop + concurrency cap (mechanical, fine) and losing the
   infra-error/bad-completion distinction unless the user hand-rolls it.
   Should ZenML's sandbox story ship a ready-made verifiers rubric so
   users don't rediscover entry 16?
3. verifiers' own architecture concedes that sandbox state needed for
   rewards must be captured before sandbox destruction (`post_rollout`).
   F1's snapshot work is exactly that capture, done at the platform layer.
   Worth connecting the two threads in the product pitch.

## Layout

- `zenml_pipeline_env.py` — `load_environment()` returning a
  `SingleTurnEnv` (dataset from `../tasks/tasks.jsonl`, spec in `info`)
  with `ZenMLSandboxRubric`, whose one reward function reproduces the
  spike's 0-1 reward by running `score_pipeline.py` in a ZenML Sandbox
  session. Reuses the parent example read-only.
- `compare_rewards.py` — the reward-equivalence experiment described
  above. Self-bootstrapping: isolates into `./.zenml_config` (never
  touches the shared staging server) and registers a local-flavor sandbox
  stack on first run.
- `results/comparison.json` — the 18-case evidence.
- `requirements.txt` — pins (`verifiers==0.1.14` re-checked against PyPI
  at build time, per the survey's pin-at-build-time rule).

## Setup

```bash
cd examples/rl_spike/verifiers_c2
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python -e "../../..[local]"
.venv/bin/python compare_rewards.py
```

No model endpoint and no GPU: the comparison deliberately uses canned
completions (a live model can't produce *identical* completions for the
two paths, so it can't answer the equivalence question). A live-model
`env.evaluate(...)` against any OpenAI-compatible endpoint is what C1
adds on top of this environment.
