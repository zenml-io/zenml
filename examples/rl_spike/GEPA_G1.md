# G1 · GEPA prompt evolution on the spike harness — findings

*Task G1 from `framework_breakout.md` Track G, run 2026-07-09 on branch
`spike/g1-gepa` (worktree), merged back to `misc/rl-spike`. Code in
`gepa_g1/`. Companion evidence: BREAKAGE_LOG entries 22–24.*

## What was built and what happened

`gepa_g1/` reruns the spike's loop with the update rule swapped: the
artifact threading the iterations is the **cheatsheet/system prompt**
instead of a LoRA adapter. A `GEPAAdapter` (gepa==0.1.1, deliberately not
DSPy) implements `evaluate()` as the existing generate → sandbox-score
path — the in-sandbox verifier `score_pipeline.py` runs **byte-identical**
to the GRPO baseline — and `make_reflective_dataset()` renders the
scorer's reward JSON (breakdown, per-clause verdicts, error, run output
tail) as text for a reflection LM. Task model gpt-5-nano, reflection
model gpt-5.4, both hosted API; zero GPUs.

Headline run (12 tasks spread across difficulties, 150-call budget,
~25 min, well under $1 of API spend): starting from a **one-line seed**
("ZenML has @step and @pipeline"), GEPA evolved an 8-candidate tree and
lifted the mean sandbox reward **0.515 → 0.839 (+63%)**. The evolved
cheatsheet contains rules nobody wrote — "Never call `.run()`", "include
exactly one pipeline invocation under `__main__`", and a
`step_run_counts`-gaming strategy for conditional tasks ("run more than
one candidate branch step and choose the final answer later") — each
inferred by the reflection model from scorer feedback alone. The
optimizer's discoveries are *readable English*, including the
reward-hack-adjacent ones; GRPO's equivalent discoveries were weight
deltas.

**Why the seed is one line:** the first attempt used the real
`prompts.py` CHEATSHEET as the seed, and gpt-5-nano scored a perfect
1.0/1.0 on all 12 tasks immediately — no headroom, run aborted. That
null result is itself a data point (see the honesty note).

**Replication on staging (same day):** a second run against the Pro
server (project `rl-spike`, stack `rl-spike-local`: local orchestrator +
S3 artifact store + local sandbox) reproduced the shape with a stronger
outcome — **0.385 → 0.946 (+146%)**, 8 candidates, 159 metric calls,
31 min. Run `gepa_pipeline-2026_07_09-13_40_18` carries the full
artifact set on the dashboard, including a `gepa_evolution_html`
HTMLString artifact (score-progression chart, candidate tree, per-task
Pareto table, best cheatsheet). The seed baseline differing between runs
(0.515 vs 0.385, same seed prompt) is nano's sampling variance — worth
remembering when reading any single GEPA score as "the" number.

## The three questions

**(a) Loop-shape genericity — YES, with a visibility trade.** The
generate → sandbox-verify → update-artifact shape survived the swap
completely: scorer unchanged, sandbox transport helpers reused as-is,
task set reused as-is, and the never-raise error contract the spike
learned in Stage 1 (entry 16) turned out to be *gepa's documented adapter
contract verbatim* — two systems independently converging on the same
rule. What did NOT survive is step granularity. GRPO's update rule was a
math library call, so ZenML steps could own generate/score/update
separately and every episode was a visible mapped step. GEPA's update
rule *owns its own inner loop* (propose → minibatch-eval → accept/reject),
so the whole optimization collapses into one `evolve_prompt` step and
episodes become invisible to the DAG — the candidate tree comes back as
one artifact instead. Driving gepa's evaluate() back out through mapped
ZenML steps (Option B) would restore visibility at the cost of a
mid-run-growing DAG and the entry-12/15 fan-out problems; we chose not
to, and the choice generalizes: **when the external framework owns the
loop, ZenML's unit of visibility coarsens from episode to
optimization-run.** That is the same axis as the Track C/D ownership
spectrum, now demonstrated within a single task.

**(b) Population/Pareto lineage — ZenML cannot represent it natively;
carried inside artifacts instead.** GEPAResult is a tree: `parents[i]`
gives each candidate's lineage edge (here: 0→1→2→6 is the winning line,
while 3, 4, 5, 7 are dead-end branches off the seed), and "best" is
**per-task**, not global — the *seed* still owns `comfort_range` and
`head_tail_balance` on the final Pareto frontier (0.90/0.92 vs the
winner's 0.80/0.83), because evolution traded those away for gains
elsewhere. ZenML's artifact versioning is a linear chain per name
(v1→v2→v3): the adapter thread fit it naturally, a population does not.
We carried the tree *inside* two artifacts (the full `gepa_result` dict +
a rendered report/HTML view), which works but means the dashboard's
lineage view shows a single artifact node where the scientifically
meaningful object is an 8-node tree with per-task frontier membership.
**Escalation for core:** is there (or should there be) a first-class way
to represent branching candidate populations — parent links between
artifact versions, or run-model support for tree-structured experiments?
This is the concrete exhibit for that conversation.

**(c) Prompt-as-artifact with a second model in the loop — works,
minor frictions.** The evolved cheatsheet is a versioned string artifact
with full lineage into the run that produced it; the HTML report gives
the run a human-legible face on the dashboard. The second model
(reflection LM) enters cleanly through the adapter, with one wrinkle:
gepa's string-based `reflection_lm="model-name"` path requires litellm,
which isn't a dependency here, so the model is passed as a **callable** —
which turned out to be the better pattern anyway, because that callable
is the natural cost-attribution point. Both models' usage is metered
per-role (task LM: 159 calls / ~634k tokens; reflection LM: 10 calls /
~25k tokens) and logged as step metadata + report content. Secrets were
plain env vars (`OPENAI_API_KEY`); nothing needed ZenML secret
management for a laptop run, but a remote-orchestrator version would —
the same secret-plumbing question every hosted-API step has.

## Honesty note (for FINDINGS.md)

The G1-vs-GRPO comparison is tilted toward GEPA **by construction** (the
task was designed so the cheatsheet is the model's only knowledge channel
for a post-cutoff API) — and this run sharpened the point: with the full
cheatsheet, gpt-5-nano — the *smallest* current API model — already
scores 1.0, so on this task set prompts saturate before weights are ever
needed. The GRPO experiment only had headroom because its policy was a
0.6B local model. Report G1 as evidence for the intervention-spectrum
story (prompts first, weights when prompts saturate — RELAI's "smallest
durable change at the right layer"), not as a GEPA-beats-GRPO benchmark.
The right head-to-head framing is: same harness, same verifier, the
cheaper intervention exhausted the task set at ~1/50th the cost and zero
GPU.

## Cost/scale notes

- Local-flavor episode: ~6s (sandbox create ≈0, upload ≈0.1s, scorer
  exec ≈5.5s of which local-sqlite pipeline run ≈3s). 4-way thread pool
  per evaluate() batch; 159 episodes ≈ 25 min wall clock.
- gpt-5-nano is a reasoning model: ~520k completion tokens for 159
  generations (~3.3k/episode, mostly hidden reasoning). Still ≈ $0.21.
- gepa overran `max_metric_calls` 150 → 159 (checks budget between
  iterations, not evaluations — BREAKAGE_LOG entry 24). Budget with one
  full-valset eval of headroom.

## Escalations collected (for the Hamza/Michael conversation)

1. **Population lineage (question b)** — candidate trees vs linear
   artifact versioning; first-class parent links between artifact
   versions?
2. **`.zen` destructive reset** (entry 22) — repo context rewritten on
   any ID-resolution failure; multi-worktree/multi-config hazard.
3. **Local sandbox PATH resolution** (entry 23) — silent
   wrong-interpreter scoring; second instance of "failure states lie"
   (entry 16 theme).
