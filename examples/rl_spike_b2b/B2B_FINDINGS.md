# B2b — TRL drives Harbor, ZenML Sandbox underneath (2026-07-09)

Spike findings for Track B / B2b (`framework_breakout.md`). Branch
`spike/b2b-trl-harbor` off `spike/b1-harbor-k8s` (merges nowhere; docs are
the deliverable). Code in `examples/rl_spike_b2b/`. Everything ran against
the staging Pro server (project `rl-spike`), sandbox pods on the staging
EKS cluster, trainer on the `rl-spike-gpu` node group (scaled to 0 after).

## The one-paragraph verdict

**Yes: ZenML Sandbox can be the execution layer under TRL-native RL, today,
without ZenML owning the loop — and the entire gap is one constructor
kwarg in TRL.** Harbor's trial config carries an `import_path` field that
its `EnvironmentFactory` *prefers* over the built-in backend enum, and
`import_class("zenml.integrations.harbor.environment:ZenMLSandboxEnvironment")`
resolves our bridge unmodified. TRL's `HarborEnv._start` simply never
exposes that field: it hardcodes `TrialEnvironmentConfig(type=...)`, and
the `EnvironmentType` enum lists 20+ vendor backends (Docker, E2B,
Daytona, Modal, LangSmith, W&B, ...) with no extension point. A ~25-line
`_start` override (a copy with `import_path=` instead of `type=`) was
sufficient to run the full stack live: **GRPOTrainer → our harness →
Harbor factory → ZenML bridge → Kubernetes sandbox pods**, both in a
manual phase-1 smoke and under a real bounded `trainer.train()` on the
GPU node. Escalation for Hamza: a one-parameter upstream PR to TRL
(`environment_type` accepting an import path, or a new
`environment_import_path=`) makes ZenML Sandbox a first-class TRL-RL
substrate — same shape as C2's "one hardcoded import is the whole gap"
finding, and it lands in *TRL*, the highest-traffic RL library there is.

## What was built

```
GRPOTrainer (TRL 1.7.1, vLLM colocate — holds policy tokens/logprobs)
  -> ZenMLPipelineEnv (zenml_harness.py: HarborEnv subclass, 2 tools:
     write_pipeline / run_pipeline; PROMPT_SUFFIX carries the 3-attempt rule)
    -> harbor 0.17.1 EnvironmentFactory (TrialEnvironmentConfig.import_path)
      -> ZenMLSandboxEnvironment (vendored bridge, zenml_sandbox_env.py)
        -> Client().active_stack.sandbox.create_session() -> K8s pods
```

- The spike's pipeline-writing task recast as 3 multi-turn Harbor tasks
  (`tasks/`): *write `/app/pipeline.py`; you may execute it, read the
  traceback, and fix it; 3 turns max*. The verifier is the spike's
  `score_pipeline.py` **verbatim** — `tests/test.sh` adapts its reward
  JSON to Harbor's `/logs/verifier/reward.json` contract in ~10 lines.
- Phase-1 smoke (`smoke_env.py`, laptop, no GPU): reset → write → run →
  reward through TRL's own HarborEnv machinery. Perfect pipeline scores
  **1.0 in 27–31s** wall clock (session pod start ~6s, in-sandbox
  pipeline run ~5–10s, verifier ~13s). The `--fix-loop` variant plays
  broken code → real NameError traceback from the pod → fixed code →
  reward 1.0, all inside ONE persistent session — the filesystem history
  F1's snapshot demo wants.
- Phase 2 (`train_b2b.py`): ONE ZenML step on the `kubernetes_aws` stack
  (K8s orchestrator, **S3 artifact store**, ECR, K8s sandbox) running a
  bounded `GRPOTrainer` session — Qwen3-0.6B + fresh LoRA, vLLM colocate,
  2 optimizer steps, group size 4. Adapter directory and metrics dict come
  out as step artifacts.

## Question (b): can ZenML Sandbox sit under a framework-owned loop?

Evidence says yes, at two levels:

1. **Contract level.** Harbor 0.17.1's environment ABC is satisfied by the
   bridge written against Harbor 0.8 with *zero* changes to the abstract
   surface (9/9 methods; the private hooks it uses — `_merge_env`,
   `EnvironmentPaths` — also survived). The factory's `import_path`
   resolution is a stable, documented-in-code mechanism (`harbor run
   --environment-import-path` exists on the CLI). ZenML doesn't need to be
   in Harbor's vendor enum to be a Harbor substrate.
2. **Runtime level.** Under `trainer.train()`, TRL created fresh envs per
   rollout, `reset()` opened `zenml-sandbox-k8s-*` pods (observed live,
   ECR image via the B1 `docker_image` translation, scheduled on shared
   CPU nodes while the trainer held the GPU node), the verifier exec'd in
   them, and teardown deleted them. The K8s events log shows the full
   create/kill cycle per rollout batch.

The residual wall is exactly where TRL's docs put it: only *external*
agents train (the trainer generates every turn, so it holds tokens and
logprobs); *installed* agents (Claude Code & co. running inside the
container with their own inference) are unsupported for RL by
construction. Our bridge lives on the right side of that wall: it is a
sandbox provider, not an agent.

## Question (a): what does ZenML still see?

When TRL+Harbor swallow generation, environment, reward, and training
into one `trainer.train()` call inside one step, ZenML's view collapses
to:

- **In:** step parameters (model id, optimizer steps, group size, turn
  cap, token budget) — versioned run config on the dashboard.
- **Out:** the trained LoRA adapter directory as an S3-backed artifact,
  plus a metrics dict artifact carrying `trainer.state.log_history`
  (per-step reward mean/std, tool-call frequency, completion lengths,
  entropy, grad norm...).
- **Nothing in between.** Per-rollout episodes, per-turn tool calls,
  verifier breakdowns, the sandbox sessions themselves — all invisible.
  The sandbox pods don't even correlate to the run in ZenML's data model
  (they're sessions on a stack component, not step-scoped resources).
  Contrast with the v0 spike, where every episode was an artifact with
  the full reward breakdown; here the same information exists only as
  numbers inside one metrics blob (or TRL's own logs).

So the lineage residue is real but thin: *config → adapter + aggregate
metrics*, per run. That is exactly the "black-box framework step" shape
PLAN.md predicted for full-span frameworks (C3/D1's question), now
confirmed empirically on the TRL path. What would thicken it without
fighting the framework: a TRL callback (or a reward-func wrapper) that
logs per-rollout records as ZenML metadata/artifacts — both hooks are
public TRL surface and need nothing from Harbor. Not built (out of
bounded-run scope), but there is no structural blocker.

## The bounded runs (what actually happened on the GPU)

Five runs on one L4 node (`g6.2xlarge`, $1.22/hr, node group scaled back
to 0 afterwards). Each failure taught something distinct:

- **Run 1 (`63050b79`, TRL defaults):** mechanically green — image built
  on `vllm/vllm-openai:v0.24.0` (Python 3.12 floor satisfied), 2 GRPO
  steps in 34s, adapter + metrics artifacts in S3 — and scientifically
  empty: `completions/clipped_ratio = 1.0`, `tools/call_frequency = 0.0`,
  all rewards 0.0. TRL's default `max_completion_length=256` is below
  Qwen3's *thinking prefix*, so the policy was clipped before it could
  emit a single tool call; the envs still went through their full sandbox
  lifecycle (reset opened pods, verifiers scored never-written files as
  0.0). **For agentic GRPO the token budget is a correctness knob, not a
  tuning knob** — at 256 tokens the policy physically cannot act.
- **Run 2 (`068c4343`, 2048-token turns):** optimizer step 1 completed
  with REAL agentic behavior — `tools/call_frequency = 0.75`, zero
  clipping, reward mean 0.05 / std 0.1 (a live GRPO gradient), loss
  0.1458 — then step 2's backward OOMed (completions up to 1546 tokens ×
  batch 4 × a 151k vocab on the 24GB shared with vLLM).
- **Run 3 (`9f7bca1a`):** capping vLLM at 25% GPU memory starved its KV
  cache for Qwen3's default 40960 max seq len — the colocate squeeze cuts
  both ways.
- **Run 4 (`55ba00c8`, +`vllm_max_model_length=8192`, sleep mode,
  gradient checkpointing): step 1 green again (loss 0.3751,
  tool calls happening), step 2 OOM at a 4.64GiB allocation. The L4 is
  simply marginal for group size 4 at 2048-token multi-turn sequences.
- **Run 5 (`ca33e089`, group size 2, 1024-token turns): GREEN.** Both
  optimizer steps completed (train_runtime 58s, step 2 loss 0.8729,
  grad_norm 1.097), `tools/call_frequency` 2.0 then 0.5 — the policy
  wrote and executed pipelines in ZenML sandbox pods mid-rollout — and
  the run finished `completed` with `b2b_trained_adapter` and
  `b2b_train_metrics` artifacts on S3, visible in the dashboard.

Hardware verdict: one 24GB L4 in colocate mode runs TRL-drives-Harbor at
(group 2, 1024 tokens); (group 4, 2048) needs either a bigger card
(`g6e.xlarge`, 48GB L40S — one flag in GPU_SETUP.md) or the server-mode
two-node split.

### Failure-mode finding: a crashed trainer step wedges and leaks sessions

Both OOM runs left the step pod alive indefinitely after printing the
traceback — Python cannot exit because each `HarborEnv` owns a daemon
event-loop thread and NCCL state persists — and the per-rollout ZenML
sandbox pods (4 each run) stayed Running until deleted by hand. On a
green run teardown is clean (verified: zero stray pods). This is the
BREAKAGE_LOG-15 zombie shape reappearing one layer down: **sandbox
sessions opened by framework code inside a step have no supervisor** — no
step-failure hook closes them, and nothing in the ZenML data model even
records that they belonged to that step run. Escalation: session TTLs
exist per flavor, but a crash-consistent "sessions die with their step"
contract does not.

## Bonus: the multi-turn snapshot demo (F1 carry-over)

`snapshot_demo.py`, on the Modal flavor (`rl-spike-modal` stack,
`modal_zenml_io` component — zenml-io workspace, env `dev`; snapshots are
Modal-only per SNAPSHOTS.md): plays the fix loop through the SAME TRL
harness the trainer drives — broken pipeline → real in-sandbox NameError
traceback → `create_snapshot()` AT FAILURE TIME → fixed pipeline runs
green → live session destroyed → **snapshot restored into a fresh
session, which still contains the broken `pipeline.py`** even though the
live filesystem had moved on. 47s end-to-end, ref
`im-01KX3SAEBZZ8A7X7H88E754BSV`, `DEMO PASSED`. This is the
"filesystem with history (attempt → traceback → edit)" version of the
demo the single-turn baseline couldn't provide. One API note: the demo
reaches through two private layers (`env._env._session`) to snapshot — a
shipped version wants `snapshot()` surfaced on the Harbor bridge.

## Version-fragmentation ledger (the fight that mostly didn't happen)

| Expectation (task brief) | Reality |
|---|---|
| "current TRL v1, NOT the spike's trl==1.7.1" | **trl 1.7.1 IS current** (latest release; ships the `harbor` extra). The spike's pin was never stale. |
| "current Harbor (0.18.x)" | `trl[harbor]` resolves **harbor 0.17.1**; fine in practice. |
| Bridge (0.8) vs Harbor 0.17 | Abstract contract: unchanged. TWO real drifts: (1) `allow_internet` deprecated → `network_mode`; parsed value is `None`, so the 0.8-era `if not cfg.allow_internet` **refused every task** (spike-patched in the bridge, both copies). (2) `BaseEnvironment.__init__` grew ~10 kwargs (mounts, network policies, resource enforcement) that pass through `**kwargs` silently — features the bridge ignores without telling anyone. |
| One venv | Impossible on macOS arm64: `vllm>=0.22` has a Linux-only transitive dep (`tokenspeed-mla`). Laptop venv = everything but vllm (enough for phase 1); vllm exists only in the Linux pipeline image. |
| zenml side | Released 0.96.1 already has everything the bridge imports (`Client`, `zenml.sandboxes`, `KubernetesSandboxSettings.image`) — which is why **vendoring the bridge into the example (~300 lines, zero private APIs) just works**, and the unmerged-integration problem (PR #5029 not in the PyPI image) dissolves. |
| kubernetes client | New wheel (v35) breaks zenml 0.96.1's service connector (`ApiClient.call_api()` signature); the integration's own pin `>=21.7,<26` must be respected in hand-built venvs. |

## Divergences from the brief, decided at build time

- **1 GPU node, not 2.** Each `g6.2xlarge` has a single L4; a single
  trainer pod can never mount two nodes' GPUs, and vLLM colocate shares
  the one GPU with training by design. The brief's "needs both GPUs"
  applies to a server-mode vLLM split (two pods), which the bounded run
  deliberately avoids. Cost: $1.22/hr instead of $2.44/hr.
- **Qwen3-0.6B, not 4B**: the bounded run proves the mechanism; 24GB
  shared between vLLM KV cache, HF weights, and optimizer state is tight.
- **No adapter-artifact input in v1**: fresh LoRA in, trained adapter
  out. Threading a previous adapter in is mechanical once this shape
  holds.

## Escalations / follow-ups

1. **To Hamza (product, time-sensitive like B1(d)):** propose the
   one-parameter TRL upstream change (accept an import path in
   `HarborSpec(environment_type=...)` / `HarborEnv`), positioning ZenML
   Sandbox in TRL's RL story the way `--env langsmith` sits in Harbor's
   eval story. Until then, the documented recipe is our harness subclass.
2. **To core:** the two bridge drifts (network_mode handling; the
   silently-ignored new Harbor env kwargs) belong in the Harbor
   version-bump work already tracked for the integration.
3. **Sandbox↔run correlation gap** (question (a)): sandbox sessions
   opened from inside a step have no ZenML-visible link to the run. Even
   a session label/tag ("opened by step run X") would let the dashboard
   answer "which pods did this training run create?".
