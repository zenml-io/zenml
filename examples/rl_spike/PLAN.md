# RL spike plan — v1 (post Alex/Michael call, 2026-07-08)

*Assignment (Hamza, post-AIE meeting): build a toy RL loop on ZenML — post-train a small open model to write better ZenML pipelines. The REAL deliverable is a breakage report: where ZenML works, chafes, or breaks for RL workloads. A mediocre model with a sharp findings doc is a successful spike.*

*Decisions locked on the call: task stays "write ZenML pipelines" (reward must be computed in the sandbox where the harness ran — that's the RL-specific property a structured-extraction toy would hide); v0 is **synchronous, one dynamic pipeline**; **TRL + vLLM** as the stack (common, self-hosted, stresses our infra); no full-span framework (verifiers/prime-rl would swallow the whole loop into one step — no ZenML tracking, at that point you'd just use their platform); **Alex builds v0, Michael reads up then iterates with him** toward async / two pipelines / shared storage.*

*Post-Michael follow-up, same day: keep the offline vLLM-in-step path as the smokeable proof, but add the real next architecture as `--serving-mode warm_vllm`: two GPUs, one raw Kubernetes vLLM server kept warm, one GPU for `grpo_update`, and LoRA adapter transport through ZenML `Path` artifacts rather than an ad-hoc S3 prefix.*

## 1 · v0 architecture: one synchronous dynamic pipeline

```python
@pipeline(dynamic=True)
def rl_spike(task_set_id: str, iterations: int = 5, group_size: int = 8):
    tasks = load_tasks(task_set_id)          # ~50 "write a ZenML pipeline that X" prompts
    adapter = init_lora()                    # artifact: LoRA adapter dir (MBs, not full weights)
    for i in range(iterations):
        # ROLLOUT — fan out; each episode = generate pipeline.py via vLLM, then run+score it
        episodes = run_episode.map(          # sandbox component: no ZenML inside the container
            task=repeat_each(tasks, group_size), adapter_ref=adapter
        )
        # TRAIN — one GPU step; GRPO update over the scored group
        adapter = grpo_update(episodes, adapter)
        log_iteration_metrics(i, episodes)
    return adapter
```

- **`run_episode`** (sandbox): call vLLM with the task prompt + a slim dynamic-pipelines cheatsheet → get `pipeline.py` → execute it against a local stack *inside the sandbox* → emit `{prompt_ids, completion_ids, reward, logs}` as the step output. Reward is scripted 0–1: parses/imports (+0.3), defines a `@pipeline` and runs green (+0.4), spec checks — step count, expected output artifact (+0.3). Single-turn on purpose (one completion per episode): it sidesteps TRL's known multi-turn weakness (see §2) and keeps v0 honest.
- **`grpo_update`** (GPU step operator): run TRL's `GRPOTrainer` for one iteration where the experimental **`rollout_func`** simply *returns the pre-generated episodes loaded from the artifacts* (token IDs + rewards). TRL then owns only the math — advantages, loss, gradient step, adapter save. This is the trick that keeps the visible loop in ZenML steps (tracking, retries, lineage per phase) while TRL stays a library, not an orchestrator. Precedent: Eval Protocol's TRL integration uses `rollout_func` exactly this way — TRL calls it, external system returns token IDs + rewards ([docs](https://evalprotocol.io/integrations/trl-trainer)).
- **Task difficulty control:** small Qwen (4–8B) + *dynamic* pipelines (post-cutoff API for tiny models) means the reward won't saturate at 100%. If it does anyway, shrink the model or tighten spec checks — Michael's "just use a shittier model" lever.

## 2 · Confirmed mechanics (so nobody re-researches these)

- **TRL `rollout_func`:** experimental but real, and recently *decoupled from the vLLM backend* (dispatch moved to top-level `_generate_single_turn`, [PR #5122 / issue #5121](https://github.com/huggingface/trl/issues/5121)) — custom rollouts no longer entangled with inference internals. API may still change; pin the TRL version.
- **TRL's known agentic gap:** multi-turn rollouts break importance-sampling assumptions in server mode (per-step prefixes get lost — [issue #4543](https://github.com/huggingface/trl/issues/4543)). Our single-turn episodes avoid this entirely; if we ever go multi-turn, that issue is the first thing to reread. TRL is also [building an async trainer](https://huggingface.co/blog/async-rl-training-landscape) — relevant for v2, not now.
- **Weight refresh into vLLM (Michael's question on the call):** solved upstream. Run the vLLM server with `VLLM_ALLOW_RUNTIME_LORA_UPDATING=1`, then after each `grpo_update` POST the new adapter to **`/v1/load_lora_adapter` with `load_inplace=true`** — built precisely for RL adapter swap without restarting the server ([vLLM LoRA docs](https://docs.vllm.ai/en/latest/features/lora/)). Alternative if the vLLM server can't see the artifact store path: the **filesystem/S3 LoRAResolver plugin** ([docs](https://docs.vllm.ai/en/stable/design/lora_resolver_plugins/)) resolves unknown adapter names from a directory/bucket on first request — i.e., "write adapter artifact to a known location, request it by versioned name." v0 can even just restart vLLM per iteration; note the pain, that's data for the findings doc.
- **vLLM topology for v0:** one long-lived vLLM server on a GPU box, episodes call it over HTTP. (TRL's own server/colocate modes are for when TRL does the generating — we don't, in v0.)
- **Sandboxes are shipped, not pending:** the sandbox stack component merged in zenml PR #4866 and has been released since **0.95.0**, with **local, Modal, and Kubernetes** flavors in-tree (`src/zenml/sandboxes/`, `integrations/modal/sandboxes/`, `integrations/kubernetes/sandboxes/`). The session API covers everything `run_episode` needs: `exec`/`aexec`, `upload_file`/`download_file`, snapshots, destroy-on-exit (#4986). v0 can use the local sandbox flavor; switch to Modal/Kubernetes for throughput runs.
- **Known ZenML facts going in:** trigger-and-poll between pipelines exists in OSS (`Client().trigger_pipeline` + `wait_for_pipeline_run_to_finish`); no live channel between running pipelines; step outputs are artifact-in/artifact-out; `.map()` fan-out parallelism is the orchestrator's, so the local stack runs serially — use a remote stack for any throughput claims. The DAG view with ~400 mapped episode steps will crawl; that's the long-wanted "collapse mapped steps" UI improvement, park it as a finding.

## 3 · Iteration ladder (each rung = new findings, stop when learning stops)

1. **v0 — synchronous, one pipeline** (above). Answers: does the loop fit one dynamic pipeline; where does data transport hurt (Hamza's `s3.getObject` worry); adapter artifact story; sandbox throughput/cleanup.
2. **v1 — overlap rollout and training** within the pipeline (`.submit()` futures: start generating iteration N+1's episodes against the *old* adapter while N trains). Tests the off-policy tolerance point from the call — frameworks accept weights a few versions stale to keep GPUs busy.
3. **v2 — split into two pipelines** (rollout pipeline triggered per iteration, training pipeline waits by polling). Only if v0/v1 strain — this is the "one pipeline or two" question answered by evidence instead of debate. Forces the shared-storage design for weights/episodes Michael raised.
4. **v3 (optional) — swap the task** to structured extraction to prove the loop is task-agnostic, and/or wrap the episode harness in Kitaru (see §5).

## 4 · Who does what

- **Alex:** builds v0 end-to-end (task set, cheatsheet prompt, sandbox episode step with in-sandbox reward, `grpo_update` step, vLLM serving + adapter swap). Keeps a running **breakage log** — every workaround is a finding.
- **Michael:** reading first — the [RL-stages article](https://alexstrick.com/posts/2026-06-16-rl-stages.html) (the five-slices framing from the call) + this doc; then reviews v0 with the core-lens questions: is the data transport acceptable, what would core need to change, sandbox behavior under fan-out, GPU step operator ergonomics. Leads the v1/v2 iterations with Alex.
- **Joint findings doc (the actual deliverable):** (1) ranked list of where ZenML broke/chafed; (2) one-pipeline-vs-two verdict with evidence; (3) data-layer verdict with specifics; (4) cost of one iteration (nothing tracks this today — measure by hand, that absence is itself a finding); (5) honest "would we recommend ZenML for this workload now, and what's the shortest path to yes."

## 5 · Kitaru notes (parked — do not build during the spike)

- Michael's question from the call — "should every episode be a Kitaru run?" — has a cheap future answer: if the harness inside the sandbox were Kitaru-wrapped, every episode gets trace capture, cost, and replay for free; tag episodes to group them per RL run. v3 material at most.
- Keep the reward function's signature compatible with the planned Kitaru `score=` hook (plain callable → 0–1) so the spike's reward code and Kitaru's eval work converge rather than fork.
- The end-goal loop Alex sketched on the call (Kitaru traces → replay identifies failure modes → reward function updated → re-run RL) is the bridge between the two tracks — it needs nothing from the spike except that episodes and scores stay artifacts with lineage.
- Capacity: this spike and the Kitaru build items (score hook, Proxima PoC gaps) both draw on Alex — sequencing is an explicit call for Hamza's plan-by-EOD, not an implicit one.
