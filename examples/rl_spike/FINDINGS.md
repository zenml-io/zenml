# RL spike — findings for core (2026-07-09)

*Audience: Michael, Hamza. This synthesizes [`BREAKAGE_LOG.md`](BREAKAGE_LOG.md)
(16 entries), [`CALIBRATION.md`](CALIBRATION.md), and
[`TRAINING_RUN.md`](TRAINING_RUN.md) into themes and asks. The log stays
the source of truth for reproduction detail; entry numbers below refer to it.
Michael has been following the log as it grew, so this document orders and
weighs rather than re-tells.*

## What the spike was

GRPO post-training of Qwen3-4B (LoRA) to write better ZenML dynamic
pipelines, built as one ZenML dynamic pipeline: a generation step (vLLM,
offline or warm-served), a `.map()` fan-out of episode steps that execute
and score each completion in a ZenML Sandbox, and a TRL `GRPOTrainer` step
demoted to pure math via `rollout_func`. Everything ran on the staging EKS
cluster with real GPUs, real fan-out (280 episode pods per iteration), and
real multi-hour wall clocks. That scale is why the second half of the log
exists: entries 10–16 only appear when you actually run the thing, at size,
for hours.

**The loop works.** Full iterations run end-to-end in ~47 minutes (fan-out
~40 min, optimizer step ~8.5 min, adapter hot-reload into the warm vLLM
server ~1 min), with adapter-artifact lineage threading the iterations.
Warm serving cut per-iteration cost by ~5–8 min of engine loading versus
offline mode (209.6s vs 555–727s per iteration at smoke scale — the
serving-gap evidence, entry 2). The training outcome itself was
inconclusive (three clean optimizer steps, statistically flat rewards —
see [`TRAINING_RUN.md`](TRAINING_RUN.md)), but the training outcome was
never the deliverable.

## Theme 1 — Dynamic fan-out has no working concurrency or placement story (entries 11, 12, 14, 15)

This is the strongest theme, and the four entries are one escalating
failure family, so they are worth reading as a unit:

1. **Placement** (11): mapped episode pods run the full ~30GB pipeline
   image even when the step is CPU-only glue. The scheduler packed ten of
   them onto a shared CPU node, tipped it into DiskPressure, and **evicted
   three other tenants' ZenML server pods**. Per-step images might fix
   this, but it's unclear whether per-step `DockerSettings` can work for
   dynamic pipelines at all, since images build client-side before the DAG
   shape exists.
2. **Concurrency** (12): `max_parallelism` — the documented knob — is
   silently ignored by dynamic pipelines. The real cap is an undocumented
   env var (`ZENML_DYNAMIC_PIPELINE_WORKER_COUNT`), and *isolated* mapped
   steps aren't governed by anything at all. Ten concurrent pod startups
   were enough for the platform's own credential endpoint to 429 its own
   fan-out to death, before user code ran.
3. **Blast radius** (14): the orchestrator pod ships with no memory
   request (BestEffort QoS), so the kernel OOM-killed it *to make room for
   the episode pods it had launched*, leaving a headless run stuck
   `running` forever.
4. **Retry integrity** (15): the `StepRetryConfig` added to survive the
   429 bursts is itself killed by 429 bursts — the relaunch path talks to
   the same rate-limited server, and when that call dies, the step is left
   in `retrying` forever with no pod, no thread, and no timeout. The final
   training run deadlocked on exactly two such zombie steps out of 280.

**Asks, in priority order:** (a) make `max_parallelism` govern dynamic
pipelines or fail loudly when set on one; (b) make the retry/relaunch path
at least as robust as the step it protects, and give `retrying` a terminal
escape (relaunch-with-backoff, then `failed`); (c) default the orchestrator
pod to a sane memory request; (d) answer the per-step-image question for
dynamic pipelines; (e) treat 429 from the platform's own server as a
first-class retryable condition (Retry-After, jitter, or an
orchestrator-seeded credential cache so N pods don't each re-fetch
identical connector credentials).

## Theme 2 — Failure states lie (entries 6, 7, 8b, 14, 15, 16)

Every long-running-workload failure we hit ended in a state that
misreported itself:

- Dead local orchestration → run `running` forever (6); pod-start failure
  on K8s → run `provisioning` forever (8b); OOM-killed orchestrator → run
  `running`, steps orphaned (14); dead retry → step `retrying` forever,
  run alive but unfinishable (15).
- Because dynamic pipelines have no `CONTINUE_ON_FAILURE`, episode steps
  must catch everything and return reward 0.0 — so a bug that zeroed
  every episode produced a **green** run that trained on garbage (7), and
  an all-NaN adapter once shipped as the final artifact of a green run
  (7 postscript).
- The scoring variant (16): a DiskPressure-degraded node made `import
  zenml` fail inside sandbox pods for ~2.5 hours, and the reward channel
  recorded that as honest "model scored 0.0" across two full iterations.
  GRPO's group-relative advantage made the poisoned update a provable
  no-op (`grad_norm: 0.0` exactly), which is luck of the algorithm, not a
  property of the platform.

**Asks:** a run-level heartbeat/reaper so orphaned runs eventually fail
(6/8b/14); a terminal path out of `retrying` (15); and a first-class
"completed with degraded result" step state so containment steps don't
have to choose between aborting the run and lying to the dashboard (7).
Entry 16's lesson is mostly on us (classify environment failures as
`infra_error`, keep scorer stderr), but the platform half — sandbox
sessions scheduled onto a node the kubelet already had under DiskPressure,
with nothing surfacing that on the step — is worth a thought about node
conditions in step/pod metadata.

## Theme 3 — The serving gap is real and now measured (entries 1, 2, 13)

There is no ZenML-native home for "keep an engine warm across steps and
tell it about new adapter artifacts": the vLLM integration pins a 2024
vLLM and can't do runtime LoRA (1); the warm server had to be a raw K8s
Deployment invisible to lineage (2); and getting adapter bytes *into* that
pod revealed that `zenml.io.fileio` silently only works inside step
bootstrap, because remote schemes register on artifact-store instantiation
with connector credentials (13). The working transport ended up: adapter
as materialized `Path` step input (canonical, credentialed), streamed into
the pod over the exec websocket — the serving pod needs no S3 and no
zenml install.

**Asks:** a serving-shaped lifetime concept ("start this service for the
pipeline's duration, give steps its address, tear it down — and record
what artifact it currently serves"); update or deprecate the vLLM
integration; make `fileio`'s unregistered-scheme error say "you are not
in a ZenML context" and offer the supported out-of-step path.

One sharpener from the final run: because teardown is a *step*, a failed
run leaks the GPU-holding vLLM Deployment (it survived both the OOM crash
and the deadlock stop and had to be deleted by hand). A pipeline-level
cleanup guarantee — `on_failure` hooks that provably run, or resources
owned by the run rather than by a step — is part of the same serving
story.

## Theme 4 — Sharp edges that cost real time but have small fixes (entries 3, 4, 8, 9, 10)

- Step caching silently replays stale rollouts across runs — statistically
  invalid for any sampling workload, default ON (3). Ask: a
  "nondeterministic step" marker.
- The local sandbox flavor implements *less* API than the K8s flavor
  (`upload_file` raises `NotImplementedError`) — the dev flavor should be
  a superset, and the fix is a `shutil.copy` (4).
- Settings keys fail open: a bare `"orchestrator"` key validates and is
  silently never applied; only `"type.flavor"` works (8).
- `log_metadata` kills a *succeeded* step when telemetry contains
  `inf`/`NaN`, with an error naming neither key nor fix (9) — and ML
  emits non-finite floats routinely.
- The step log handler is not fork-safe with the S3 store: every log line
  from a forked child (vLLM engine, DataLoader workers) raises a
  traceback that buries the user's real error (10).
- Custom parent images: five submissions to first green, each failure
  discovered at pod runtime after a multi-GB build/push/pull cycle (8b).
  A build-time `import zenml` check inside the image would have caught
  three of the five instantly.

## The verdict question, widened

The honest summary for "would we recommend ZenML for this workload today":
the **shape** is right — visible phases, artifact lineage through the
loop, sandboxes as first-class execution, `runs stop` and step retries
that mostly work — but the **defaults assume short, small, deterministic
pipelines**. Everything in themes 1–2 is what happens when a workload is
long, wide, and stochastic. None of it looks architectural; all of it is
defaults, caps, heartbeats, and honest failure states.

Per [`framework_breakout.md`](framework_breakout.md), the closing question
is now wider than RL:
the same loop (generate → sandbox-verify → update an artifact → iterate)
underlies prompt evolution, eval campaigns, and trajectory export, and the
follow-up spikes are chosen to test whether ZenML is the harness for that
whole spectrum rather than for GRPO specifically. The findings above are
the platform work that any of those consumers would hit first.
