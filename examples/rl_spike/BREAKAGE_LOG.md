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
  in Stage 3. After the Michael follow-up, `--serving-mode warm_vllm`
  adds the real next workaround: a raw Kubernetes vLLM Deployment held warm
  on one GPU, while `grpo_update` trains on a second GPU. ZenML records the
  control steps and adapter artifacts, but the serving object itself still
  lives outside ZenML's component model.
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
- **Postscript (same day, found by an adversarial fresh-eyes review):** we
  then shipped a second instance of the same failure class ourselves: on
  Apple MPS the GRPO optimizer step can produce NaN gradients, and the
  pipeline published an **all-NaN adapter as its final artifact from a
  green run** — finite train_loss in metadata, nothing red anywhere.
  `grpo_update` now logs grad_norm to step metadata and refuses to save
  non-finite weights (fails the step loudly). The general lesson stands:
  numerical health of artifacts is invisible to ZenML; any "is this
  artifact sane" check is the user's job today.

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
- Settings keys fail open: `settings={"sandbox": ...}` passes validation
  (the key regex makes the `.flavor`/`:name` suffix optional) but
  `get_settings` only ever looks up `"type.flavor"`/`"type:name"` keys —
  a bare `"sandbox"` or `"orchestrator"` key is accepted and then
  silently never applied. Found while wiring GPU placement; the failure
  mode would have been every sandbox pod using the wrong image with no
  error pointing at the settings key.
- Custom parent images hit two sharp edges in the image builder (found
  using `vllm/vllm-openai` as parent, GPU_SETUP.md part 4): (a) the
  default `uv` installer runs plain `uv pip install`, and modern uv
  refuses to install into system Python without `--system` — the build
  dies with a bare "exit code 2" and no captured uv output; fix is the
  non-obvious `python_package_installer_args={"system": None}`. (b)
  ZenML's container entrypoint execs `python`, but Ubuntu-based images
  ship only `python3` — the pod crashes at start with "python: executable
  file not found"; fix is `apt_packages=["python-is-python3"]`. Both cost
  a full ~30GB image rebuild/push cycle to discover on a real image.
- **Hit:** Stage 1-2, 2026-07-08.

## 8b. Custom parent images: the full gauntlet (GPU smoke, Stage 2 execution)

Getting one trivial GPU step to run green on the remote stack with a
custom (vLLM) parent image took **five submissions**, each failing one
layer deeper. Individually these are paper cuts; the sequence is the
finding — every failure was discovered at pod runtime, minutes after a
multi-GB build/push/pull cycle:

1. `uv pip install` → bare "exit code 2" (no venv in parent; needs
   `python_package_installer_args={"system": None}`).
2. Pod StartError: entrypoint execs `python`, Ubuntu images ship only
   `python3` (needs `apt_packages=["python-is-python3"]`).
3. Pod Error: `No module named 'zenml'` — with a custom parent, ZenML
   does not install itself into the image; nothing checks at build time.
4. `No module named 'k8s_settings'` — a `.zen` directory at the *repo*
   root silently made the whole monorepo the source root, so the
   example's flat imports broke only in the container (fix: `zenml init`
   inside the example dir). Bonus trap: the fresh `.zen` reset the
   active project and stack, so the next submission silently went to the
   default LOCAL stack in the wrong project.
5. Green.

- **Also observed along the way:** the ~30GB image landed on a shared
  CPU node and got the orchestrator pod **evicted for node
  ephemeral-storage pressure** (workaround: pin the orchestrator pod to
  our own tainted GPU node, `ORCHESTRATOR_ON_GPU_NODE`); and runs whose
  orchestrator pod dies before ZenML code starts (StartError/eviction)
  stay in `provisioning` forever — the Kubernetes orchestrator only
  marks runs failed once its own code is running, so entry 6's zombie
  problem exists on Kubernetes too, just with a narrower window.
- **Severity:** chafes, repeatedly; each iteration costs a
  build/push/pull cycle (~10-40 min).
- **Core change:** build-time validation (import `zenml` inside the
  freshly built image before pushing would have caught 1-3 instantly), a
  documented "custom parent image checklist", and a failure-detection
  window that covers pod-start failures.
- **Hit:** Stage 2 execution, 2026-07-08.

## 9. `log_metadata` crashes the step on inf/NaN floats, with a cryptic error

- **Tried:** `log_metadata(metadata={"grad_norm": float(...)})` in the
  training step — and one iteration legitimately produced
  `grad_norm=inf` (gradient explosion on deliberately off-policy data;
  ML training emits non-finite floats routinely).
- **What happened:** The step failed with
  `requests.exceptions.InvalidJSONError: Out of range float values are
  not JSON compliant`, raised from deep inside the REST client
  (`json.dumps(allow_nan=False)`). No validation at the `log_metadata`
  API surface, no hint which key was the problem, and the *step* fails —
  after training succeeded — because *telemetry* was unserializable.
- **Workaround:** `json_safe()` in `steps/grpo_update.py` stringifies
  non-finite floats before logging.
- **Severity:** chafes (metrics code shouldn't be able to kill a
  succeeded step; the error names neither the key nor the fix).
- **Core change:** Validate/sanitize metadata values in `log_metadata`
  (stringify or drop non-finite floats with a warning), and name the
  offending key in any rejection.
- **Hit:** Stage 1, 2026-07-08.

## 10. ZenML's step log handler is not fork-safe with the S3 artifact store

- **Tried:** First real `generate_rollouts` on the GPU node: the step
  loads vLLM in-process, and vLLM forks a child process (`EngineCore`)
  to run the engine.
- **What happened:** The *actual* failure was a vLLM config error
  (Qwen3-4B declares a 262k context; the KV cache for one full-length
  request needs 36GiB and the L4 has ~11.6GiB after weights — fixed by
  passing `max_model_len=8192`). But stacked on top of it in the logs
  was a second, unrelated traceback: `RuntimeError: This class is not
  fork-safe` from fsspec/s3fs, raised out of
  `artifact_store.exists(logs_base_uri)` in ZenML's log storage. Chain:
  the step's log handler flushes to the S3 artifact store; the s3fs
  filesystem object (with its asyncio event loop) was created in the
  parent step process; the forked vLLM child inherited the handler,
  emitted a log line, and fsspec refuses to use a parent-process event
  loop from a child pid. Any log line emitted from any forked child
  inside a step produces this crash noise.
- **Workaround:** None needed for the run itself once the real error
  was fixed — but the fork-unsafe traceback sat *above* the real error
  in the pod logs and cost real time to see past. Worse: in the
  *successful* rerun, the same traceback repeats for **every single log
  line** the forked EngineCore emits (dozens of times in one green
  step), interleaved with the real output. Frameworks that fork (vLLM,
  torch DataLoader workers, multiprocessing pools) are the norm in ML
  steps, not the exception.
- **Severity:** chafes (error masking; users debugging their own step
  failure first have to diagnose ZenML's logging internals).
- **Core change:** Make the log storage handler fork-aware — e.g. check
  `os.getpid()` against the pid that created the filesystem and
  reinitialize (or silently drop child-process log flushes) instead of
  letting fsspec raise.
- **Hit:** Stage 3 smoke, 2026-07-08.

## 11. Mapped fan-out drags the full pipeline image onto shared nodes — and evicted other tenants' pods

- **Tried:** First Stage 3 smoke: `run_episode.map(seeds)` fanned out
  10 isolated step pods. Each isolated step pod runs the *pipeline
  image* — ~30GB here, because the RL image carries torch + CUDA +
  vLLM — even though `run_episode` itself is CPU-only glue that
  uploads files to a sandbox and reads back a JSON reward.
- **What happened:** The Kubernetes scheduler packed all 10 pods onto
  one shared CPU node (~50GB ephemeral disk). The single 30GB image
  pull tipped the node into `DiskPressure: True`, and the kubelet
  started evicting *other tenants' pods* — three staging ZenML server
  pods from unrelated namespaces were evicted before we force-stopped
  the run. On a shared staging cluster, our RL experiment degraded
  someone else's service.
- **Workaround:** Two-part. (1) `zenml pipeline runs stop <id>` worked
  exactly as hoped — it deleted the step jobs and marked the run
  `stopped` (positive counterpoint to entry 6's zombie behavior).
  (2) `EPISODE_STEP_SETTINGS` now pins episode step pods to our own
  tainted GPU node (100GB disk, image already present), same trick as
  the orchestrator pod.
- **Severity:** breaks (for multi-tenant clusters) — and the failure is
  invisible until a *neighbor* pages.
- **Core change:** The root issue is that a step which only shuffles
  files into a sandbox ships the pipeline's 30GB CUDA/vLLM image.
  ZenML *does* support per-step `DockerSettings`
  (`step.config.docker_settings` feeds the build), which would be the
  clean fix — but it is unclear whether that works for steps invoked
  at runtime inside a *dynamic* pipeline, since images build
  client-side at submission before the DAG shape exists (untested
  here; worth a follow-up). Short of that: docs for dynamic `.map()`
  on Kubernetes should warn that N mapped pods × fat image lands on
  whatever nodes have room, and recommend `pod_settings` pinning plus
  an ephemeral-storage request so the scheduler accounts for image
  size.
- **Hit:** Stage 3 smoke, 2026-07-08.

## 12. The server rate-limits its own fan-out: 10 concurrent mapped steps → 429s → dead steps

- **Tried:** Attempt 4 of the offline smoke: `run_episode.map(seeds)`
  started 10 episode pods, all healthy this time (image/pinning fixed).
- **What happened:** Each step pod independently calls the ZenML server
  at startup — auth, then
  `/api/v1/service_connectors/<id>/client?resource_type=s3-bucket` for
  artifact-store credentials, plus sandbox-session and metadata calls.
  Ten pods doing this simultaneously tripped the staging Pro server's
  rate limiting; the REST client retried, got "too many 429 error
  responses", exhausted its retry budget, and raised — killing 5 of 10
  episode steps *before the step function ever ran*. `run_episode`'s
  own never-raise containment could not help because the failure is in
  ZenML's input/credential resolution, not user code. So the platform's
  own fan-out primitive (`.map()`) generated enough control-plane
  traffic to get itself rate-limited by the platform's own server, at
  N=10. The full-scale run maps 400 episodes.
- **Workaround (first try, failed):** The Kubernetes orchestrator
  advertises `max_parallelism` ("Maximum number of step pods to run
  concurrently") as a per-run setting. Applied `max_parallelism=4`;
  the rerun launched all 10 pods simultaneously again and failed the
  same way. Reading the source: `max_parallelism` feeds the *static*
  `DagRunner` — **dynamic pipelines never consult it**. Their real
  concurrency cap is a `ThreadPoolExecutor` in the dynamic runner,
  sized by the undocumented env var
  `ZENML_DYNAMIC_PIPELINE_WORKER_COUNT` (default 10). So the
  documented knob silently does nothing for exactly the pipeline type
  whose `.map()` creates the fan-out problem. (The third knob,
  `parallel_step_startup_waiting_period`, is registration-time
  component config — not settable per run on a shared stack.)
- **Workaround (actual):** set
  `ZENML_DYNAMIC_PIPELINE_WORKER_COUNT=3` via `env` on the
  orchestrator pod settings.
- **Severity:** breaks (default settings, modest N, total step death;
  and 429 + backoff-until-dead is a bad failure shape for a *retryable*
  condition).
- **Core change:** Two things. (1) Make `max_parallelism` work for
  dynamic pipelines (or fail loudly when set on one), and promote
  `ZENML_DYNAMIC_PIPELINE_WORKER_COUNT` from undocumented env var to a
  real setting. (2) 429s deserve smarter client handling than generic
  retry-then-raise (respect Retry-After, longer/jittered backoff for
  fan-out startup calls, or a shared credentials cache seeded by the
  orchestrator so N mapped pods don't each re-fetch identical connector
  credentials).
- **Hit:** Stage 3 smoke, 2026-07-08.

## 13. `zenml.io.fileio` looks like a standalone file API — it isn't, and outside a step it fails at runtime

- **Tried:** The warm-vLLM design's original adapter transport: exec
  into the raw vLLM pod (which has `zenml[s3fs]` installed) and run a
  helper that calls `fileio.copy("s3://<artifact-uri>/data.tar.gz", ...)`
  to pull the adapter archive.
- **What happened:** `ValueError: No file systems were found for the
  scheme: s3://`. Reading the source: `fileio` only learns a remote
  scheme when a `BaseArtifactStore` subclass is *instantiated* —
  `S3ArtifactStore.__init__` registers a filesystem whose methods are
  bound to that instance and its credentials. That instantiation
  happens during ZenML step bootstrap (where connector-issued temporary
  credentials are fetched from the server). A process outside ZenML's
  execution context — our raw serving pod, but equally any user
  sidecar, cron job, or notebook without an active stack — has
  installed all the right packages and still can't use `fileio` for
  remote paths. The failure surfaces only at runtime, deep in a
  registry lookup. (Fallback attempt: raw `s3fs` with the node IAM
  role — `AccessDenied`; the credentials genuinely live only in the
  ZenML connector flow.)
- **Workaround:** Invert the transport: the *step* declares the
  adapter as a materialized `Path` input (ZenML downloads it with
  connector credentials — the canonical in-step pattern), then streams
  the bytes into the serving pod over the exec websocket
  (tar.gz + base64, same trick as entry 4). The serving pod needs no
  S3 access and no zenml install at all.
- **Severity:** chafes (the API's import-and-use surface hides a hard
  dependency on stack-component lifecycle; error message doesn't say
  "you're not in a ZenML context").
- **Core change:** Document the coupling prominently on `fileio`, and
  make the unregistered-scheme error explain the fix ("remote schemes
  are registered by an instantiated artifact store; outside a step,
  construct one via `Client().active_stack.artifact_store` with a
  connected client"). A supported "give me an authenticated filesystem
  for this artifact store" helper for out-of-step processes would
  close the gap properly.
- **Hit:** Stage 3 warm-vLLM smoke, 2026-07-08.

