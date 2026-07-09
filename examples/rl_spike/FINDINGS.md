# RL spike — findings for core (2026-07-09)

*Audience: Michael, Hamza. This synthesizes [`BREAKAGE_LOG.md`](BREAKAGE_LOG.md)
(18 entries), [`CALIBRATION.md`](CALIBRATION.md),
[`TRAINING_RUN.md`](TRAINING_RUN.md), [`SNAPSHOTS.md`](SNAPSHOTS.md)
(task F1), [`DATA_LAYER.md`](DATA_LAYER.md) (task E3), and
[`verifiers_c2/README.md`](verifiers_c2/README.md) (task C2) into themes
and asks. The log stays the source of truth for reproduction detail; entry
numbers below refer to it. Michael has been following the log as it grew,
so this document orders and weighs rather than re-tells.*

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

Since the training run, three follow-up tasks widened the evidence
without any new GPU time. We taught failing episodes to save their
sandbox filesystem so a human can reopen it later and see what actually
happened (F1, [`SNAPSHOTS.md`](SNAPSHOTS.md)); we measured what the loop
really pushes through the artifact store instead of guessing (E3,
[`DATA_LAYER.md`](DATA_LAYER.md)); and we rebuilt the same task and
reward inside `verifiers`, an external RL library, to see whether ZenML
sandboxes survive contact with someone else's framework (C2,
[`verifiers_c2/`](verifiers_c2/README.md)). Their results live in
themes 2, 3, and 5 below.

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

This theme now has a price tag ([`DATA_LAYER.md`](DATA_LAYER.md)).
Across 1,398 episode steps, the useful work — create a sandbox, upload
three small files, run the scorer — averages 31.6 seconds. The step
around it averages 117 seconds. **73% of every episode's wall-clock goes
to getting a step running at all**: scheduling a pod, pulling the image,
downloading the code archive, fetching credentials, writing the output
artifact. Since the fan-out is ~90% of iteration time, most of what a
training iteration pays for is this fixed cost, not scoring. Each
iteration also registers 280 separate ~10 KB artifacts with the ZenML
server (one ingredient of the 429 storms above), and the trainer then
re-reads them at a measured 293 ms apiece — about 82 seconds hiding
inside what looks like "training time" on every optimizer step.

**Asks, in priority order:** (a) make `max_parallelism` govern dynamic
pipelines or fail loudly when set on one; (b) make the retry/relaunch path
at least as robust as the step it protects, and give `retrying` a terminal
escape (relaunch-with-backoff, then `failed`); (c) default the orchestrator
pod to a sane memory request; (d) answer the per-step-image question for
dynamic pipelines; (e) treat a 429 from the platform's own server as something
the client is built to retry (honor Retry-After, add jitter, or have the
orchestrator seed a credential cache so N pods don't each re-fetch
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
  zenml` fail inside sandbox pods for ~2.5 hours, and the scorer wrote
  that down as an honest "model scored 0.0" across two full iterations.
  GRPO's group-relative advantage made the poisoned update a provable
  no-op (`grad_norm: 0.0` exactly), which is luck of the algorithm, not a
  property of the platform.

**The forensics answer exists — on one flavor (F1, entries 17–18).**
Entry 16 cost hours because the failed sandboxes were gone by the time
anyone asked what happened inside them. Task F1 built the fix into the
example: failing episodes now snapshot their sandbox filesystem before
teardown, and `restore_sandbox.py` reopens one from the episode's
artifact id. The demo compressed the entry-16 diagnosis to a single
command — restore, `cat pipeline.py` (valid program), `import zenml`
(ModuleNotFoundError) — environment's fault, proven in seconds. The
catch: the core snapshot API is implemented **only by the Modal flavor**.
Kubernetes and local — the flavors long-running fan-outs actually run
on, where entry 16 happened — raise `NotImplementedError` (documented,
no roadmap; the open GKE PR targets a different flavor). Snapshot cost
on Modal measured at ~1.3 s per failing episode, so failure-only
snapshotting is cheap. Full matrix and gap list in
[`SNAPSHOTS.md`](SNAPSHOTS.md).

**Asks:** a run-level heartbeat/reaper so orphaned runs eventually fail
(6/8b/14); a terminal path out of `retrying` (15); a real "completed
with degraded result" step state so containment steps don't have to
choose between aborting the run and lying to the dashboard (7); snapshot
support for the Kubernetes sandbox flavor — even "tar the workdir to the
artifact store" answers the entry-16 question — plus snapshot refs
recorded by the platform as step metadata, not smuggled through step
outputs by user code the way our example has to (17). Entry 16's remaining lesson is
mostly on us (classify environment failures as `infra_error`, keep
scorer stderr), but the platform half — sandbox sessions scheduled onto
a node the kubelet already had under DiskPressure, with nothing
surfacing that on the step — is worth a thought about node conditions
in step/pod metadata.

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

**Asks:** a way to declare "start this service when the run starts, hand
its address to steps, tear it down when the run ends — and record which
artifact it is currently serving"; update or deprecate the vLLM
integration; make `fileio`'s unregistered-scheme error say "you are not
in a ZenML context" and point at the supported out-of-step path.

One more lesson from the final run: because teardown is a *step*, a failed
run leaks the GPU-holding vLLM Deployment (it survived both the OOM crash
and the deadlock stop and had to be deleted by hand). A pipeline-level
cleanup guarantee — `on_failure` hooks that provably run, or resources
owned by the run rather than by a step — is part of the same serving
story.

We also measured what actually moves through the artifact store, and
the answer is **weights, not episodes**
([`DATA_LAYER.md`](DATA_LAYER.md)). The scored episodes everyone worries
about are 10 KB each. A full 280-episode iteration writes 2.8 MB of
them, and the whole training run's episode traffic (14 MB) is smaller
than a single adapter artifact. The adapters are where the bytes are:
~110 MB written per iteration, then read back twice (once into the
serving pod, once into the next optimizer step), about 330 MB of S3
round-trips per iteration. That number grows with model size; the
episode number doesn't. One trap inside it: the initial and trained
adapters are the *same* 132 MB uncompressed. The initial one just gzips
4× smaller because untrained LoRA halves are all zeros, so size
estimates made from iteration 0 are wrong by 4×.

The mounted-volume idea from the 7/8 call therefore gets a split
verdict. For moving adapters it is a clear, measured win, and it would
delete the exec-websocket adapter push (13) outright: trainer, serving
pod, and the next iteration would simply open the same files. For
episodes it buys little that batching wouldn't — the generation step
already writes all 280 episodes as one 2.6 MB artifact; the fan-out
re-shards them into 280 tiny artifacts purely so each episode gets its
own lineage entry. And it does nothing about the dominant cost, which is
Theme 1's per-step overhead.

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
- The sandbox session filesystem API has no workdir contract:
  `upload_file(local, "pipeline.py")` works on the kubernetes flavor, is
  unimplemented on local (4), and throws `InvalidError` on Modal —
  three flavors, three behaviors for the same call, discovered only at
  runtime when code validated on one flavor ran on another (18). Define
  what a relative remote path means at the base class, or reject
  relative paths uniformly.

## Theme 5 — The sandbox travels: what the first ecosystem test found (task C2)

Everything above is about ZenML running the loop itself. Task C2 asked
the opposite question: what happens when *someone else's* framework owns
the loop and ZenML only supplies the sandbox? The framework was
`verifiers` (Prime Intellect), which the RL-environments ecosystem is
converging on for packaging "task + reward" as a reusable object. The
collision to test: our reward runs *inside* a sandbox where the
generated code executes; verifiers runs reward functions in its own
process, with no sandbox in sight.

It works. A verifiers reward function that opens a ZenML Sandbox
session per completion and runs our unmodified scorer inside it
reproduces the spike's rewards exactly — 18/18 canned completions
across five tasks — and verifiers' own concurrency machinery happily
ran four sandbox sessions at a time
([`verifiers_c2/`](verifiers_c2/README.md)). It took two adaptations,
both small and both generalizable: the blocking session calls go onto a
thread (their event loop must not stall while a pipeline runs), and
concurrency gets a cap (Theme 1's lesson travels — any framework will
stampede the sandbox backend if you let it).

Three findings matter beyond the mechanics:

1. **The sandbox is separable from the orchestration.** This is the
   first evidence that a ZenML Sandbox is useful with no ZenML pipeline
   anywhere in sight — created, used, and destroyed as a library call
   from inside someone else's harness. The loop owner and the sandbox
   owner can be different products. That reframes the "is ZenML the
   harness for this spectrum?" question: even where the answer is no,
   the sandbox can still be in the room.
2. **verifiers built its own sandbox lifecycle and welded it to one
   vendor.** Their new sandbox support (the "safer sandbox lifecycle"
   from their release notes) is per-rollout create/destroy with retries
   and teardown — and it constructs Prime Intellect's paid
   `prime_sandboxes` client directly, with no way to hand it anything
   else. The contract underneath is five duck-typed async methods
   (create, run a command, upload, read a file, delete), every one of
   which ZenML's session API can satisfy. The distance between "ZenML
   Sandbox as a verifiers backend" and reality is one hardcoded import,
   in their code. If that's a direction we want, it's time-sensitive:
   the contract is ossifying around Prime's cloud right now.
3. **Theme 2 is an ecosystem blind spot, not a ZenML quirk.** verifiers
   swallows any exception a reward function raises and scores the
   rollout 0.0 — the exact "bad completion, or broken harness?"
   ambiguity that entry 16 turned into hours of archaeology, rebuilt
   independently by another team. And their own docs concede that
   anything a reward needs from a sandbox must be captured before the
   sandbox is destroyed — which is precisely what F1's snapshots do,
   one layer down. Nobody in this ecosystem has solved failure
   forensics. We have the beginnings of it, and it would differentiate.

**Asks:** none for core plumbing — this theme is product direction, not
bug fixes. The concrete decision it tees up: whether to pursue an
upstream PR (or a published shim) making ZenML Sandbox a verifiers
backend while the contract is still five methods wide.

## The verdict question, widened

The honest summary for "would we recommend ZenML for this workload
today": the **shape** is right — the loop's phases are visible in the
dashboard, artifacts thread the iterations, steps can create and destroy
sandboxes, and `runs stop` and step retries mostly work — but the
**defaults assume short, small, deterministic pipelines**. Everything in
themes 1–2 is what happens when a workload is long, wide, and
stochastic. None of it looks architectural. All of it is defaults, caps,
heartbeats, and honest failure states.

The follow-up tasks (F1 snapshots, E3 measurement, C2 ecosystem test)
sharpen that verdict rather than change it. The snapshot work proves the thing Hamza
described on the 7/8 call already works: a failed sandbox can become an
object you reopen with one command and look around in. What blocks it is
that only the Modal flavor implements the API — a coverage problem, not
missing architecture. The measurement work says the same about data
movement: episodes need no redesign, adapters have one genuinely
motivated improvement (a shared volume), and the biggest measured cost —
73% of episode wall-clock spent on per-step fixed overhead — points
straight back at Theme 1's defaults, not at how bytes are stored.

Per [`framework_breakout.md`](framework_breakout.md), the closing question
is now wider than RL:
the same loop (generate → sandbox-verify → update an artifact → iterate)
underlies prompt evolution, eval campaigns, and trajectory export, and the
follow-up spikes are chosen to test whether ZenML is the harness for that
whole spectrum rather than for GRPO specifically. C2 supplied the first
datapoint, and it cuts both ways: where a framework already owns the
loop, ZenML's harness adds nothing they miss — but the sandbox slots
into their machinery today, and their own sandbox story is a single
vendor hardcoded. The findings above are the platform work that any of
those consumers would hit first.
