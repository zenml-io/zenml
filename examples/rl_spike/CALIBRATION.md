# Calibration run results (2026-07-09)

One measurement pass over all 64 tasks before the full training run:
group size 4, one iteration, learning rate 1e-12 (no meaningful update),
offline serving, Qwen3-4B-Instruct-2507, temperature 0.9. Run as four
sequential chunks of 16 tasks (the mapped fan-out has no working
concurrency cap — BREAKAGE_LOG entry 12 — so one 256-episode run would
have hammered the staging server). Runs:
`f411036a`, `9d51a334`, `93f4246b`, `6a6e0480` (project `rl-spike`).

Chunk 1 first attempt also produced BREAKAGE_LOG entry 14: the
orchestrator pod (BestEffort QoS by default) was OOM-killed by its own
episode fan-out; fixed with explicit memory requests in
`k8s_settings.py`, after which all four chunks ran green (episode
retries visible and working: a handful of 429-killed pods came back).

## Headline numbers

| Chunk | Tasks | Mean reward | Scored failures /64 | Groups with variance /16 |
|---|---|---|---|---|
| 1 | D1 + easy D2 | 0.950 | 4 | 0 |
| 2 | D2 + D3 | 0.747 | 24 | 3 |
| 3 | D3 + D4 | 0.718 | 22 | 6 |
| 4 | D4 + OOD | 0.665 | 30 | 4 |

## Per-task buckets (group of 4 samples per task)

**Variance NOW (13 tasks — GRPO's food, keep all):**
mostly conditionals and loops where some samples remember `.load()`
and some don't: `abs_route` (0.33–1.0), `bigger_of_two`,
`grade_letter`, `parity_branch`, `vowel_any_flag`,
`string_grow_until`, `alternating_sum_loop`, `fib_loop`,
`word_ladder`, `loop_sum_to_five`, `find_first_big`,
`triangular_until`, `double_until`.

**Flat-imperfect (14 tasks — all 4 samples fail the same way; keep):**
`mean_of_list`, `longest_word_flag`, `even_count_branch`,
`threshold_flag`, `comfort_range`, `crossed_reports`,
`two_stage_map`, `head_tail_balance`, `sum_vs_product`,
`halve_then_flag`, `gruntle_until`, `range_then_flag`, `zorp_fold`,
`halve_until`. Inspected failures are NOT spec bugs — they are one
systematic model error: using an artifact handle directly in Python
(`len(numbers)`, `num % 2`) instead of `.load()`. Notably
`crossed_reports`: the model handled the deliberately-crossed naming
*correctly* and crashed only on the missing `.load()`. At group size 8
these tasks should split into variance (their cousins already do).

**Saturated all-1.0 (37 tasks — no learning signal at 4B):**
all D1/D2 plus every plain `.map()` task and, humblingly, most of the
out-of-distribution family (`blorbify`, `florp`, `fake_triple`,
`mixed_signs`, `qthird_replace`, `wug_map_count` — the 4B follows
novel/misleading instructions fine when no `.load()` is involved).

## What this says about the training run

1. **The learnable skill is crisp:** `.load()` for control flow. The
   model composes steps, maps, and even anti-prior instructions
   reliably; it fails predictably at the one API concept that has no
   analogue in its training data. That is an ideal RL target.
2. **Task mix for the full run:** keep the 27 variance/flat-imperfect
   tasks as the core; keep ~10 saturated tasks as regression guards;
   drop or demote the other ~27 saturated ones from the training mix
   (they cost GPU time and contribute zero advantage).
3. **Group size 8 + temperature ≥1.0** to convert flat-imperfect
   groups into split groups.
4. **Smaller-model option (Alex's suggestion, kept in the idea bank):**
   Qwen3-1.7B would likely de-saturate the map/chain tasks too, at the
   risk of flooring the D4 loops. Given the 4B already has a clean
   20–80% frontier on the tasks that matter, the harder-mix route
   needs no new engineering; the smaller model is the fallback if the
   4B trains through the `.load()` frontier too quickly.
