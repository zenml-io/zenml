# E3: what the RL loop actually moves through the artifact store (2026-07-09)

*Measured, not estimated — the named evidence for Hamza's `s3.getObject`
worry and the mounted-volume-layer question. All numbers from runs
already on the staging server: training run `7c7d72c7` (5 × 280 episodes,
warm vLLM, group 8) and the four calibration chunks (`f411036a`,
`9d51a334`, `93f4246b`, `6a6e0480`; offline, group 4). Reproduce with
`measure_data_layer.py` (read-only: walks step outputs, stats the S3
objects directly, loads episode artifacts for their in-sandbox timing
dicts).*

## The byte inventory (training run, 4.5 iterations)

1,419 artifacts, 1,419 S3 objects (every artifact is exactly one
object), **477 MB total**, ~112–120 MB per iteration:

| Channel | Artifacts | Bytes | Share |
|---|---|---|---|
| Trained adapters (`grpo_update` outputs) | 4 | 423.0 MB (~106–115 MB each) | **89%** |
| Initial adapter (`init_lora`) | 1 | 26.7 MB | 6% |
| Episodes (`run_episode` outputs) | 1,398 | 14.2 MB (mean 10.1 KB, p95 12.9 KB, max 40 KB) | 3% |
| Generation seeds (token IDs + logprobs + completions, one artifact per iteration) | 5 | 12.9 MB (~2.6 MB each) | 3% |
| Everything else (tasks, endpoints, metrics) | 11 | < 0.1 MB | ~0% |

Two immediate surprises:

1. **Episodes are noise.** The entire 5-iteration episode fan-out —
   1,398 scored episodes with token IDs and logprobs — wrote 14 MB.
   One iteration's episode payload is 2.8 MB, less than half a single
   phone photo. Bandwidth is not the problem.
2. **Weights dominate, and the growth is entropy, not data.** Both the
   initial and trained adapters are the *same* 132 MB of fp32 LoRA
   tensors uncompressed (rank 16 × 7 target modules on Qwen3-4B ≈ 33M
   params). The initial adapter gzips to 26.7 MB because LoRA B-matrices
   start as zeros; one optimizer step later the weights are
   incompressible noise and the artifact is 106–115 MB. Anyone
   estimating storage from the first adapter will be off by 4×.

Per-iteration weights movement through S3: ~110 MB written
(`grpo_update` output), then read back twice (once by
`load_adapter_into_vllm`, which streams it into the serving pod over the
exec websocket precisely because pods share no filesystem, and once by
the next `grpo_update` as its input) — ≈ **330 MB of S3 round-trips per
iteration for the weights channel** vs 5.6 MB for episodes+seeds.

## The request inventory (the actual `s3.getObject` math)

- Per iteration the episode fan-out creates **280 artifact versions**:
  280 uploads, 280 server-side registrations (version + metadata +
  visualization checks), and 280 downloads when `grpo_update` ingests
  them. Object *count*, not object *size*, is the pattern.
- Measured sequential load latency: **293 ms per episode artifact**
  (server round-trip + S3 GET; payload ~10 KB, so it's almost pure
  fixed cost). 280 sequential input loads ≈ 82 s — which fits inside
  the measured `grpo_update` overhead of 120–222 s per step (step
  wall-clock minus TRL's `train_runtime`; the remainder is base-model
  load and adapter save/upload).
- The same 280-registrations-at-once pattern is one of the ingredients
  of the 429 storm (BREAKAGE_LOG entry 12): each episode pod also does
  its own credential fetch and metadata writes against the same server.

## Where episode wall-clock actually goes (training run, n=1,398)

| Segment | Mean | Median | p95 |
|---|---|---|---|
| Episode step wall-clock | 117.2 s | 105 s | 177 s |
| — in-sandbox: session create | 13.4 s | 12.1 s | 20.6 s |
| — in-sandbox: file upload | 0.4 s | 0.4 s | 0.8 s |
| — in-sandbox: scorer execution | 17.8 s | 16.4 s | 44.0 s |
| — **everything else (harness overhead)** | **85.6 s (73%)** | 75.7 s | 126.1 s |

The harness overhead is pod scheduling, image/code bootstrap, credential
fetch, input load, and the ~10 KB artifact write — i.e. the fixed cost of
"a step" — and it is **2.7× the useful work** (31.6 s in-sandbox mean).
The calibration chunk shows the same shape with worse absolute numbers
(overhead mean 187 s while sharing the GPU node with offline vLLM
generation). This is the per-step-cost story of FINDINGS.md Theme 1 in
numbers, and no data-layer change fixes it.

## Verdict: is episodes-through-the-artifact-store an anti-pattern?

**At this scale, no — and the bytes never will be the reason.** 2.8 MB
per iteration of episode payload is irrelevant next to a 110 MB adapter.
What *does* scale badly is per-artifact fixed cost, in three places:

- 280 registrations/iteration against the control plane (already a
  contributor to entry 12's 429s);
- 293 ms × N sequential ingest in the trainer (~82 s at N=280; at a
  real-RL N=16,000 that's 78 minutes — the pattern breaks on *count*,
  not size);
- 73% harness overhead per episode step, which dwarfs everything above.

Worth noting: the loop already contains the batched alternative. The
generation step writes **all 280 episodes as one 2.6 MB artifact**; the
fan-out then re-shards them into 280 single-object artifacts purely so
each episode gets its own lineage node, reward metadata, and (since F1)
snapshot ref. The data-layer question is really "what lineage
granularity is worth 280× the fixed cost" — a product question, not a
bandwidth one.

**What a mounted-volume layer would and wouldn't buy (Hamza's
question):**

- **Weights channel: yes.** 330 MB of S3 round-trips per iteration
  becomes a file handoff; the exec-websocket adapter push into the vLLM
  pod (BREAKAGE_LOG entry 13's workaround) stops existing entirely,
  because trainer, server, and the next iteration would see the same
  files. This is the concrete, measured beneficiary — and it grows with
  model/rank while episodes don't.
- **Episode channel: marginal.** It would remove the per-episode
  registration/GET fixed costs, but so would batching episodes per task
  group, with no new infrastructure. The bytes were never the issue.
- **The big lever it doesn't touch:** 73% per-episode harness overhead.
  A volume layer optimizes the 27% (partially); the fan-out's real cost
  is step fixed cost (Theme 1 asks: placement, concurrency caps,
  lighter per-step bootstrap).

Storage/cost footnote: the whole spike's artifact residue is ~0.9 GB
across all runs measured (< $0.03/month on S3); request costs are
similarly noise. The anti-pattern risk is server load and latency, never
the AWS bill.
