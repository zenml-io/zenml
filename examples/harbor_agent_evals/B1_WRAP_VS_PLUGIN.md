# Wrap vs. plug in — how ZenML should meet Harbor users (B1 question (d), for Hamza)

*2026-07-09, from the B1 spike thread (branch `spike/b1-harbor-k8s`). Sales
signal below comes from Alex's customer conversations; technical claims from
PR #5029 and the B1 K8s validation (`B1_K8S_FINDINGS.md`). Assessment only —
nothing was prototyped for this page, per the B1 brief.*

## The decision

Harbor campaigns can connect to ZenML in two shapes, and they are not
exclusive:

- **Wrap (what PR #5029 ships):** ZenML is the entrypoint. A user writes
  `python run.py`, ZenML expands the campaign into mapped shard steps, each
  step calls Harbor programmatically, and Harbor's trials execute in the
  stack's Sandbox component. ZenML owns retries, caching, artifacts, report.
- **Plugin (not built):** Harbor stays the entrypoint. A user who already
  lives in Harbor types `harbor run --env zenml --plugin zenml`. The `--env`
  half already effectively exists (the bridge is a regular Harbor environment
  provider, loadable today via `--environment-import-path`); the `--plugin`
  half would be a new thin package that, after each job, records the campaign
  into ZenML as a run with per-trial artifacts, rewards, and cost — the exact
  pattern LangChain shipped as `--plugin langsmith`.

The question for you: which shape gets distribution priority, and is the
plugin worth a named owner?

## What the spike established (technical side is settled)

The wrap shape is validated end-to-end on **two** sandbox flavors now: all of
#5029's Modal validation reproduced on the Kubernetes flavor (hermetic
head-to-head, caching/resume, metadata, log restore). The one portability
wall — task-pinned `docker_image` being Modal-only — turned out to be a
one-function fix: `KubernetesSandboxSettings.image` already exists, and a
spike-only patch booted real Terminal-Bench images on EKS with oracle reward
1.000. So neither shape is blocked on infrastructure; this is purely a
distribution and positioning decision.

## Sales signal (honest about sample size)

From Alex's calls — explicitly too few to be representative, weigh
accordingly:

- **The people asking about agent evals are agent teams new to ZenML**, not
  platform teams that already run ZenML. That is the single strongest
  argument for the plugin shape: these users already know `harbor run`; a
  plugin meets them without asking them to adopt a pipeline framework on day
  one. The wrap shape asks them to restructure their eval loop around ZenML
  before they've seen value.
- **What they ask for is a genuine mix** — run-the-benchmark, reports and
  regression gates, lineage into training — with no single dominant ask yet.
- **LangSmith is not the competitor in our deals.** Some customers have it,
  but most use **Langfuse, Braintrust, or Arize** for observability. Two
  consequences: (a) the "LangSmith already occupies the results slot" urgency
  is about *pattern precedent and slot occupation*, not head-to-head
  displacement in our pipeline; (b) a ZenML plugin should not be positioned
  as trace observability at all — our customers already own a trace tool.
  The plugin's job is the thing none of those tools do: **connecting eval
  results to artifact lineage that continues into training** (which
  trajectories became SFT data, which adapter version an eval gated, what
  the eval-to-training loop looked like six months later).
- **Maintenance appetite: fine if it's thin.** A results-recording plugin
  with a small API surface (post-job hook, read `JobResult`, write one ZenML
  run + artifacts) is judged maintainable despite Harbor's release pace
  (0.8 → 0.18.x in months; our integration canaries currently pin 0.8, and
  the version-bump path is already tracked work the plugin would ride).

## Assessment

**Ship both, in this order — they serve different funnels:**

1. **Wrap is done (PR #5029) and is the right shape for the customers we
   already have**: platform teams get campaigns with retries, caching, and
   reports inside the system they operate. Nothing more to decide.
2. **The plugin is the acquisition shape and the time-sensitive one.** The
   audience actually asking about evals doesn't run ZenML yet. A thin
   `--plugin zenml` gives them lineage receipts in a ZenML project after
   their normal `harbor run`, with zero adoption ask — and the natural
   upgrade path ("want retries/caching/regression gates? the same campaign
   runs as a pipeline") leads to the wrap shape we already ship. LangChain
   has demonstrated the slot works; the slot is still uncontested for
   *training-lineage* recording. Formalizing `--env zenml` (naming, packaging
   — the import path works today) should ride along.
3. **What makes it more than a LangSmith clone** (and than Langfuse/
   Braintrust — the comparison our customers would actually make): record
   not scores-and-traces but *artifact lineage into training* — trial
   identity (reuse #5029's sha256 join keys), task version pin, sandbox
   image, reward, and a trajectory artifact reference in the schema B3's
   exporter will consume. The plugin and B3 should share that schema; that's
   the moat, and it's cheap because #5029 already defined the identities.

**The residual decision is staffing, not architecture:** a named owner for a
thin package on Harbor's release cadence, and whether it waits for the
integration's Harbor version bump (probably yes — building a plugin against
0.8 while upstream is at 0.18 would be maintaining two pasts).

**Suggested trigger to commit:** the first conversation where an agent team
would try ZenML *if* it didn't require restructuring their Harbor loop —
Alex's calls suggest that conversation is already close.
