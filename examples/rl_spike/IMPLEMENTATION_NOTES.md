# RL spike — implementation notes (build plan)

*Written at Stage 0 gate, 2026-07-08, after the design interview. This is the file-by-file plan for v0. Deviations from PLAN.md discovered during the build get appended to the "Deviations" section at the bottom — read that section last, it wins over anything above it.*

## Decisions made in the Stage 0 interview

1. **No vLLM server in v0.** Generation happens *inside* a per-iteration GPU step (`generate_rollouts`) using vLLM's **offline batch API** (`vllm.LLM.generate()`), not the OpenAI-compatible HTTP server. The LoRA adapter is passed per call via `LoRARequest(name, id, path)` — no server-side adapter state, no hot-swap endpoint, no external Deployment. Michael concurred ("I'll just do it in-step for now, but note that people will want more flexibility" — that note is a logged finding). The deployer-hosted vLLM service is the documented runner-up for v1.
2. **The sandbox only runs and scores.** The episode step does not talk to any model. `generate_rollouts` produces the completion text + exact token IDs (same process as the tokenizer); the sandbox executes the generated `pipeline.py` against a throwaway local ZenML store and computes the reward.
3. **Task set:** Claude drafts all 50 tasks; Alex spot-checks a 10-task sample before Stage 1 closes.
4. **Spec checks are declarative.** Each task record carries a spec dict (see schema below); one generic in-sandbox checker awards partial credit. No per-task check code.
5. **Model:** `Qwen/Qwen3-4B-Instruct-2507` for GPU runs; `Qwen/Qwen3-0.6B` for the CPU dry-run `grpo_update` proof. Non-thinking instruct variant on purpose: single-turn completions with no `<think>` preamble.

## v0 pipeline shape (revised from PLAN.md §1)

```python
@pipeline(dynamic=True, enable_cache=False)
def rl_spike(iterations: int = 5, group_size: int = 8, ...):
    tasks = load_tasks(...)                     # list of task records
    adapter = init_lora(...)                    # LoRA adapter dir artifact
    for i in range(iterations):
        # ONE GPU step: vLLM offline batch over all tasks x group_size
        completions = generate_rollouts(tasks, adapter, group_size)
        # fan out: each completion runs + scores inside a sandbox session (CPU)
        episodes = run_episode.map(completions, ...)
        # ONE GPU step: TRL GRPOTrainer, rollout_func returns pre-generated episodes
        adapter = grpo_update(episodes, adapter)
        log_iteration_metrics(i, episodes)
```

Differences from the PLAN.md sketch, and why:

- **`generate_rollouts` is a separate batched step** instead of each episode calling a vLLM server (interview decision 1). vLLM batch inference over ~400 prompts is also far faster than 400 HTTP round-trips.
- **`enable_cache=False` on the pipeline** (and explicitly on rollout steps). ZenML caches by (step code + inputs); in any iteration the `group_size` rollouts for one task have identical inputs, so caching would serve one sampled completion 8 times → zero within-group variance → GRPO advantages are all zero and learning silently stops. Logged as a finding (caching assumes deterministic steps; RL rollouts are deliberately nondeterministic).
- **`run_episode.map()` maps over the completions artifact**, not over `repeat_each(tasks, group_size)` — ZenML mapping only works over artifacts produced in the same run, so the expansion must happen inside a step anyway, and the natural expansion point is `generate_rollouts` (one output record per completion).
- **Episode failure containment:** dynamic pipelines have no `CONTINUE_ON_FAILURE`; one crashed episode step would fail the whole run. `run_episode` therefore never raises — any sandbox/execution failure becomes `reward=0.0` with the error captured in the episode record.

## File-by-file plan

```
examples/rl_spike/
├── PLAN.md                      # pre-existing; untouched
├── IMPLEMENTATION_NOTES.md      # this file
├── BREAKAGE_LOG.md              # the actual deliverable; updated live
├── README.md                    # Michael-cold-readable: what this is, how to run the dry-run
├── requirements.txt             # pinned: trl, peft, transformers, torch; vllm marked GPU-only
├── tasks/
│   └── tasks.jsonl              # 50 records: {id, prompt, difficulty, spec{...}}
├── prompts.py                   # system prompt + slim dynamic-pipelines cheatsheet
├── generation.py                # Generator interface: VLLMGenerator | StubGenerator
│                                #   selected by one config value (dry_run: bool)
├── stub_completions/            # canned completions for the dry run:
│                                #   perfect / runs-but-wrong / runtime-failure / syntax-error
├── sandbox_scripts/
│   └── score_pipeline.py        # uploaded into each sandbox session; runs the generated
│                                #   pipeline.py under a throwaway ZENML_CONFIG_PATH
│                                #   (fresh sqlite store), applies the declarative spec
│                                #   checks against the local run, prints reward JSON
├── steps/
│   ├── load_tasks.py            # read tasks.jsonl -> list artifact
│   ├── init_lora.py             # create initial (empty/identity) LoRA adapter dir
│   ├── generate_rollouts.py     # GPU (or stub): batch-generate; emits one episode-seed
│   │                            #   record per (task, rollout_index): prompt_ids,
│   │                            #   completion_ids, completion_text, task spec
│   ├── run_episode.py           # sandbox session per completion: upload code + scorer,
│   │                            #   exec, collect reward JSON; never raises
│   ├── grpo_update.py           # TRL GRPOTrainer step with rollout_func returning the
│   │                            #   pre-generated episodes; saves new adapter artifact
│   └── log_metrics.py           # per-iteration: mean/max reward, reward histogram,
│   │                            #   wall-clock per phase (by-hand cost capture)
├── pipelines/
│   └── rl_spike_pipeline.py     # the dynamic pipeline above
├── run.py                       # CLI: --dry-run, --iterations, --group-size, --num-tasks
└── tests/
    └── test_reward.py           # canned completions -> exact expected 0-1 scores
```

## Task record schema

```json
{
  "id": "map_reduce_squares",
  "difficulty": 2,
  "prompt": "Write a ZenML dynamic pipeline that squares each number in [1,2,3,4] using a mapped step and sums the results.",
  "spec": {
    "min_steps": 3,
    "required_api": [".map("],
    "expected_output": {"step": "reducer-like", "value": 30}
  }
}
```

Reward (scripted, computed in-sandbox by `score_pipeline.py`):
- +0.3 — file parses (`ast.parse`) and imports cleanly
- +0.4 — defines a `@pipeline(dynamic=True)` and a run completes green against the sandbox-local store
- +0.3 — spec clauses, partial credit per clause (step count, required API strings, expected output artifact value)

## Cost/timing capture (nothing in ZenML tracks this — planned finding)

Every phase step records `wall_clock_seconds` into its output metadata via
`log_metadata`; `log_iteration_metrics` aggregates per-iteration totals.
Token counts (prompt/completion) recorded per episode. Stage 3 multiplies by
instance hourly price by hand.

## Dry-run mode (Stage 1 bar)

`--dry-run` swaps `VLLMGenerator` for `StubGenerator` behind the same
interface (one config value, zero code changes elsewhere). The stub tokenizes
canned completions with the real Qwen tokenizer so `grpo_update` receives
honest token IDs. `grpo_update` runs a real `GRPOTrainer` step on CPU with
Qwen3-0.6B and saves a real LoRA adapter artifact the next iteration loads.
Local stack + local sandbox flavor throughout; note the local sandbox is a
bare subprocess, so `score_pipeline.py` must set `ZENML_CONFIG_PATH` to a
temp dir or the generated pipelines would hit the real (staging Pro!) server.

## Deviations discovered during the build

1. **TRL pin is `trl==1.7.1`, not 0.2x.** `rollout_func` doesn't exist in
   the 0.x line at all; it's mainline (still experimental) in 1.7.1. Its
   real contract also differs from its docstring: prompts arrive already
   repeated `num_generations` times and the function returns exactly one
   completion per entry (see BREAKAGE_LOG.md entry 5). Verified with a
   standalone CPU proof before wiring into the step (one optimizer step,
   all 56 lora_B tensors changed, adapter save/reload round-trip green).
   Caveat discovered later: that proof's tiny grad_norm (≈2.3) was an
   artifact of its *fake* old-logprobs — they made every importance ratio
   collapse to ~0, so PPO-style clipping zeroed most of the gradient. With
   real logprobs (ratio ≈ 1, gradient flows fully), canned completions are
   maximally off-policy text and grad norms in the wired pipeline reach
   1e5–1e6 before TRL clips the update to `max_grad_norm=1.0`. On Apple
   MPS this occasionally overflows to NaN — `grpo_update` now logs
   grad_norm and hard-fails rather than save non-finite weights (see
   BREAKAGE_LOG entry 7 postscript). Real sampled completions (Stage 3)
   are on-policy by construction and should not exhibit this magnitude.
2. **The scorer isolates itself.** `score_pipeline.py` sets
   `ZENML_CONFIG_PATH` to a fresh temp dir *in its own process* before any
   zenml import, instead of relying on the episode step to pass sandbox
   paths it can't know. Subprocesses (the generated pipeline) inherit it.
3. **File transfer into the local sandbox goes through exec+base64**
   because the local flavor doesn't implement upload/download
   (BREAKAGE_LOG.md entry 4).
4. **Batch config for grpo_update:** micro-batch = `group_size`
   completions, `gradient_accumulation_steps` = number of tasks,
   `max_steps=1` — exactly one optimizer pass per iteration over all
   episodes with bounded memory; `beta=0` so no reference model is loaded.
5. **`init_lora` produces a real (identity) adapter** up front rather than
   letting GRPOTrainer create one internally, so iteration 1's generation
   step loads an adapter exactly the way iteration N does — no special
   first-iteration path.
6. **(Stage 2) Remote placement lives in `k8s_settings.py`**, applied
   conditionally in the pipeline body via `with_options(runtime=ISOLATED,
   settings=...)` when `dry_run=False`, and Docker settings attach in
   `run.py` before submission (the image builds client-side). GPU steps:
   `init_lora`, `generate_rollouts`, `grpo_update` (also switched to bf16
   on CUDA — fp32 4B wouldn't fit the 24GB L4 comfortably, and would OOM
   the 16GB CPU nodes). Watch out: component settings keys must be
   flavor-scoped (`"orchestrator.kubernetes"`, `"sandbox.kubernetes"`) —
   bare `"orchestrator"` keys validate but are silently ignored
   (BREAKAGE_LOG entry 8). `gpu_smoke.py` is the one-step CUDA smoke
   pipeline for GPU_SETUP.md part 6.
7. **(Stage 3 direction) Warm vLLM mode is now wired but unverified.**
   `run.py --serving-mode warm_vllm` starts or patches a raw Kubernetes
   vLLM Deployment + ClusterIP Service from a ZenML step, then keeps that
   server warm across iterations. The loop uses two GPUs: the vLLM server
   holds one GPU continuously, and `grpo_update` schedules on the other.
   Adapter transport stays inside ZenML's artifact model: `init_lora` and
   `grpo_update` still return `Path` artifacts, ZenML stores those
   directories as `<artifact_uri>/data.tar.gz`, and
   `load_adapter_into_vllm` passes the unmaterialized artifact URI to an
   exec helper in the vLLM pod. The helper copies the archive into
   `/adapters/<adapter-name>`, extracts it, and POSTs
   `/v1/load_lora_adapter` with `load_inplace=true`. On normal completion,
   `delete_vllm_server` deletes the raw Deployment and Service; if the run
   is killed, manual scale-down still matters. This is intentionally not a
   ZenML model deployer; the spike is testing the gap between ZenML lineage
   and raw serving infrastructure.
8. **Warm-vLLM caveat before first run** *(superseded by deviation 10)*:
   the original design had the vLLM pod pull the adapter archive itself
   via `zenml.io.fileio` — that cannot work (fileio's remote schemes
   only exist inside ZenML step bootstrap; see BREAKAGE_LOG entry 13)
   and the node IAM role has no S3 access either. The verified design
   materializes the adapter in the step and pushes it into the pod over
   the exec websocket.
9. **(Stage 3 execution) Four fixes from the first real offline runs:**
   (a) `max_model_len=8192` on both the offline `LLM(...)` and the warm
   `vllm serve` command — Qwen3-4B declares a 262k context and the KV
   cache for one full-length request (36GiB) doesn't fit an L4
   (BREAKAGE_LOG entry 10 documents the fork-safety noise that sat on
   top of that error). (b) Episode step pods are pinned to the RL GPU
   node — letting the mapped fan-out schedule freely pulled the 30GB
   pipeline image onto a shared CPU node and evicted other tenants'
   pods via DiskPressure (entry 11). (c) Sandbox image 0.2 installs
   `zenml[local]` — bare `zenml` cannot run pipelines against the
   scorer's throwaway sqlite store, which silently floored every
   episode at reward 0.3 ("pipeline exited nonzero"); episodes now also
   record `run_output_tail` so that failure mode is diagnosable from
   the artifact. (d) `SamplingParams(seed=os.urandom(...))` — a fresh
   vLLM engine reproduces identical samples per run, so with an
   unchanged adapter, iteration 2's completions were byte-identical to
   iteration 1's (612 tokens both times). Postscript: even with random
   seeds the completions for the difficulty-1 tasks stayed identical —
   the distribution is near-argmax at every token on these formulaic
   prompts. Not a bug, but it means the full run needs harder tasks
   (and possibly higher temperature) or GRPO groups stay flat.
10. **(Stage 3 execution) Warm-vLLM mode is now VERIFIED** — green
    end-to-end run (ensure server → push+hot-load adapter → HTTP
    rollouts → sandbox episodes → GRPO update on the second GPU →
    delete server). Five fixes on the way, all in the example:
    (a) server image 0.2 installs `boto3` in the same pip command as
    `zenml[s3fs]` — aiobotocore's botocore pin breaks the boto3 baked
    into the vLLM image, and vLLM imports boto3 at startup
    (crash-loop); (b) the adapter transport was inverted to
    materialize-in-step + exec-websocket push, because `fileio` can't
    work in the raw pod (BREAKAGE_LOG entry 13) — the server image no
    longer needs zenml at all; (c) `_post_json` tolerates vLLM's
    plain-text "Success" responses; (d) completion token IDs come from
    the logprobs entries via `return_tokens_as_token_ids` instead of
    re-tokenizing text (stop token made counts differ by one);
    (e) prompt_ids are tokenized explicitly (`apply_chat_template`'s
    return type varies across transformers versions; a str became
    per-character "ids" and crashed TRL). Timing: warm iteration
    wall-clock 209.6s vs 555–727s offline — the offline path pays
    169–226s of vLLM engine load per iteration, the warm server pays
    it once.
11. **(Post-smoke) Task set v2 + reward v2, designed for GRPO variance.**
    The Stage 3 smoke exposed that difficulty-1 tasks produce all-1.0
    groups AND near-argmax identical samples — zero within-group
    variance, zero gradient. The redesign targets pass rates in the
    20–80% band and a finer reward ladder:
    - Weights rebalanced to 0.2 parse + 0.3 runs-green + 0.5 spec
      (the base model never misses parse/run; the reward mass now sits
      where samples differ). Dry-run expected mean changes from 0.5125
      to 0.4458.
    - New declarative clauses in `score_pipeline.py`, all graded from
      the sandbox run's own history: `step_run_counts` (exact
      invocation counts per step function name — grades fan-out width,
      loop iterations, and which conditional branch ran, from ZenML's
      store instead of source text; mapped `map:<name>:<i>` and
      repeated `<name>_<k>` invocation ids verified empirically),
      `forbidden_source` (anti-hardcoding: the answer literal must not
      appear in source), and `expected_outputs` (one clause per listed
      value).
    - `tasks/tasks.jsonl` regenerated: 55 tasks (7 D1 keepers incl.
      the three dry-run stub tasks unchanged, 14 D2 compute-through-DAG
      chains, 18 D3 conditionals/two-stage maps, 16 D4 runtime-width
      fan-outs and loops). Harder prompts dictate step function names
      so shape clauses are checkable. Re-mapping over a mapped result
      (`add_one.map(double.map(nums))`) verified working locally via
      the real scorer before authoring tasks that require it.
    - Nine OUT-OF-DISTRIBUTION tasks (Alex's suggestion): invented
      operations with nonsense names (`blorbify`, `zorp`, `florp`,
      `gruntle`), arbitrary rules no textbook contains (replace every
      3rd character with 'q', loop until the value ends in digit 1),
      and ACTIVELY MISLEADING names (`fake_triple`: a step named
      triple that must add 4; `crossed_reports`: even numbers must
      call report_odd; `mixed_signs`: add_one subtracts). Standard
      tasks like fibonacci/collatz are all over the base model's
      training data, so it can score by retrieving the algorithm;
      these tasks only score if the model reads the spec and follows
      it against its priors — which is also where within-group sample
      disagreement (GRPO's signal) is most likely.
    - Before the full run: a CALIBRATION run (1 iteration, all tasks,
      group 4, learning rate ~0) to measure per-task reward mean and
      within-group variance; drop or re-tier tasks that are uniformly
      1.0 or uniformly floored. This also catches wrong expected
      values in specs.

## Deviation 12: full training run (2026-07-09)

Three example-side changes for STOP GATE 4, results in TRAINING_RUN.md:

1. `grpo_update` micro-batching decoupled from `group_size`
   (`per_device_train_batch_size=2`, grad-accum `episodes/2`): group 8 ×
   280 episodes CUDA-OOMed the L4 when the micro-batch was tied to the
   group. Verified against TRL 1.7.1 source: the only constraint is
   `generation_batch_size % num_generations == 0`, and advantages are
   computed over the full generation batch before micro-slicing, so
   groups may straddle micro-batches.
2. `temperature` threaded through the pipeline signature into both
   generation steps (was a step default nobody could reach from run.py);
   `--temperature` CLI flag added.
3. `--task-ids-file` CLI flag + `tasks/training_mix_v1.txt` (the
   calibration-derived 35-task mix), so the training mix is versioned
   instead of a 35-item command line.

Also learned: re-submitting after a code-only change reuses the Docker
build and ships code via the artifact-store archive (12s submission),
and the idempotent `ensure_vllm_server` adopts a still-running server
from a previous failed run — together they make crash-iterate loops on
the warm stack pleasantly cheap.
