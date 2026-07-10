# RL spike → Kitaru: what the findings mean for the Kitaru roadmap (2026-07-10)

*Audience: the Kitaru team. This document is self-contained — you don't need
the spike's context or Alex in the room to act on it. Each section ends with
a suggested issue, and every claim links to the evidence that backs it.*

## Why this document exists

The Kitaru direction document (`docs/strategy/kitaru-direction.md` in the
kitaru repo, dated 2026-07-07) committed to a product direction — score
hook, replay isolation guard, Harbor export, Proxima PoC — and explicitly
listed the ZenML-side RL spike as one of the things that could change or
sharpen the answer ("§7: The toy RL spike surprises us"). The spike is now
done: a full GRPO training run on EKS plus seven follow-up experiments
(snapshots, data-layer measurement, verifiers, Harbor-on-K8s, trajectory
export, TRL-owns-the-loop, GEPA), producing 27 logged platform findings.
The synthesis lives in
[`FINDINGS.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/FINDINGS.md)
with
[`BREAKAGE_LOG.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/BREAKAGE_LOG.md)
as the entry-by-entry source of truth.

The headline back to the direction doc: **its open trigger fired.** The
spike's verdict is that ZenML's loop shape is right and nothing found is
architectural — the failures are defaults, caps, heartbeats, and honest
failure states. That is the "close to workable" condition the direction
doc set for the weights path earning a ZenML-side roadmap. None of that
changes Kitaru's direction; what it does is hand the Kitaru build items
concrete evidence, one design constraint, and two warnings. That's what
the rest of this document is.

The direction doc also predicted the spike's pain points ("data transport
and the one-pipeline-vs-two question") — both predictions landed, both
were measured, and both verdicts support the direction doc's Fork 4
stance: one pipeline held at full scale
([`TRAINING_RUN.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/TRAINING_RUN.md)),
and data transport got a split verdict — episode records need nothing,
model weights want a shared volume, and the dominant cost is neither
([`DATA_LAYER.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/DATA_LAYER.md)).

---

## 1. The score hook needs an explicit "scorer crashed" state, from v1

**What Kitaru plans:** `def score(execution) -> float`, stored per
execution, surfaced in `diff_matrix` and the compare view. The direction
doc's scope discipline is "a float, full stop."

**What the spike found:** a float alone is a trap, and we have four
independent datapoints. When user-written scoring code crashes, every
system we touched silently converts the crash into a score of 0.0 —
indistinguishable from "the agent genuinely did badly":

1. Our own scorer: a degraded node made `import zenml` fail inside the
   scoring environment for 2.5 hours; the system recorded honest-looking
   0.0s across two full training iterations, and diagnosing it took hours
   of archaeology
   ([BREAKAGE_LOG entry 16](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/BREAKAGE_LOG.md)).
2. verifiers (Prime Intellect's RL/eval library) swallows any exception a
   reward function raises and scores the rollout 0.0 — the same bug,
   rebuilt independently by another team
   ([FINDINGS Theme 5, C2 finding 3](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/FINDINGS.md)).
3. Harbor's campaign layer: a campaign in which *every* trial errored
   reports "0 shards below reward 1.0" — reads as a perfect score
   ([entry 21](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/BREAKAGE_LOG.md), found in
   [`B1_K8S_FINDINGS.md`](https://github.com/zenml-io/zenml/blob/spike/b1-harbor-k8s/examples/harbor_agent_evals/B1_K8S_FINDINGS.md)).
4. The strongest one: **our own team, knowing the trap and having built
   the guard, still fell in.** One parsing call sat a single line above
   the `try:` block; a live message shape the tests never exercised made
   it throw; ten plausible-looking completions "scored" 0.0 with nothing
   flagged ([C1 finding 3](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/verifiers_c2/C1_EVAL.md)).

The lesson is structural: in any system where users write scoring
functions, *any uncaught line in that function becomes "the agent
failed"*, and teams that know about the trap still fall into it. Only
framework-level support closes it.

**What to adopt:** the stored score result should be a float **plus** an
explicit scorer-error state (crashed / infra failure vs. genuine score),
with the scorer's stderr/traceback kept, and the error state rendered
distinctly in `diff_matrix`, the CLI, and the compare view (an errored
row must not average into the cohort score). This is not LLM-judge scope
creep — it's the difference between an eval column someone can trust and
entry 16 with a nicer UI.

**Suggested issue:** *"Score hook: distinguish 'scored 0.0' from 'scorer
crashed' in the stored result and every surface that renders it."*

---

## 2. `kitaru optimize` (GEPA-style prompt evolution) is de-risked — and its design blocker is known

**What Kitaru plans:** item 7 of the direction doc — a native "evolve
this prompt against your last 100 production runs" loop, treated as an
exploratory spike after score + isolation, justified with secondhand
numbers from the GEPA paper.

**What the spike found:** we ran the loop firsthand (task G1). Same
tasks, same sandbox scorer as the GRPO baseline, GEPA as the update rule:
**one-line seed prompt → +63% mean reward (0.515 → 0.839), zero GPUs,
under $1 of hosted-API spend**
([`GEPA_G1.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/GEPA_G1.md)).
Better: with the full hand-written cheatsheet, even a small model
saturates the task set at 1.0 — **prompts exhausted this task before
weights were needed**, which is the "cheapest durable intervention
first" pitch, demonstrated rather than cited. The loop consumes exactly
what Kitaru already produces: real production examples (cohorts), cheap
counterfactual execution (replay with prompt overrides), a fitness
signal (the score hook), and error traces to feed the next mutation.

**The design blocker found alongside:** GEPA does not produce a version
thread (prompt v1 → v2 → v3). It maintains a **Pareto frontier — a
candidate tree** where the "best" candidate is per-task, not global, and
parents spawn multiple children. Linear artifact/version lineage cannot
represent that population; the spike had to stuff the whole tree inside
a single dict artifact to keep it at all (escalated as a core
artifact-model question — entries 22–24 in the
[BREAKAGE_LOG](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/BREAKAGE_LOG.md)).
Kitaru's compare view and lineage model will hit the identical wall the
day `kitaru optimize` exists: the object to display is a tree of scored
candidates, not a sequence.

**What to adopt:** move item 7 up in confidence (the loop is real,
cheap, and trainer-free), and budget the population-lineage
representation *before* building it, not after. One honesty note
transfers to customer conversations: the spike's task was designed so
the prompt is the model's only knowledge channel, which tilts any
"prompts beat weights" comparison — pitch it as "cheapest layer first,"
not "GEPA wins."

**Suggested issues:** *"Spike: `kitaru optimize` — GEPA-style prompt
evolution over a cohort, using replay + score hook"* and *"Design:
representing a scored candidate tree (population lineage) in the compare
view."*

---

## 3. The replay isolation guard has a stronger v2: the sandbox is a library

**What Kitaru plans:** declared-effect checkpoints blocked/stubbed under
replay, plus loud warnings on bare flow-body network calls. Right scope
for v1 — nothing here argues against shipping that.

**What the spike found:** ZenML's Sandbox is separable from ZenML's
orchestration. Three experiments used a ZenML Sandbox session as a plain
library call from inside *someone else's* process — no pipeline, no
step, no ZenML run anywhere in sight: a verifiers reward function opened
sessions per completion
([C2](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/verifiers_c2/README.md)),
TRL's trainer ran multi-turn agent tool calls in them mid-rollout
([`B2B_FINDINGS.md`](https://github.com/zenml-io/zenml/blob/spike/b2b-trl-harbor/examples/rl_spike_b2b/B2B_FINDINGS.md)),
and the bridge that makes it work vendors into ~300 lines against
released zenml from PyPI (B2b finding 2).

**Why Kitaru should care:** the strong version of replay isolation is
not "warn when flow-body code opens a socket" — it's "re-execute the
overridden checkpoint *inside a sandbox session*, where it physically
cannot send the Slack message." That was infeasible when the direction
doc was written; the library finding makes it a candidate v2. It is also
the answer to the direction doc's own best customer quote for this
feature — Adeo's "an agent with 40 tools that would all need mocking,
this becomes very complex": don't mock 40 tools, run the replay
somewhere the tools' side effects can't escape.

**Suggested issue:** *"Isolation guard v2 exploration: sandbox-backed
checkpoint re-execution for replay (ZenML Sandbox as a library)."*

---

## 4. Failure forensics: Kitaru replay and sandbox snapshots are the same product instinct — one story, two layers

**What Kitaru plans:** production-trace-grounded replay as the wedge —
"reopen the past and experiment on it."

**What the spike found:** the sandbox layer now does the same thing one
level down. Failing episodes snapshot their sandbox filesystem before
teardown, and a one-command restore reopens the failed environment to
look around — the demo compressed a multi-hour diagnosis (entry 16) into
`restore` + `cat pipeline.py` + `import zenml`
([`SNAPSHOTS.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/SNAPSHOTS.md)).
Measured cost: ~1.3 s per failing episode, so snapshot-on-failure is
cheap. And the ecosystem scan says nobody else has this: verifiers' own
docs concede that anything a reward needs from a sandbox must be grabbed
before the sandbox is destroyed, and their exception-swallowing (item 1
above) makes the missing forensics *worse* for them
([FINDINGS Theme 5, finding 3](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/FINDINGS.md)).

**What to adopt:** when the Kitaru story reaches "why us" against
observability tools, replay-of-the-trace and restore-of-the-environment
are one differentiated claim: *the trace tells you what the agent did;
the snapshot gives you back the world it did it in.* Concretely, a
Kitaru trace of an agent run whose commands executed in a sandbox could
carry the snapshot ref and expose restore, the way the spike's episode
records do. Two known dependencies to state in any issue: the core
snapshot API is currently implemented **only by the Modal sandbox
flavor** (Kubernetes/local raise `NotImplementedError` — the flavor gap
is entry 17 and an open escalation), and snapshot refs currently ride in
user-code outputs because the platform has no native place for them
(SNAPSHOTS.md gap list).

**Suggested issue:** *"Trace ↔ snapshot linkage: carry sandbox snapshot
refs on Kitaru traces and expose restore (depends on ZenML flavor
coverage, entry 17)."*

---

## 5. If the Harbor export ships, adopt B3's identity and provenance lessons

**What Kitaru plans:** `kitaru executions export --format harbor` — a
recorded production run becomes a Harbor task directory (item 4 of the
direction doc).

**What the spike found:** we built and ran the *reverse* edge — Harbor
eval trials exported into an accumulating training-data artifact
([`B3_EXPORTER.md`](https://github.com/zenml-io/zenml/blob/spike/b3-exporter/examples/harbor_agent_evals/B3_EXPORTER.md))
— and the failures were all about identity and provenance, which apply
verbatim to Kitaru's export direction:

- **Join keys fragment if they hash anything but canonical coordinates.**
  Harbor-integration trial identities differ for byte-identical tasks
  depending on *how the task was referenced* (dataset resolver stamps a
  `source:` field; local paths hash machine-specific). Any "the same
  exported task, re-run later, joins with its history" story — including
  the regression-suite accumulation both roadmaps want — dies on this.
  Hash the canonical pin (URL + commit + subpath) and nothing else.
- **Record the execution environment at execution time, or the record
  lies.** Nothing in the Harbor stack records which sandbox image a
  trial actually ran in; the best-effort fallback (read the stack
  config) gave *provably wrong* answers for image-pinned tasks. The one
  sentence the whole export story wants to say — "this score came from
  this task in this environment, here's the resulting example" — is
  exactly the sentence nothing currently supports. Whoever resolves the
  environment must write it into the record then and there.

**Suggested issue:** *"Harbor export: task identity = canonical pin
coordinates only; record resolved execution environment in the exported
task/result."* (Cross-reference: the same fixes are filed as asks
against the ZenML Harbor integration in FINDINGS Theme 5 / B3.)

---

## 6. Batch replay at customer scale has ZenML-core prerequisites — name them now

**What Kitaru plans:** cohort of 200 production runs → override-replay →
score/diff. The direction doc honestly notes today's batch replay is a
sequential client-side loop and says real parallelism belongs to the
orchestrator. The Proxima PoC adds days-long durable jobs at
millions-of-runs scale.

**What the spike found:** the orchestrated version of "many small
re-executions" is exactly what the spike ran 1,400 of, and the two
strongest findings themes are what it hit
([FINDINGS Themes 1–2](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/FINDINGS.md)):

- **Fan-out has no working concurrency or placement story.** The
  documented parallelism knob is silently ignored by dynamic pipelines;
  ten concurrent pod startups rate-limited the platform's own credential
  endpoint into killing its own fan-out; the orchestrator pod ships with
  no memory request and got OOM-killed by its own children; the retry
  path can die and leave steps in `retrying` forever with no timeout
  (entries 11/12/14/15).
- **Small work units drown in per-step fixed cost.** Measured across
  1,398 steps: 31.6 s of useful work inside a 117 s step — **73% of
  wall-clock is getting a step running at all**
  ([`DATA_LAYER.md`](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/DATA_LAYER.md)).
  A single-checkpoint replay is precisely this kind of small unit.
- **Failure states lie.** Every long-running failure mode we hit ended
  in a state that misreported itself — runs stuck `running`/
  `provisioning` forever, a green run shipping garbage. For a design
  partner whose jobs run for days, a silently wedged "durable wait" is a
  churn event.

**What to adopt:** nothing to build in Kitaru — this is a
prioritization argument to make explicitly. The core asks already filed
from the spike (concurrency caps that work on dynamic pipelines, a
run-level heartbeat/reaper, a terminal escape from `retrying`, sane
orchestrator defaults, cheaper per-step floor) are prerequisites for
*Kitaru's batch replay product and the Proxima engagement*, not just for
RL. Two products and the revenue beachhead want the same fixes; the
issues should carry those names so they're weighed accordingly. This
also corrects one line in the direction doc: "no ZenML core changes
required" is true of the SDK items, but the product's ceiling is
core-side.

**Suggested issue (zenml repo, tracking):** *"Batch replay / Proxima
prerequisites: adopt the RL-spike Theme 1–2 asks with product owners
attached."*

---

## 7. Three time-sensitive ecosystem openings (agenda material, not builds)

The direction doc positions Kitaru/ZenML as the production on-ramp that
feeds the eval/RL ecosystem rather than competing with it, and mentions
the scheduled Harbor call and the Prime Intellect follow-up. The spike
supplies three concrete openings, all of the same shape — **the contract
is still soft; one small upstream change puts ZenML Sandbox in the
slot** — and all get harder as the enum lists ossify:

1. **verifiers:** its sandbox lifecycle hardcodes Prime Intellect's paid
   sandbox client, but the contract underneath is five duck-typed async
   methods that ZenML's session API already satisfies. One import is the
   whole gap
   ([C2 finding 2](https://github.com/zenml-io/zenml/blob/misc/rl-spike/examples/rl_spike/verifiers_c2/README.md)).
2. **TRL:** its Harbor adapter hardcodes Harbor's vendor enum (20+
   backends), but Harbor's own config prefers an `import_path` the
   adapter never exposes. A one-parameter upstream PR would put ZenML
   Sandbox inside the highest-traffic RL library's native agentic path —
   we ran the full nesting live on EKS with a ~25-line override to prove
   it works
   ([`B2B_FINDINGS.md`](https://github.com/zenml-io/zenml/blob/spike/b2b-trl-harbor/examples/rl_spike_b2b/B2B_FINDINGS.md),
   finding 1).
3. **Harbor wrap-vs-plugin:** the product assessment the direction doc
   asked for is written, with a recommendation (wrap for existing
   platform customers, thin `--plugin zenml` as the acquisition shape) —
   [`B1_WRAP_VS_PLUGIN.md`](https://github.com/zenml-io/zenml/blob/spike/b1-harbor-k8s/examples/harbor_agent_evals/B1_WRAP_VS_PLUGIN.md).

**Suggested issue:** one umbrella *"Ecosystem substrate slots: decide
and staff the verifiers / TRL / Harbor-plugin upstream moves"* — it's
one staffing conversation, not three engineering projects.

---

## What this document deliberately does not do

It does not reopen the direction doc's forks. The spike's evidence
*strengthens* the recommendation already made there: Option B stays
rejected (we measured what remains when a framework swallows the loop —
config in, adapter + one metrics dict out; B2b finding 3), the trainer
stays documented-not-owned (the Ray-based frameworks were skipped
precisely because their findings would be about Ray), and Fork 4's
single-pipeline stance survived a full training run. The items above are
additive to the committed direction: one correctness requirement
(item 1), one confidence upgrade with a known design constraint
(item 2), two feature upgrades unlocked by new evidence (items 3–4), one
set of spec requirements for an already-planned feature (item 5), one
prioritization argument (item 6), and one staffing conversation
(item 7).
