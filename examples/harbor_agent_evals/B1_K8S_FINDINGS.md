# B1 — Harbor campaigns on the Kubernetes sandbox flavor (2026-07-09)

Spike findings for Track B / B1 (`framework_breakout.md`). Branch
`spike/b1-harbor-k8s` off `feature/add-harbor-integration` (PR #5029, open at
the time). Everything below ran against the staging EKS cluster
(`eu-staging-cloud-infra-cluster`) via the existing `kubernetes_aws` sandbox
component (namespace `michael`, image `python:3.11-slim`), local orchestrator,
stack `rl-spike-harbor-k8s`, project `rl-spike`. Harbor 0.8.0, Python 3.14
venv. Fan-out kept deliberately small (≤4 pods at any point) — shared cluster.

## Verdict: the hermetic path passes on Kubernetes

Everything PR #5029 validated on Modal that does *not* involve
`docker_image` reproduces on the K8s flavor unchanged:

- **Single-trial smoke** (`tasks/hello`, oracle): reward 1.000, shard step
  15.4s including pod startup, whole run 26s.
- **Oracle-vs-nop head-to-head** (6 trials, 4 shards): oracle 1.000 /
  nop 0.000, 6/6 completed, 0 errored, 29.7s wall clock. Report, `harbor.*`
  step metadata, and the `download_jobs_dir()` log restore all worked.
- **Caching**: identical rerun cache-hit all 6 steps, 8.3s, zero pods
  created — the E4 caching answer holds on the K8s path.
- Pod churn was a non-issue at this scale: 4 concurrent session pods created
  and torn down cleanly; asyncio-in-step behavior identical to Modal.

## The `docker_image` wall — hit by design, sharper than expected

`dataset:terminal-bench-sample@2.0:3` (oracle, 1 trial/task): **all three
tasks errored** with the bridge's intended loud failure:

```
NotImplementedError: Task-level docker_image is currently only supported
with the Modal sandbox flavor (active flavor: 'kubernetes').
```

All Terminal-Bench 2.0 tasks pin a prebuilt `docker_image`, so **the full
89-task fan-out (B1 stage 3) is moot on K8s until translation lands** — it
would be 89 deterministic errors. Skipped deliberately.

**The sharp part:** the translation target already exists.
`KubernetesSandboxSettings.image`
(`src/zenml/integrations/kubernetes/flavors/kubernetes_sandbox_flavor.py:37`)
is a per-settings image knob on the K8s flavor. The wall lives entirely in
the bridge: `ZenMLSandboxEnvironment._settings_override`
(`src/zenml/integrations/harbor/environment.py:74-106`) hardcodes Modal as
"the only sandbox flavor with an image knob today" — and its own docstring
says to switch to the active flavor's settings class when another flavor
ships an image field. That field has shipped.

**Escalation question for core (per B1 stop condition):** should
`_settings_override` translate `task.docker_image` →
`KubernetesSandboxSettings(image=...)` for the kubernetes flavor? Open
sub-questions before saying yes: image pull policy / private-registry
credentials on the cluster (Modal pulls from public registries transparently;
EKS nodes need pull access), architecture mismatches (arm64 vs amd64 nodes),
and whether a flavor-dispatch table in the bridge is acceptable vs. a
`supports_image_override` capability on `BaseSandbox`.

## Secondary finding 1 — failed `start()` leaves noisy, misleading wreckage

When `start()` raises (here: the `NotImplementedError`), Harbor's trial
cleanup still calls `download_dir_with_exclusions` → `env.exec()` on the
never-started environment, producing a *second* exception
(`RuntimeError: ZenMLSandboxEnvironment used before start()`) plus repeated
"Failed to download logs to ..." lines per trial. The real cause is only
visible above the secondary traceback. The bridge could make its
unstarted-state error name the original failure, or no-op the log-download
path when no session was ever created. Small UX bug, but exactly the kind of
archaeology tax BREAKAGE_LOG entry 16 was about.

## Secondary finding 2 — errored trials are invisible to the receipt queries

Report semantics for the errored campaign: each trial shows **Completed=1
AND Errored=1**, mean reward `n/a`, and the run.py receipt query
(`harbor.mean_reward < 1`) reports **"Shards with mean reward < 1: 0"** —
three fully-errored shards don't register, because errored shards log no
`harbor.mean_reward` metadata at all and "completed" apparently means "the
shard step finished", not "the trial succeeded". A user gating on the
mean-reward query would ship a campaign where every trial errored. The
queryable surface needs either an `harbor.n_errored`-first idiom in the
example receipts (the metadata exists — `harbor.n_errored:gt:0` works) or
errored shards logging a sentinel reward. Worth an entry in the eventual
core follow-up alongside the `docker_image` translation.

## Environment / version notes

- Harbor 0.8.0 installed and ran fine on **Python 3.14** (integration canaries
  target 0.8; upstream Harbor is at 0.16-0.18.x — version-bump path is
  tracked work, out of B1 scope).
- `zenml integration install harbor --uv` does not pull the `kubernetes`
  client; using the K8s sandbox flavor additionally requires
  `zenml integration install kubernetes`. Expected, but worth one line in the
  example README's prerequisites (currently Modal-only instructions).
- The `exec(user=...)` ignored warning (documented limitation) fired on every
  trial — cosmetic at this scale, noisy at 89 tasks.

## Experiment: the translation works (spike-only patch, verified live)

To upgrade the escalation from "the field exists" to evidence, the spike
branch patches `_settings_override` with a kubernetes case (marked
do-not-ship in the code):

```python
if sandbox.flavor == "kubernetes":
    from zenml.integrations.kubernetes.flavors import KubernetesSandboxSettings
    return KubernetesSandboxSettings(image=image)
```

Result — `dataset:terminal-bench-sample@2.0:3 oracle 2` on the K8s flavor:
**all three tasks (chess-best-move, polyglot-c-py, sqlite-with-gcov), 6/6
trials completed, 0 errored, reward 1.000** — the same table PR #5029
produced on Modal. Single-task run: 47s wall clock including pulling the
Terminal-Bench image onto the node; full 3-task run 1m19s. EKS pulled the
public benchmark images without any registry configuration.

So the answer to the escalation question is *yes with caveats*:
`KubernetesSandboxSettings.image` is a working translation target today for
public images. What a real fix still has to decide: private-registry
credentials (works here only because Terminal-Bench images are public),
arch mismatches (amd64 images on mixed node groups), node disk pressure from
large benchmark images at 89-task fan-out (BREAKAGE_LOG 16's failure mode),
and whether the bridge grows a per-flavor dispatch or `BaseSandbox` grows a
capability flag. The five-line patch is on this branch as the reference
implementation.

## Still open in B1

- Question (d) — wrap vs plug in: see `B1_WRAP_VS_PLUGIN.md` (assessment for
  Hamza, informed by Alex's sales-call answers).
