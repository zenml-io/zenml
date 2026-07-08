# RL spike — breakage log

*The actual deliverable. One entry per friction point, logged at the moment it
was hit. Severity: **broken** (no supported path) / **chafes** (works with a
workaround you shouldn't need) / **cosmetic**.*

Format per entry: what we tried → what happened → workaround → severity → what
zenml core would need to change.

---

## 1. vLLM integration is unusable for modern serving

- **Tried:** Use ZenML's existing vLLM integration (`zenml.integrations.vllm`,
  a model-deployer flavor) to serve the policy model during rollouts.
- **What happened:** The integration pins `vllm>=0.6.0,<0.7.0` (late-2024).
  Modern features the RL loop needs — runtime LoRA loading
  (`/v1/load_lora_adapter`), current model support (Qwen3), per-request
  `LoRARequest` — postdate that pin. The component is also built on the local
  daemon-service model-deployer concept, which has no GPU/Kubernetes story.
- **Workaround:** Don't use it. Generation moved inside a pipeline step using
  vLLM's offline batch API (see entry 2).
- **Severity:** broken (for this workload; the integration itself may still
  serve its original CPU demo purpose).
- **Core change:** Either update the vLLM integration to current vLLM with a
  serving story that fits GPU stacks, or deprecate it so it doesn't present
  itself as the obvious path.
- **Hit:** Stage 0 investigation, 2026-07-08.

## 2. No way to keep a model engine warm between steps ("serving gap")

- **Tried:** Find a ZenML-native home for a long-lived vLLM server that
  rollout steps can call, whose weights refresh each iteration.
- **What happened:** Every option is outside ZenML or awkward inside it:
  a raw K8s Deployment is invisible to ZenML (no lineage from adapter
  artifact → serving); a long-running "server step" has no way to publish
  its address or outlive the step contract cleanly; the deployer component
  can host a long-lived FastAPI service (with `on_init` for engine loading)
  but is designed for online inference endpoints, not intra-pipeline batch
  serving, and would hold a GPU continuously.
- **Workaround:** v0 loads the vLLM engine *inside* a per-iteration
  `generate_rollouts` step (offline batch API, per-call `LoRARequest`).
  Costs an engine cold-load per iteration — wall-clock measured and logged
  in Stage 3. Michael's own read when asked: "I'll just do it in-step for
  now, but note that people will want more flexibility."
- **Severity:** chafes (in-step works, pays repeated engine loads; anything
  needing a warm engine across steps has no supported shape).
- **Core change:** A serving-shaped component or step lifetime concept:
  "start this service for the duration of the pipeline (or N steps), give
  dependent steps its address, tear it down at the end" — with artifact
  lineage into what the service is currently serving.
- **Hit:** Stage 0 interview, 2026-07-08.

## 3. Step caching silently replays stale rollouts across runs (confirmed empirically)

- **Tried:** A minimal dynamic pipeline with a `random.random()` step
  mapped over four identical inputs, `enable_cache=True`, run twice.
- **What happened:** *Within* one run ZenML behaves well: all four
  identical-input mapped steps executed and returned four different
  samples (no within-group collapse — better than we anticipated at
  Stage 0). But on the second run **every sampling step was served from
  cache**: same four "random" values, byte-for-byte, and the whole run
  completes green in seconds. Applied to RL: re-running the training
  pipeline (new experiment, same config) would silently replay last
  run's rollouts and gradients instead of resampling — you'd "train"
  twice and get the identical adapter, with no warning that no new
  sampling happened.
- **Workaround:** `enable_cache=False` on the pipeline
  (`pipelines/rl_spike_pipeline.py`).
- **Severity:** chafes (one flag — but caching defaults to ON, and the
  failure is silent and experiment-invalidating).
- **Core change:** A way to mark a step as nondeterministic/sampling
  (never cache-eligible), or at minimum documentation for stochastic
  steps in RL/agentic workloads.
- **Hit:** anticipated Stage 0; confirmed empirically Stage 1, 2026-07-08.

## 6. A dead orchestration process leaves a zombie "running" run forever

- **Tried:** Kill the local dry-run process mid-`grpo_update` (first by
  accident — a process-management mixup on our side — then deliberately).
- **What happened:** The server keeps the run and the in-flight step in
  status `running` indefinitely. Nothing detects that the orchestration
  environment died; there is no heartbeat/TTL, and the zombie runs clutter
  the dashboard as forever-running experiments. (The dynamic-pipelines
  docs' orchestrator table does mark the local orchestrator as not
  handling orchestration-environment failures; Kubernetes is the only
  listed orchestrator that does.)
- **Workaround:** None applied — the zombies from this session are left
  on the staging server as evidence (runs of `rl_spike` in project
  `rl-spike` stuck at `running`).
- **Severity:** chafes locally / matters more for long RL runs on
  orchestrators without failure handling.
- **Core change:** Run-level heartbeat + reaper, so a run whose
  orchestrator vanishes eventually transitions to failed instead of
  running forever.
- **Hit:** Stage 1, 2026-07-08.

## 7. Forced never-raise episode steps make real failures invisible (green run, zero learning)

- **Tried:** Because dynamic pipelines have no `CONTINUE_ON_FAILURE`, one
  crashed episode step would abort the whole training run — so
  `run_episode` catches everything and returns reward 0.0 instead of
  raising (a deliberate, RL-appropriate containment).
- **What happened:** The containment then masked a real bug perfectly: a
  `TypeError` in our sandbox exec call errored **every single episode**,
  all 24 steps completed "successfully", the pipeline ran green
  end-to-end, and training happily performed an optimizer step on
  all-zero rewards. The only tell was our own hand-rolled
  `flat_groups: 3/3` metric in the iteration report.
- **Workaround:** Reward-variance canary in `log_iteration_metrics`
  (`flat_groups`), plus error strings carried on episode outputs.
- **Severity:** chafes (the combination "no partial-failure mode for
  dynamic pipelines" + "no step-level soft-failure state" pushes users
  into catch-everything steps, and then the DAG view can no longer tell
  healthy from broken).
- **Core change:** A first-class "completed with degraded result" step
  state (or CONTINUE_ON_FAILURE for dynamic pipelines) so containment
  doesn't have to lie to the dashboard.
- **Hit:** Stage 1, 2026-07-08.

## 8. Minor API paper cuts hit during the build

- `SandboxProcess.collect()` accepts no timeout — a caller cannot bound a
  sandbox exec; the cap must live inside whatever runs in the sandbox
  (our scorer enforces its own subprocess timeouts). `wait(timeout=...)`
  exists but then output draining is manual.
- Local orchestrator runs the training step's PyTorch effectively
  single-threaded in this setup (~45 min/step CPU vs 8 s on Apple MPS for
  the identical step) — not a ZenML bug per se, but worth knowing that
  step code doesn't automatically get the parallelism an interactive
  process gets.
- **Hit:** Stage 1, 2026-07-08.

## 4. Local sandbox flavor has no file transfer

- **Tried:** Upload the generated `pipeline.py`, the spec, and the scorer
  into a local-flavor sandbox session with `session.upload_file(...)` —
  the documented session API (and what the episode step must do on every
  flavor).
- **What happened:** `NotImplementedError`. `LocalSandboxSession`
  implements only `_exec`/`_close`/`_destroy`; `upload_file`/
  `download_file` fall through to the base class raise. The Kubernetes
  flavor implements both. So the flavor you develop against locally has a
  *smaller* API than the one you deploy on — the opposite of what a local
  dev flavor is for.
- **Workaround:** `steps/run_episode.py::_put_file/_get_file` — try
  `upload_file`, fall back to smuggling the file content through
  `session.exec(["python", "-c", ...])` as base64. Works on every flavor,
  should be needed on none.
- **Severity:** chafes.
- **Core change:** Implement `_upload_file`/`_download_file` on
  `LocalSandboxSession` (trivial: it has a workdir on the same
  filesystem — `shutil.copy` suffices).
- **Hit:** Stage 1 build, 2026-07-08.

## 5. TRL's rollout_func docs don't match its behavior (context, not ZenML)

- Not a ZenML finding, but recorded because anyone rebuilding this will
  hit it: TRL 1.7.1's docstring says rollout_func "receives the raw
  per-process prompt slice with no duplication". Empirically each prompt
  arrives already repeated `num_generations` times, and the function must
  return exactly one completion per received entry (returning
  `num_generations` per entry crashes with an IndexError inside batch
  shuffling). Reinforces the plan's "pin the TRL version" instruction —
  the experimental API's docs lag its behavior.
- **Hit:** Stage 1 build, standalone TRL proof, 2026-07-08.
