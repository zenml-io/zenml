# Full training run results (2026-07-09)

STOP GATE 4: 5 iterations × 35 curated tasks (`tasks/training_mix_v1.txt`,
derived from CALIBRATION.md buckets: 13 variance + 14 flat-imperfect +
8 saturated guards) × group size 8, temperature 1.0, learning rate 5e-6,
warm_vllm serving, Qwen3-4B-Instruct-2507 + LoRA rank 16.
280 episodes per iteration; runs `94ba8559` (failed, see below) and
`7c7d72c7` (the real run) in project `rl-spike`.

## Timeline

1. **First launch (`94ba8559`) died at iteration 0's `grpo_update` with
   CUDA OOM.** `per_device_train_batch_size` was tied to `group_size`;
   group 8 × 280 episodes overflowed the 24GB L4 (calibration at group 4
   fit, so this never showed before). Fixed by decoupling: micro-batch 2
   with `gradient_accumulation_steps = episodes/2` — identical gradient
   math (TRL computes advantages over the full generation batch before
   slicing into micro-batches), ~4× less activation memory. All later
   optimizer steps completed in ~8.5 min each.
2. **Relaunch (`7c7d72c7`) submitted in 12s** — ZenML reused the Docker
   build and shipped the changed code as an archive the pods download at
   startup. The still-running vLLM server from the failed run was
   adopted by the idempotent `ensure_vllm_server` step, saving the
   ~7 min model load.
3. Iterations 0–2 healthy; iterations 3–4 poisoned by sandbox
   environment failure (BREAKAGE_LOG entry 16); run then deadlocked on
   two zombie retries in iteration 4 (entry 15) and was force-stopped.
   The 5th optimizer step never ran.

## Reward per iteration

| Iter | Mean | Min | Max | Failures /280 | Flat groups /35 | grad_norm | Wall clock |
|---|---|---|---|---|---|---|---|
| 0 | 0.5874 | 0.2 | 1.0 | 161 | 22 | 0.079 | 45 min |
| 1 | 0.5859 | 0.2 | 1.0 | 160 | 23 | 0.077 | 47 min |
| 2 | 0.5771 | 0.0 | 1.0 | 163 | 21 | 0.094 | 52 min |
| 3 | 0.0000 | 0.0 | 0.0 | 280 | 35 | 0.000 | 47 min |
| 4* | 0.0236 | 0.0 | 1.0 | 284/289 | 32 | — (never ran) | — |

*Iteration 4 stats computed client-side from the 289 completed episode
artifacts (includes a few retried duplicates); its `log_iteration_metrics`
step never ran because the pipeline deadlocked.

Iterations 3–4 are **not** model collapse: inspected completions are
complete, valid programs (correct `.load()` usage included) that failed
the scorer's `import zenml` gate inside degraded sandbox pods (one GPU
node was under kubelet DiskPressure; the degradation outlived it). The
`grad_norm: 0.0` on the poisoned update is GRPO's group-relative
advantage working as a firewall: uniform rewards → zero advantage →
mathematically no update.

## Honest training verdict

Three clean optimizer steps (iterations 0→2) moved mean reward
0.587 → 0.586 → 0.577 — statistically flat. Three LoRA steps at lr 5e-6
over 35 groups is a very small amount of optimization; no conclusion
about whether the `.load()` skill is learnable at this scale can be
drawn from this run. What the run *did* establish:

- The full loop (generate via warm vLLM → 280-pod sandbox fan-out →
  GRPO update → adapter hot-reload) runs end-to-end at ~47 min per
  iteration, ~90% of it in the episode fan-out.
- Group 8 + temperature 1.0 gives 12–14 groups with within-group
  variance per iteration — real GRPO signal, matching calibration's
  prediction.
- Two new platform findings (BREAKAGE_LOG 15, 16) that only appear at
  multi-hour, multi-hundred-pod scale.

## What a next attempt should change

1. Reward channel: classify sandbox/import failures as `infra_error`
   (trainer already drops those episodes) and keep `check_import`
   stderr in the artifact (entry 16 workaround).
2. More optimization per wall-clock hour: the fan-out dominates
   (~40 min vs ~8.5 min training). Either more iterations on fewer
   tasks, or parallelize episodes across more nodes.
3. Consider a KL anchor (beta > 0) before running many more steps —
   with beta=0 nothing prevents slow policy drift once iterations
   accumulate.
4. Retry deadlock (entry 15) needs external watchdogging until fixed
   in core: alert when a step sits in `retrying` with no pod.

## Cost

~5.5 h × 2 × g6.2xlarge on-demand ≈ **$13.5** for this session
(both runs, including the OOM false start and the deadlocked tail).
Node group verified back at 0 after teardown.
