# RL spike — framework survey brief (planning, 2026-07-08, rev. 11)

*Purpose: a menu of framework combinations and example variants to try next, so the spike keeps producing findings after v0. Nothing here is implementation — each entry is a spec for an example someone could build later. The deliverable of every entry is a BREAKAGE_LOG-style finding, not a working model.*

*Rev. 11 (2026-07-09, evening): **B1 is done** (branch `spike/b1-harbor-k8s` off PR #5029, pushed, merges nowhere — the docs are the deliverable: [`B1_K8S_FINDINGS.md`](https://github.com/zenml-io/zenml/blob/spike/b1-harbor-k8s/examples/harbor_agent_evals/B1_K8S_FINDINGS.md) + [`B1_WRAP_VS_PLUGIN.md`](https://github.com/zenml-io/zenml/blob/spike/b1-harbor-k8s/examples/harbor_agent_evals/B1_WRAP_VS_PLUGIN.md); FINDINGS.md Theme 5 extended; BREAKAGE_LOG entries 19–21). K8s-flavor verdict: the hermetic campaign passes untouched; the `docker_image` wall hit by design on all terminal-bench tasks and was then proven hollow — `KubernetesSandboxSettings.image` already exists, and a five-line spike patch booted the real Terminal-Bench images on EKS at oracle 1.000. The 89-task scale test is moot until that translation ships (every TB task pins an image). Question (d) answered with a recommendation: wrap (shipped in #5029) for existing platform customers, thin `--plugin zenml` as the acquisition shape for the agent teams actually asking — staffing decision escalated to Hamza. B2b's environment track is unblocked. G1 still in progress in its worktree.*

*Rev. 10 (2026-07-09, evening): **C2 is done** (`verifiers_c2/README.md`; FINDINGS.md gains Theme 5) — the sandbox-reward collision resolves to composes-and-parallelizes (18/18 reward parity on canned completions, concurrent sessions), the C2 environment now exists for C1/C3/D1 to reuse, and the native-sandbox question is answered: verifiers hardcodes `prime-sandboxes` behind a five-method duck-typed contract ZenML's session API satisfies — the pluggability escalation is with Hamza. G1/B1 still in progress in their worktrees.*

*Rev. 9 (2026-07-09, later the same day): **F1 is done** (`SNAPSHOTS.md` — snapshot-on-failure + `restore_sandbox.py`; support matrix is Modal-only, entries 17–18; the flavor gap is the escalation) and **E3 is done** (`DATA_LAYER.md` — episodes 3% of bytes, weights 89%, 73% of episode wall-clock is harness overhead; volume-layer verdict: weights yes, episodes no). Findings count is now 18; `FINDINGS.md` updated with both. C2/G1/B1 in progress in separate worktrees.*

*Rev. 8 (2026-07-09, after the Stage 3 smokes, calibration, and the full training run — see `TRAINING_RUN.md`, `CALIBRATION.md`, `FINDINGS.md`): **A1 is done** (warm vLLM verified end-to-end: 5 iterations, 4 adapter hot-reloads; its gates are open); **E1 and E4 are answered without being scheduled** — the training run's own failures supplied them (vLLM Deployment leaks on failure, confirmed twice; retries can die and leave steps in `retrying` forever, deadlocking the run — BREAKAGE_LOG 15/16); **E3 needs no new run** (5×280 episode artifacts sit on the staging server, measurement is a laptop script); findings count is now 16 entries, synthesized in `FINDINGS.md`. Sequencing in §4 updated accordingly.*

*Rev. 2: B2b rewritten around TRL v1's shipped `trl.experimental.harbor` / `environment_factory` path (verified against TRL's docs — it resolves the token/logprob wall the first draft predicted, and it raises a new ZenML-Sandbox-as-substrate question); Harbor 0.18.x / Python ≥3.12 compat risk; B3 trajectory exporter; verl (D3) and SGLang (E5) as named deferrals; scorecard + pick-four framing in §4.*

*Rev. 3 (after the 7/8 Alex↔Hamza call): new Track F — sandbox filesystem snapshots as inspectable experiment state; E3 gains its named consumer (the mounted-volume data layer as escalation path); D1's question re-sharpened around "don't out-Ray Ray — find the seam"; §4 gains a post-call priority note and an Alex/Michael division-of-labour day shape.*

*Rev. 4: the single-turn-vs-agentic decision resolved and documented (§1 note): baseline stays single-turn as the control; the agentic task variant (write → run → read traceback → fix, ≤3 turns) lives in B2b where TRL owns the multi-turn token plumbing; F1's demo pointed at agentic trials; Kitaru-as-policy-agent ruled out via the installed-agent pattern, Kitaru-as-observability-wrapper stays parked per PLAN.md §5.*

*Rev. 7 (rebased on PR #5029, `zenml.integrations.harbor`, merging soon): B1 shrunk to what the integration doesn't answer (K8s-flavor pass, scale test, wrap-vs-plugin); B2a becomes composition of the integration steps; B3 upgraded from proposal to "#5029's named follow-up — build what the Agent evals guide promises", reusing the sha256 trial-identity join keys; Harbor version-split risk documented (integration canaries 0.8, TRL path pulls current); worktree-migration risks resolved; #5030 flagged for the BREAKAGE_LOG.*

*Rev. 6 (after Harbor positioning research): Track B gains a positioning context block — Harbor as the task-contract + substrate layer with evals and RL as two consumers differing in who drives generation; the LangChain three-slot integration (agent / sandbox provider / results plugin) documented as the template ZenML can mirror (`--env zenml` + `--plugin zenml`); B1 gains question (d) (wrap vs plug in) and a product-decision escalation; competitive urgency note added (LangSmith plugin already ships reward+trace lineage).*

*Rev. 5 (after the RELAI VCL case study): new Track G — GEPA prompt evolution on the existing harness, as the "cheaper intervention layer" entry (RELAI's memory → harness → weights spectrum); findings-doc closing question widened from "ZenML for RL" to "ZenML as the harness for the agent-improvement spectrum"; regression-traps benchmark idea noted for B3/Kitaru evals.*

*Reading order for someone cold: §1 says what we already have, §2 is the menu, §3 maps the menu back to the open questions, §4 is sequencing.*

---

## 1 · Where we are (what the existing assets already prove)

The current spike (`examples/rl_spike`) proves one complete shape end-to-end: **ZenML owns the whole RL loop as visible steps, TRL is demoted to a math library**. Concretely: ZenML steps generate rollouts (vLLM), score them in sandboxes, and hand pre-scored episodes to TRL's `rollout_func` so `GRPOTrainer` only computes advantages/loss/gradient. As of 7/9 this shape has run at full scale — a calibration pass over 64 tasks and a 5-iteration training run at 280 mapped episodes per iteration on the staging EKS cluster (`TRAINING_RUN.md`) — and has yielded 18 logged findings, synthesized by theme in `FINDINGS.md` (fan-out has no working concurrency/placement/retry story; failure states lie; the serving gap, now with warm-vs-cold numbers; plus the earlier caching/logging/image sharp edges — see `BREAKAGE_LOG.md`).

The Harbor worktree examples prove a second shape: **ZenML owns campaign fan-out, an external framework owns one trial**. `sandbox_harbor`'s `build_matrix → run_harbor_trial.map → build_report` runs one Harbor trial per mapped step, with Harbor's agent/verifier/reward running against a ZenML Sandbox session via the `ZenMLSandboxEnvironment` bridge. Smoke-tested on Modal only.

What the survey should now find out is the shapes in between and beyond:

| Shape | Status |
|---|---|
| ZenML owns everything, framework = library (TRL `rollout_func`) | **Built AND run at scale (calibration + 5-iteration training run, warm serving), findings flowing** |
| ZenML owns fan-out, framework owns one trial (Harbor campaign) | **Built (worktree), Modal-only, eval not RL** |
| ZenML owns the outer loop, framework owns rollout+train internals (verifiers `RLTrainer`, prime-rl) | Not tried |
| Framework swallows the whole loop, ZenML = config-in/checkpoint-out wrapper (prime-rl full stack) | Not tried — PLAN.md *predicted* this is pointless; nobody has verified the prediction |
| Two ZenML pipelines with trigger/poll (rollout pipeline ↔ training pipeline) | Not tried (PLAN.md v2) |
| Overlapped rollout/training inside one pipeline (`.submit()` futures) | Not tried (PLAN.md v1) |

One asset decision that recurs below: the existing **task set + in-sandbox scorer** (`tasks/tasks.jsonl` + `score_pipeline.py`) is reusable as-is by any candidate that lets us supply our own reward path, and is the *thing that breaks* candidates that insist rewards run inside the trainer process. That breakage is a finding, not a failure of the survey.

**On "should the task become agentic?" (raised on the 7/8 call — "if we don't have an agent, we don't have a filesystem"):** the baseline stays single-turn, and agenticness enters through the survey instead. Reasoning, briefly: (a) single-turn was locked precisely to sidestep TRL's multi-turn importance-sampling problem, and the `rollout_func` architecture re-inherits that trap the moment episodes go multi-turn — agentifying the baseline both reopens it and destroys the control group. (b) TRL's `environment_factory` path (B2b) *is* multi-turn agentic RL with the token/logprob plumbing solved upstream: the trainer drives every turn, so it always holds the policy's tokens. The agentic task therefore lives there — see B2b's task-variant note. (c) A **Kitaru agent as the policy harness is specifically the pattern that cannot train**: an agent running its own inference loop in the sandbox is TRL's "installed agent" — it emits a trajectory after the fact with no policy tokens or logprobs, so there is nothing to compute a gradient from, and TRL explicitly doesn't support it for RL. Kitaru's spike-adjacent role remains what PLAN.md §5 parked: an *observability* wrapper on episodes (traces, cost, replay), which never touches the token path. B2b and F1 are the experiments that tell the Kitaru `score=`/replay work what it needs.

---

## 2 · The menu

Each entry states: (1) framework combo + pins to investigate, (2) smallest runnable shape, (3) ZenML vs framework ownership, (4) the exact ZenML question it tests, (5) stop condition — what result makes it keep / abandon / escalate.

Ordering inside each track is by dependency, not preference. Priority across tracks is in §4.

---

### Track A — Deepen the existing TRL + vLLM baseline

These extend the current loop. They're the cheapest new findings because everything is already wired.

#### A1 · Verify warm-vLLM mode end-to-end — **DONE (7/8 smoke, 7/9 full run)**

**Status: complete; kept for the record.** Warm mode ran a full 5-iteration
training run: 4 adapter hot-reloads into the live server, ~1 min each;
iteration wall clock 209.6s vs 555–727s offline at smoke scale (the
serving-gap number, entry 2). Answers to the questions below: the exec+tar
transport works but had to be **inverted** (push from the step, which holds
materialized artifacts with connector credentials, into the pod — the pod
pulling from S3 is impossible outside step bootstrap, entry 13); HTTP
logprobs align with token IDs via `return_tokens_as_token_ids` (one
alignment bug found and fixed: the stop token appears in logprobs but not
in returned text); `delete_vllm_server` fires on normal completion **and
provably does not fire on failure** — the Deployment leaked a GPU twice
(OOM crash, deadlock force-stop) and had to be deleted by hand. Gates for
E2/B2a/C1/C3 are open; Michael's A2 work attaches here.

1. **Combo/pins:** existing — `trl==1.7.1`, `zenml==0.96.1`, vLLM `0.24.0` via parent image, the `zenml-rl-spike-vllm-server:0.1` derivative image.
2. **Smallest shape:** GPU_SETUP.md part 6 step 4 exactly: 1 iteration, 1 task, group 2, `--serving-mode warm_vllm`, node group at 2.
3. **Ownership:** ZenML records control steps and adapter artifacts; raw Kubernetes owns the serving pod. Deliberately no model-deployer.
4. **ZenML question:** does the "artifact-lineage-into-raw-serving" bridge actually hold? Specifically: does the exec+tar adapter materialization work against the S3 artifact store from inside the vLLM pod (pod identity → bucket read); do the HTTP logprobs align with tokenizer IDs (`vllm_http.py` fails loudly if not — either outcome is a finding); does `delete_vllm_server` fire on normal completion and what leaks when it doesn't.
5. **Stop condition:** *keep* if it runs green — Track E stress tests then attach here. *Escalate* if the logprob alignment check fails (that would mean the warm-serving path can't feed TRL at all without a tokenization detour, a core finding about HTTP-serving-based RL on any stack). *Abandon* nothing — this run gates half the menu.

#### A2 · Overlap rollout and training (`.submit()` futures, PLAN.md v1)

1. **Combo/pins:** same as A1; no new packages.
2. **Smallest shape:** modify the iteration loop so `generate_rollouts_from_endpoint` for iteration N+1 is submitted (against the *old* adapter, i.e. deliberately one version stale) while `grpo_update` for iteration N runs. 2 iterations is enough to see the overlap.
3. **Ownership:** unchanged — this tests ZenML's ability to *express* off-policy overlap, not a new framework.
4. **ZenML question:** can dynamic pipelines express "start step B before step A's consumer finished" cleanly, or does the futures API force awkward dependency contortions? What does the DAG show — does the overlap read as intentional or as spaghetti? Does the warm vLLM server tolerate a `load_lora_adapter` call while generation requests for the old adapter name are in flight (the adapter-refresh race — every async RL framework has to solve this; we should know what raw vLLM does).
5. **Stop condition:** *keep* if overlap works and saves visible wall clock (the by-hand iteration timer already measures it). *Escalate* to A3 if futures can't express it — "one pipeline can't do async RL" is exactly the one-pipeline-vs-two evidence the findings doc needs.

#### A3 · Two pipelines with trigger/poll (PLAN.md v2)

1. **Combo/pins:** same; uses `Client().trigger_pipeline` + `wait_for_pipeline_run_to_finish` (both OSS).
2. **Smallest shape:** a rollout pipeline (generate + score, writes episodes artifact) and a training pipeline (polls for episodes, trains, writes adapter). One handoff cycle is enough for the first findings; don't build the full loop until the handoff pattern is judged.
3. **Ownership:** ZenML owns both pipelines; the design burden is the shared-storage contract *between* runs — how does the training run name/find "the episodes artifact from rollout run N" without hardcoded run IDs.
4. **ZenML question:** Michael's shared-storage question, answered with evidence: is cross-run artifact addressing (by name/tag/version query) good enough to coordinate two live pipelines, or do you end up smuggling S3 prefixes around anyway (Hamza's `s3.getObject` worry in a new costume)? Also: polling latency, and whether the two runs' lineage stitches together in the dashboard or reads as two unrelated experiments.
5. **Stop condition:** *keep* only if A2 strained — PLAN.md already says v2 is evidence-gated. *Abandon* if A2 was comfortable; write "one pipeline suffices at this scale" as the verdict instead.

---

### Track B — Harbor

**Positioning context (researched 7/8, for whoever runs this track):** Harbor is neither "an evals tool" nor "an RL-environments tool" — it is the **task contract plus execution substrate** underneath both: a standardized task format (`task.toml` + instruction + verifier), a registry of benchmark datasets (Terminal-Bench 2 ships through it), and pluggable sandbox environments (Daytona, Modal, LangSmith, Blaxel, Novita — and, unofficially, our bridge). Evals and RL are two *consumers* of the same contract, differing only in who drives generation: evals plug in an installed agent that runs autonomously (Claude Code, Codex, LangGraph apps); RL replaces the agent with the trainer, which generates turn-by-turn against the same task and verifier (TRL's `environment_factory` — see B2b). Adoption signals as of July 2026: Anthropic's agent-evals engineering post names Harbor as the standard containerized-eval infrastructure, and LangChain has integrated deeply — occupying three slots around Harbor: the **agent slot** (Deep Agents/LangGraph as `--agent langgraph`), the **sandbox-provider slot** (LangSmith Sandboxes as `--env langsmith`), and the **results slot** (`--plugin langsmith`: every job recorded as a LangSmith dataset/experiment with the verifier's reward as feedback and traces attached). That three-slot pattern is the template: **ZenML can occupy the sandbox-provider slot (the bridge, formalized as an installable environment) and the results slot (a Harbor plugin recording jobs as ZenML runs/artifacts)** — and the plugin system dissolves the worktree README's old objection to the `harbor run` entrypoint ("ZenML invisible"): with a plugin, ZenML is visible without owning orchestration. Competitive note: the LangSmith plugin already ships the "reward + trace lineage" story B1/C1 propose — ZenML's differentiated slice is what LangSmith doesn't do: artifact lineage *into training* (B3), the sandbox substrate itself with snapshots (F1), and the loop connecting eval results back to interventions (G1/RL).

**State change (PR #5029, merging soon):** the worktree example has been promoted to a first-class `zenml.integrations.harbor` integration — typed campaign contracts, sha256 trial identities as cross-run join keys, `trials_per_step` shard packing, a shard-result materializer persisting the full Harbor job tree, `build_harbor_matrix → run_harbor_shard (mapped) → build_harbor_report` steps, an `examples/harbor_agent_evals` example, and an Agent evals docs guide (including *Benchmark operations* with regression gates and *From evals to training*). Validated live on Modal: caching/resume, registry benchmarks with per-task `docker_image` overrides, a real `claude-code` agent run with cost tracked through to the report. Track B entries below are rebased on this: B1 shrinks to what #5029 does *not* answer, B2a reuses the integration steps, and B3 is the PR's own named follow-up.

#### B1 · Harbor campaign on the Kubernetes sandbox flavor, at real fan-out

**Status: DONE 2026-07-09** — see rev. 11 note; findings on branch `spike/b1-harbor-k8s`, BREAKAGE_LOG 19–21, FINDINGS.md Theme 5. The 89-task fan-out (smallest-shape item 3) was deliberately not run: moot until the `docker_image` translation ships, since every terminal-bench task pins an image.

1. **Combo/pins (rebased on #5029):** use the merged `zenml.integrations.harbor` integration and `examples/harbor_agent_evals` — do not resurrect the worktree copies. Note the integration **canaries against Harbor 0.8** (explicit 0.8 API canary test, a 0.8 quiet-mode IndexError workaround), while upstream Harbor is at 0.16–0.18.x; the version-bump path is tracked work, and B2b's TRL path will pull *current* Harbor — so the eval integration and the RL path likely pin different Harbor versions in different envs (acceptable, but decide it consciously). Python gating (≥3.12 with graceful `get_requirements()` fallback) is already handled by the integration.
2. **Smallest shape (what #5029 leaves open):** everything validated so far is Modal. B1 is now the **Kubernetes-flavor pass**: the hermetic oracle-vs-nop head-to-head on the K8s sandbox flavor, then `dataset:terminal-bench-sample@2.0` — where a registry task pinning `docker_image` will hit the Modal-only translation wall by design — then, only if cheap, the full 89-task fan-out with `trials_per_step` tuned (the sharding knob is #5029's answer to the DAG-crawl worry; test the answer at real scale).
3. **Ownership:** ZenML owns matrix expansion, mapped trial steps, retries, report; Harbor owns task loading, agent loop, verifier, reward. Exactly the worktree design.
4. **ZenML question (rebased):** (a) Portability — is the "portable substrate" claim true on the K8s flavor: `docker_image` translation (still Modal-only, documented), asyncio-in-step behavior, sandbox session lifecycle and pod churn? (b) Scale — with shard packing, what does the 89-task benchmark actually cost in DAG readability and artifact volume (each shard's materializer persists the full job tree)? Note that #5029's live validation already answered the Harbor-path slice of E4 (identical reruns cache-hit; a hung shard re-executes alone). (d) **Integration shape: wrap vs plug in.** The current design wraps Harbor in mapped ZenML steps (ZenML is the entrypoint). Harbor's plugin system enables the inverse: `harbor run --env zenml --plugin zenml`, where Harbor stays the entrypoint users already know and a ZenML plugin records the job as a run with per-trial artifacts — the exact pattern LangChain shipped with `--plugin langsmith`. Prototype nothing for (d) during B1, but assess it: which shape would the sales conversations you've had actually land with, and what would the plugin need to record to be more than a LangSmith clone (artifact lineage into training data and adapters, not just scores and traces)?
5. **Stop condition:** *keep* — still the lowest-cost track (oracle agent, CPU-only, no LLM keys), now with the merged integration doing the heavy lifting. *Escalate* the `docker_image` gap to a core question ("should `KubernetesSandboxSettings.image` be the translation target?") the moment a registry task hits it on the K8s flavor. *Escalate* (d) to a product decision with Hamza regardless of B1's technical outcome — formalizing `--env zenml` + `--plugin zenml` as installable packages is a distribution question, not a spike question, and the LangChain precedent means the window is now. Note #5029 deliberately picks "wrap" and lists no plugin/Hub work in its non-goals — so (d) survives the PR intact.

#### B2 · Harbor inside the RL loop — eval gate, then TRL's native Harbor path

1. **Combo/pins:** B2a: as B1 plus the existing rl_spike stack. B2b: **TRL v1 with the `trl[harbor]` extra (`trl.experimental.harbor`)** — this path has hard floors: `transformers>=5.2.0` (the spike pins `<5`), `vllm>=0.22.0`, Python ≥3.12 via Harbor. Mandatory separate venv/image; treat that fragmentation cost itself as a logged finding.
2. **Smallest shape — two sub-experiments, run in this order:**
   - **B2a (eval gate):** after each `grpo_update`, insert the #5029 integration steps (`build_harbor_matrix` → `run_harbor_shard`) evaluating the *new adapter* on a tiny Harbor task set — post-#5029 this is composition, not bespoke code (could literally be 3 of our pipeline-writing tasks recast as Harbor tasks: instruction.md = the prompt, test.sh = a shell wrapper around `score_pipeline.py`). The Harbor agent would be a thin "call the warm vLLM endpoint once, write the completion to a file" script.
   - **B2b (TRL drives Harbor):** one ZenML step runs `GRPOTrainer(environment_factory=...)` against a tiny Harbor task suite for a handful of optimizer steps, adapter artifact in/out. TRL's vLLM runs colocated inside the trainer, so this does *not* depend on A1's warm endpoint. **Task variant — this is where the agentic upgrade of the spike task lives:** recast the pipeline-writing task as a short multi-turn Harbor task — *write a ZenML pipeline; you may execute it, read the traceback, and fix it; three turns max* — with the existing scorer logic in the verifier. Same task, but the model now iterates against a sandbox whose filesystem evolves (attempt → traceback → fix), which is what makes it agentic in the sense that matters, and what gives F1's snapshot demo something worth looking at.
3. **Ownership:** B2a — ZenML owns the RL loop and inserts Harbor as a per-iteration evaluator; Harbor owns one eval trial. B2b — **TRL owns generation, the multi-turn environment loop, and training; Harbor owns task + sandbox + verifier; ZenML owns the step wrapper, config/adapter artifacts, and surrounding evals** — the same "what residue remains" question as C3/D1, but with a strategic twist (below).
4. **ZenML question:** B2a tests whether "eval lineage next to training lineage in one run" is a real ZenML advantage (adapter vN → Harbor eval report vN in the same DAG — a story no framework-native stack shows). B2b — context first, because this section changed after a cross-check: the wall the first draft of this brief predicted ("agent harnesses sever the token/logprob link RL needs") is real, but **TRL has already shipped the workaround upstream**. With `environment_factory`, the trainer itself generates every turn of the rollout, so it always holds the policy's token IDs and logprobs; Harbor supplies the task, the sandbox the tool calls execute in, and the in-sandbox verifier for reward. TRL's own docs confirm the residual wall exactly where predicted: "installed agents" that run autonomously inside the container with their own inference emit only an after-the-fact trajectory — no policy tokens — and are explicitly unsupported for RL. So the questions become: (a) what does ZenML still see when TRL+Harbor swallow generation+environment+reward+training into one trainer call, and (b) the strategic one — TRL's Harbor integration needs *a Harbor environment implementation underneath*, and we already have one: **can `ZenMLSandboxEnvironment` be the environment TRL's Harbor adapter runs on, making ZenML Sandbox the execution substrate under TRL-native RL?** If yes, that's a product-boundary finding bigger than anything else in Track B.
5. **Stop condition:** B2a: *keep* if the eval report lands as a per-iteration artifact without fighting the loop. B2b: *keep* one bounded attempt regardless of outcome; *escalate* the bridge-under-TRL question (b) to Hamza the moment there's evidence either way — it reframes what the Sandbox component is for.

#### B3 · Harbor→RL trajectory exporter — eval traces become training-data artifacts

1. **Combo/pins:** the #5029 integration plus the existing rl_spike episode schema. **Status upgrade: this is no longer a survey proposal — it is #5029's own named follow-up** ("trajectory→training-dataset utilities are the natural follow-up; the archives already carry rollouts + rewards"), and the Agent evals guide already promises the story (*From evals to training*: SFT from winning trajectories, rejection sampling, eval-gated promotion). B3 is now "build what the guide promises." No training in the first version — the exporter is the experiment.
2. **Smallest shape:** run a small B1 campaign, then one conversion step: use the shard materializer's `download_jobs_dir()` to read the per-trial archives and emit a normalized dataset artifact — one record per trial with the **sha256 trial identity** (#5029's cross-run join key — reuse it, don't invent a second identity scheme), task ref + version pin, agent, reward, sandbox image, and a trajectory reference — labeled "RL episode candidates". A stub `grpo_update` consuming it comes only after the exporter is judged useful.
3. **Ownership:** Harbor owns trial internals and the raw jobs tree; ZenML owns the campaign, the conversion step, schema validation, and — the point — the *lineage edge from an eval run to a training-data artifact*.
4. **ZenML question:** can "this reward came from this verifier at this task version in this sandbox image, and here is the resulting training example" be expressed as first-class lineage? This is the eval→training-data bridge, and it's the same shape as the Kitaru end-goal loop already parked in PLAN.md §5 (traces → failure modes → reward update → re-run RL) — so findings here transfer beyond the spike.
5. **Stop condition:** *keep* if conversion means reading Harbor's documented result/trajectory formats. *Abandon* if it degrades into scraping Harbor internals. *Escalate* if Harbor's trajectory format turns out stable enough that ZenML should treat it as a first-class artifact type. **Design note (from the RELAI case study):** whatever B3 exports should be built to accumulate into a *regression suite* — RELAI's "regression traps" idea: past environments are kept, and every future fix is evaluated against all of them, not just the newest failure. #5029 already provides the mechanism half (trial-identity join keys, and regression gates in the *Benchmark operations* guide); B3's job is the accumulation half — that property is what makes the exported artifact valuable to Kitaru's eval story, not just to the spike. One constraint to log: the integration rejects multi-step tasks with `NotImplementedError`, so B2b's agentic task variant can't be *evaluated through the integration* until that lifts — fine for now, one line in the findings doc.

---

### Track C — Verifier-first: the `verifiers` package

Context for whoever picks this up: `verifiers` (Prime Intellect / Will Brown) packages an RL task as an *environment* — dataset + rubric (reward functions) + interaction protocol — loaded via `load_environment(...)`. The same environment object is used for evals (`env.evaluate(client, model, ...)` against any OpenAI-compatible endpoint) and for training (prime-rl, or the bundled `vf.RLTrainer`). Current line is v0.1.x with releases roughly monthly (a cross-checked brief reports v0.1.14 as of July 2026; v0.1.10 in Feb 2026 added OpenEnv/BrowserEnv integrations and trajectory-based rollout tracking, and there are reports of Harbor taskset integration landing in the newer releases — verify at build time). Pin exactly and expect API movement — same discipline as the TRL pin.

#### C1 · verifiers environment eval as a mapped ZenML campaign

1. **Combo/pins:** latest `verifiers` 0.1.x (0.1.14 reported — re-check before building), warm vLLM endpoint from A1 as the OpenAI-compatible target, or any API endpoint for a dry variant.
2. **Smallest shape:** one ZenML pipeline: a step loads a Hub environment or a local one, `run_env_eval.map(...)` fans out over environments (or dataset shards of one environment), each mapped step calls `env.evaluate(...)` against the endpoint and returns the results dataset; a report step aggregates. Structurally it's `sandbox_harbor/run.py` with verifiers swapped in for Harbor — reuse that pipeline's shape wholesale.
3. **Ownership:** verifiers owns rollout, parsing, rubric scoring per environment; ZenML owns fan-out, retries, artifact/lineage, aggregation.
4. **ZenML question:** the verifier-first question from the planning guidance — when the framework already owns rollout+reward, does ZenML's artifact/lineage layer add enough (comparable eval artifacts across model versions, mapped-step retries, dashboard reports) to justify the wrapping? Also mechanical: verifiers is async-native — does `asyncio.run` inside a step behave (Harbor bridge says probably yes), and what do verifiers' rollout outputs look like as ZenML artifacts (they're HF datasets — is the materializer story clean)?
5. **Stop condition:** *keep* if the wrapped version produces something the bare `vf-eval` CLI doesn't (versioned eval artifacts tied to adapter lineage). *Abandon* if it's a thin wrapper adding only overhead — and write that verdict down, because "ZenML adds nothing to X" is a legitimate survey finding.

#### C2 · Port the pipeline-writing task as a verifiers environment (the sandbox-reward collision) — **DONE (7/9, see verifiers_c2/README.md; FINDINGS.md Theme 5)**

*Outcome: the keep branch. The rubric-opens-a-ZenML-Sandbox path composes — 18/18 exact reward matches on canned completions across 5 tasks, scored concurrently (4 sessions at a time) through verifiers' real machinery. Costs: blocking session calls need a thread + concurrency cap, and verifiers swallows reward-func exceptions into 0.0 (entry-16 ambiguity rebuilt upstream; the rubric records `state["infra_error"]` as the workaround). The native-sandbox question is answered too: both their `SandboxEnv` and the new v1 lease API hardcode `prime-sandboxes`, but the v1 client contract is five duck-typed async methods ZenML's session API satisfies — one hardcoded import is the whole gap. Environment lives in `verifiers_c2/zenml_pipeline_env.py` (`load_environment()`), ready for C1/C3.*

1. **Combo/pins:** as C1. *(Built against `verifiers==0.1.14`, re-checked 7/9.)*
2. **Smallest shape:** a `SingleTurnEnv` with `tasks.jsonl` as the dataset and a rubric function that must produce the same 0–1 reward as `score_pipeline.py`. Evaluate 5 tasks against the warm endpoint; compare rewards against the existing scorer's output on identical completions.
3. **Ownership:** verifiers owns everything per-example; ZenML is not in the loop yet — this is a *contract experiment*, one file plus an eval run.
4. **ZenML question:** indirectly, the spike's founding decision. Our reward's defining property is that it runs *inside a sandbox where the generated code executes*. verifiers rubric functions run in the eval/trainer process. So the rubric must itself open a ZenML Sandbox session per completion (importing `zenml.client` inside a verifiers rubric — does that even compose?), or shell out, or the isolation property is silently lost. Whichever of those happens is the finding: it defines what "bring your own sandboxed reward" costs in a verifier-first framework, and it's the exact question a ZenML-Sandboxes-as-a-product pitch to that ecosystem depends on. (Worth knowing: verifiers v0.1.10 release notes mention "safer sandbox lifecycle behavior" — investigate what sandbox concept they now have natively and whether ZenML Sandbox could slot in behind it.)
5. **Stop condition:** *keep* if the rubric-opens-a-Sandbox-session path works, because it directly enables C3. *Escalate* (don't abandon) if it can't compose — that's a product-boundary finding for Hamza, not a dead example.

#### C3 · verifiers `RLTrainer` inside one ZenML step (framework owns rollout+train, ZenML owns the outer loop)

1. **Combo/pins:** latest `verifiers` 0.1.x with its nano trainer `vf.RLTrainer` (replaced `vf.GRPOTrainer` in v0.1.7); needs the vLLM inference server + trainer split across the same 2 GPUs the current warm mode uses.
2. **Smallest shape:** one ZenML step that: takes environment name + adapter artifact in, runs a short `RLTrainer` session (a handful of optimizer steps) with the environment from C2, returns the checkpoint as an artifact. The pipeline around it is just load-env → train-step → (optionally) a C1-style eval step.
3. **Ownership:** verifiers owns rollout generation, reward, and the optimizer loop *internally*; ZenML owns config-in/checkpoint-out lineage, and the eval steps around it. This is the "framework-run-inside-a-step" shape from the planning guidance, at the smallest possible scale.
4. **ZenML question:** PLAN.md rejected full-span frameworks for v0 with the argument "the loop disappears into one step — no ZenML tracking". This tests what actually remains: per-iteration reward curves are gone (they live in the framework's logs), but checkpoints, configs, and surrounding evals are still artifacts. Is that residue worth anything? Secondary, very concrete: the trainer step launches a vLLM server subprocess — entry 10's fork-unsafe log handler and the GPU placement settings both get re-stressed by a framework we don't control.
5. **Stop condition:** *keep* if the step runs and the residual lineage is articulable. *Abandon* the deeper version (multi-hour runs) either way — the finding is the ownership boundary, not the training result.

---

### Track D — Training-first heavyweights: prime-rl (and where OpenRLHF sits)

#### D1 · prime-rl as a black-box ZenML step (verify PLAN.md's prediction empirically)

1. **Combo/pins:** `prime-rl` — **pin at build time from its releases page**; the project went through a major redesign for INTELLECT-3 and only recently adopted a regular release schedule, so any pin chosen today goes stale fast. Installs via `uv`; expects TOML config composition; native verifiers-environment integration (so C2's environment is directly reusable as the task).
2. **Smallest shape:** one ZenML step that writes a minimal `rl.toml` (small Qwen, the C2 environment, a handful of steps), launches prime-rl's process group as a supervised subprocess, streams its logs, and returns the checkpoint directory as a `Path` artifact. Single-node, 2 GPU. Do **not** attempt to decompose prime-rl's internals into ZenML steps — the point is the black-box boundary.
3. **Ownership:** prime-rl owns *everything* in the loop — async rollouts, inference server, trainer, checkpointing. ZenML owns: the config artifact in, the checkpoint artifact out, the wall clock, and whatever surrounding eval steps we attach.
4. **ZenML question:** the honest version of "would we recommend ZenML for this workload" — sharpened by the 7/8 call: Hamza's position is that distributed-training mechanics (multi-node coordination, GPU scheduling, Ray/Volcano territory) are a solved problem ZenML should not compete on, and the opportunity is combining the *sandbox workload* with the *training workload*. So D1's real question is not "can ZenML wrap prime-rl" but **where the seam sits between the layer we own (sandboxes, orchestration, lineage, recovery) and the training runtime we don't** — what crosses that seam cleanly (configs, checkpoints, eval artifacts) and what can't (per-step reward curves, in-flight weight sync, worker health). prime-rl is architecturally the anti-ZenML shape: trainer and inference are separate long-lived processes with their own coordination, designed around asynchrony ZenML steps can't see into. Concrete sub-questions: can a ZenML step supervise a multi-process framework at all (log capture across processes — entry 10 says the log handler already chokes on one fork; prime-rl forks a lot more); what happens on cancellation (kill the run — does the step's process tree die, or do orphaned vLLM processes hold the GPUs, extending entry 6's zombie finding to the process level); is `Path`-artifact checkpoint transport viable at real checkpoint sizes (adapters are MBs; full-model checkpoints are not).
5. **Stop condition:** *keep* one honest attempt regardless of outcome — the findings doc needs the "ZenML around a full-span framework" verdict written from evidence, and a Kitaru-adjacent bonus: the same wrap-an-opinionated-runtime pattern is what any "ZenML for agentic post-training" pitch would look like. *Abandon* after the boundary findings are logged; do not iterate toward making prime-rl comfortable.

#### D2 · OpenRLHF — listed, deprioritized

OpenRLHF (currently `openrlhf==0.10.4`; note the 0.10.x line moved to hierarchical dotted CLI flags, so old command snippets are stale) is Ray-based: launching it means standing up a Ray cluster (or Ray-on-K8s) inside or beside the ZenML run. That's an infrastructure project, not a survey example, and its findings would mostly be about Ray, not ZenML. Keep it on the list as the named representative of the "Ray-native RL framework" class, with one paragraph in the findings doc explaining *why* it was skipped (the explanation itself is a finding: ZenML has no story for "my step needs a Ray cluster"). Only escalate to actually running it if a customer conversation makes Ray-based RL concrete — and if D1 (prime-rl) already answered the "framework owns everything" question, OpenRLHF adds mostly Ray-specific pain, not new ZenML findings.

#### D3 · verl — listed, second opinion only

verl (currently `verl==0.8.0` on PyPI) is the other production heavyweight, also Ray-based, and its own install docs recommend source installs for anything custom — so as a ZenML example it would mainly stress image builds, source-install packaging, and nested Ray logs, which largely duplicates the D2 skip-rationale plus the 8/8b image findings we already have. Defer with the same one-paragraph treatment as D2; revisit only if a customer names verl specifically (it is becoming a default open-source post-training stack, so that ask is plausible).

---

### Track E — Serving/resource stress tests (attach to Track A, not standalone)

These are experiments, not examples — each is a deliberate abuse of an A-track run, and each maps to a specific gap already suspected in the BREAKAGE_LOG.

| Experiment | What you do | Finding it targets |
|---|---|---|
| E1 · Kill mid-run — **ANSWERED for free (7/9)** | The training run supplied both halves without scheduling the test: the OOM-killed orchestrator (entry 14) and the retry deadlock (entry 15) | vLLM Deployment leaks: **confirmed twice** (survived an orchestrator crash and a force-stop; deleted by hand). Zombie modes catalogued: headless `running` (14), unfinishable `running` with steps stuck `retrying` (15). Recovery by hand: `runs stop` + manual Deployment/Service delete + job cleanup |
| E2 · Adapter refresh under load | Fire `load_adapter_into_vllm` for iter N+1 while N's generation requests are still in flight (natural side effect of A2) | The adapter-swap race every async RL system must handle; what raw vLLM's `load_inplace=true` semantics are under concurrent requests |
| E3 · Transport volume at scale — **DONE (7/9, DATA_LAYER.md)** | Measured from run `7c7d72c7` + the four calibration runs via `measure_data_layer.py`; no new runs, no GPU | Answered with numbers: episodes are 3% of bytes (10 KB each, 2.8 MB/iteration) — any anti-pattern is per-artifact fixed cost (280 registrations/iter, 293 ms/artifact ingest), never bandwidth. Weights dominate (89% of bytes; the trained adapter gzips 4× worse than the zero-init one) at ~330 MB of S3 round-trips per iteration. Volume-layer verdict: clear win for the weights channel (also kills the exec-websocket adapter push), marginal for episodes (batching does the same for free), and untouched: the real fan-out cost, 73% per-episode harness overhead |
| E4 · Retry semantics on mapped steps — **ANSWERED for free (7/9), worse than feared** | The training run's 429 bursts exercised retries at scale without any forcing | Retries mostly work (429-killed pods came back across all runs), but the relaunch path itself can be killed by the same 429 burst, leaving the step in `retrying` forever with no pod and no timeout — the run deadlocks (entry 15). The original question (retried episode ≠ original sample — visible anywhere?) remains open but is now secondary to "retries need a terminal escape" |
| E5 · SGLang serving swap — **deferred** | Replace the warm vLLM server with an SGLang server for one rollout step | Whether a future ZenML serving abstraction should be engine-agnostic; SGLang's RL-oriented primitives (sleep/wake memory management, weight refit from disk/tensor) vs vLLM's runtime-LoRA path. Deferred until warm-vLLM is fully characterized — comparing two uncharacterized serving paths teaches nothing |

Stop conditions are uniform: each experiment is one run plus one BREAKAGE_LOG entry; none gets a second iteration (E5, if ever run, gets the A1 treatment instead).

---

### Track F — Sandbox state as experiment state (added after the 7/8 Hamza call)

#### F1 · Episode filesystem snapshots — **DONE (7/9, see SNAPSHOTS.md; entries 17–18)**

*Outcome: the mechanics work and the substrate story is real — failing
episodes snapshot before teardown, the ref rides the episode record, and
`restore_sandbox.py` reopened a failed sandbox and diagnosed an entry-16
lookalike in one command. Answers to this section's questions: the
support matrix is **Modal-only** (Kubernetes/local raise
`NotImplementedError`, documented; the open GKE PR #4870 is a different
flavor — that flavor gap is entry 17 and the headline escalation);
snapshot latency on Modal measured ~1.3 s per failing episode, so
failure-only is cheap and always-on is plausible; snapshots are invisible
to lineage unless user code carries them (gap list item 2); bonus entry
18 — the session filesystem API has no workdir contract across flavors.
The agentic-demo upgrade below (snapshot a multi-turn trial's filesystem)
remains open for B1/B2b to pick up.*

1. **Combo/pins:** existing spike only, no new frameworks. Step zero is a fact-check: the Sandbox session API lists snapshots (#4986), but which *flavors* implement it is unknown — Modal probably, Kubernetes and local unclear. The support matrix is itself the first finding.
2. **Smallest shape:** modify `run_episode` so that on scorer failure (or always, behind a flag) it snapshots the session *before* destroy and records the snapshot reference in the episode record and step metadata. Then the manual test that matters: starting from a failed episode in the dashboard, can a human actually get back to the filesystem — restore the snapshot into a fresh session and look around? The dry run is enough to prove the mechanics; no GPU. **But run the *demo* on an agentic trial (B1's Harbor tasks, or B2b's multi-turn task), not the single-turn baseline** — a single-turn episode's filesystem is just `pipeline.py` plus the scorer, whereas an agentic trial's filesystem has history (attempt, traceback, edit), which is the thing worth clicking into and the version Hamza was actually describing.
3. **Ownership:** all ZenML — this is a pure "is the substrate story real" experiment. No external framework is involved, which is exactly why it's a good contrast to the rest of the menu.
4. **ZenML question:** Hamza's strongest product thread from the call, made testable. Concrete scenario: an agent edits files in a sandbox, the run scores 0.0, and today the only trace is an error string on the episode record (BREAKAGE entry 7's whole problem). Can the sandbox filesystem at the moment of failure become a linkable, inspectable object in the lineage — episode → snapshot → reward → adapter — or does that need core work (snapshot refs as an artifact type, a restore-from-snapshot flow, a dashboard affordance)? Secondary: snapshot latency and storage cost, because "snapshot every episode" × 400 episodes is a very different proposition from "snapshot on failure only".
5. **Stop condition:** *keep* if a snapshot ref can ride the episode record and be restored by hand — that's already a demo (the DigitalOcean angle from the call: sandbox snapshotting on their infrastructure). *Escalate* the gap list to Hamza/core if the API exists but nothing connects it to lineage — that gap list is the "sandbox workload + training workload combined" product pitch in requirements form. *Abandon* always-on snapshots if latency is brutal; keep failure-only.

---

### Track G — Cheaper interventions on the same harness: GEPA (prompt evolution)

Context for whoever picks this up: GEPA (Genetic-Pareto, arXiv 2507.19457 — "Reflective Prompt Evolution Can Outperform Reinforcement Learning") optimizes textual components instead of weights. Instead of collapsing each rollout into a scalar reward the way GRPO does, an LLM *reads* the execution traces — error messages, score breakdowns — diagnoses failures, proposes prompt mutations, and keeps a Pareto frontier of candidates. It typically needs far fewer rollouts than RL, needs no training GPU, and works on frozen/API models. It ships as a standalone `gepa` package (custom systems plug in via a two-method `GEPAAdapter`: evaluate a candidate over a minibatch, extract trace text for reflection) and as `dspy.GEPA` on top of it; MLflow has already integrated it into `mlflow.genai.optimize_prompts()` — which is competitive context, not just tooling context. RELAI's talk places exactly this method in its "harness layer" (cheapest testable intervention above memory, far below weights).

#### G1 · GEPA on the existing spike harness — same loop, different update rule

1. **Combo/pins:** standalone `gepa` (pin at build time), an OpenAI-compatible endpoint for the task model (A1's warm vLLM, or any hosted API model — meaning this can run with **zero GPUs**), and a stronger API model as the reflection LM. Deliberately *not* DSPy for the spike: DSPy's program abstraction would replace our harness, and the point is to reuse it — DSPy stays the named escalation if the standalone adapter chafes.
2. **Smallest shape:** a ZenML pipeline where the artifact threading the loop is the **system prompt/cheatsheet from `prompts.py`** instead of a LoRA adapter: a `GEPAAdapter` whose evaluate() runs candidates through the existing generate → sandbox-score path, and whose reflection dataset is built from the scorer's reward JSON (breakdown, error string, spec clauses, run output tail — which is already exactly the "rich textual feedback" GEPA feeds its reflection LM; GRPO has been discarding this text and keeping only the scalar). A dozen tasks, a small metric-call budget, output = evolved cheatsheet artifact + per-candidate eval report.
3. **Ownership:** GEPA owns the propose/reflect/select algorithm; ZenML owns everything else — tasks, sandbox scoring, lineage, the candidate artifacts, and the report. Note this is the *inverse* of Track D: the external package is a small library inside our loop, the way TRL was demoted in v0.
4. **ZenML question:** three that nothing else on the menu asks. (a) **Genericity of the loop:** does the spike's shape (generate → sandbox-verify → update artifact → iterate) survive swapping the update rule and the artifact type — i.e., is ZenML's real value proposition "the verified-improvement loop, whatever the intervention layer", not "RL support"? (b) **Population lineage:** GEPA maintains a Pareto *frontier* of candidates, not a single adapter thread — adapter v1→v2→v3 lineage doesn't fit; how does ZenML represent a candidate tree where the "best" artifact is per-task, not global? (c) **Prompt-as-artifact:** versioned prompt → eval-report lineage, plus a second model in the loop (the reflection LM: secret management, cost attribution per optimization run). Bonus head-to-head: same tasks, same scorer — GEPA reward curve and cost vs the GRPO baseline. **Honesty note for the findings doc:** this comparison is tilted toward GEPA by construction — the task was designed so the prompt (the cheatsheet) is the model's only knowledge channel for a post-cutoff API. Report it as illustrative of the intervention spectrum (prompts first, weights when prompts saturate — RELAI's "smallest durable change at the right layer"), not as a general GEPA-beats-GRPO verdict.
5. **Stop condition:** *keep* if the loop-shape reuse is real — that finding upgrades the whole spike's story from "ZenML for RL" to "ZenML for the agent-improvement spectrum", which is also the shape customer conversations will take ("can I do the less invasive intervention first?"). *Escalate* the population-lineage gap (b) if ZenML genuinely can't represent it — that's a core artifact-model question. *Abandon* only if the adapter fight costs more than the harness reuse saves, which would itself be worth one log entry.

---

## 3 · Coverage check — menu entries vs the open questions

| Open question (from PLAN.md §4 / the call / planning guidance) | Answered by |
|---|---|
| One pipeline vs two, with evidence | A2 → A3 |
| Data-layer verdict (episodes/weights transport) | E3, A3, D1 (checkpoint sizes) |
| Warm serving + adapter lineage into raw infra | **A1 done, E1 answered** (leak + zombie catalogue in BREAKAGE_LOG 14/15); E2 still open (rides on A2) |
| Does ZenML help eval/reward lineage without owning training | B1, B2a, C1 |
| Can external task/verifier/agent loops replace our harness | B2b (TRL's `environment_factory` path); **C2 — DONE** (verifiers can own the loop while a rubric drives ZenML Sandbox sessions: 18/18 reward parity; verifiers_c2/README.md) |
| Framework owns rollout+train, ZenML owns outer loop | C3, B2b |
| Eval traces → training-data lineage (Kitaru-adjacent) | B3 |
| Can ZenML Sandbox be the substrate under a framework-owned loop | B2b question (b) |
| Sandbox filesystem state as inspectable/recoverable experiment state | **F1 — DONE** (SNAPSHOTS.md; real but Modal-only, flavor gap escalated as entry 17) |
| Data layer: object store vs mounted-volume for weights/episodes | **E3 — DONE** (DATA_LAYER.md; volume layer motivated for weights, not episodes) |
| Should the task be agentic / multi-turn | Baseline stays single-turn (control); agentic variant lives in B2b's task; Kitaru-as-policy-agent ruled out (installed-agent pattern, no tokens to train on) — see §1 note |
| Cheaper interventions on the same harness (the RELAI "layer" spectrum) | G1 — GEPA prompt evolution reusing tasks + sandbox scorer |
| Is the loop shape generic across intervention types (prompts vs weights) | G1 question (a) |
| Population/Pareto lineage (candidate trees, not version threads) | G1 question (b) |
| Which Harbor integration shape wins: wrap (ZenML entrypoint) vs plug in (`--env zenml --plugin zenml`) | B1 question (d) → product decision (untouched by #5029, which picks "wrap") |
| Retry/cache semantics on the Harbor path | Answered by #5029's live validation (cache-hit reruns, hung-shard resume); **E4 answered for the RL episode path** (retries work until the relaunch itself dies — entry 15) |
| Framework owns everything, ZenML = wrapper | D1 |
| Sandbox flavor portability + fan-out at benchmark scale | B1 |
| Cancellation/retry/cost behavior for long RL runs | **Answered by the 7/9 training run** (E1/E4 outcomes above; ~47 min/iteration, ~$13.5/session — TRAINING_RUN.md) |
| "Would we recommend ZenML for this workload, shortest path to yes" | Synthesis of all of the above — the findings doc, not one example |

---

## 4 · Tomorrow's output, scoring, and sequencing

**Tomorrow's concrete output is a ranked matrix plus a small selected set of builds — not equal coverage of the whole menu.** A sensible P0 set is four-to-five sharply different ownership shapes: A1 (deepen the baseline), B1 (ZenML outside, framework inside), one of C1/C2 (verifier-first), one of B2b/C3/D1 (framework owns the loop), and **G1 (GEPA — same harness, cheaper intervention layer)**, which earns consideration despite being a late addition because it needs no GPU, reuses everything, and is the only entry that tests whether the spike's loop shape generalizes beyond RL at all. Everything else is P1/P2 or a skip-with-rationale.

**Priority note after the 7/8 Hamza call and the RELAI case study:** strategic weight shifts toward the substrate/observability entries — **F1 (filesystem snapshots)** and **B2b question (b) (Sandbox under TRL)** are the two experiments most aligned with where Hamza is pointing (sandbox workload + training workload combined; state inspection/recovery; the volume/data layer), and framework *breadth* matters less than it did. G1 reinforces the same direction from the other side: it's the intervention where the sandbox/verification/lineage layer does all the work and the training runtime disappears — and RELAI's talk is market evidence that customers frame agent improvement as a spectrum of interventions (memory → prompts/harness → weights) and will ask for the cheaper layer first. The findings doc's closing question should widen accordingly: not "would we recommend ZenML for RL" but "would we recommend ZenML as the harness for the agent-improvement spectrum". E3's measurement now has a named consumer: it's the evidence for or against the volume layer — *delivered 7/9: the numbers motivate the volume for the weights channel only (DATA_LAYER.md)*. The Ray-adjacent skips (D2/D3) now have Hamza's explicit backing. One urgency signal from the Harbor research: LangChain's `--plugin langsmith` already ships reward-as-feedback + trace lineage for Harbor jobs — the eval-lineage ground B1/C1 target is being occupied now, which raises B1's priority and makes its question (d) (wrap vs plugin, and what ZenML records that LangSmith doesn't) a near-term product conversation rather than a someday one.

**Division of labour, given Michael is on the async work:** Michael's async track *is* the A1→A2 path (warm server, overlap, adapter-refresh race), so don't both converge on it. A workable split: Michael owns A1 verification and A2; Alex takes the CPU-parallel experiments — B1 (Harbor on K8s flavor), C2 (verifiers reward collision), F1 (snapshots) — none of which need a GPU or Michael's endpoint, so a blocked GPU morning costs nothing. Reconvene on evidence in the afternoon.

To rank candidates in the meeting, score each 1–5 on five questions and write one paragraph of evidence:

1. **ZenML visibility** — can ZenML see meaningful phases, artifacts, retries, and failures, or does everything vanish into one step?
2. **Resource lifecycle stress** — does it exercise GPUs, warm servers, sandboxes, process cleanup, or cancellation in a way ZenML must manage?
3. **Reward/eval lineage** — can reward be traced back to task version, verifier code, sandbox image, adapter, and output?
4. **Artifact/data pressure** — does it produce large or numerous artifacts (job trees, token logs, checkpoints, 400 mapped outputs), and does ZenML cope?
5. **Core-product signal** — if it breaks, does the breakage imply a ZenML feature gap, or just "this framework has its own platform"?

A candidate earns a build slot only if it's likely to produce at least one **new** BREAKAGE_LOG-grade finding. "Dependency installation was annoying" is a compatibility note, not an example.

### Sequencing and dependencies (no calendar — order only)

1. ~~**A1** first~~ **A1 done (7/8–7/9)** — its gates (E2, B2a, C1, C3) are open, and its failure modes delivered E1/E4's answers as a side effect.
2. **B1** — CPU-only, oracle-agent, no GPU cost, and post-#5029 it's smaller than originally scoped: the Kubernetes-flavor pass plus the scale test, using the merged integration. B3 rises with it — now sanctioned follow-up work with its substrate already merged, not a speculative example.
3. ~~**E3**~~ **E3 done (7/9)** — measured from the staging artifacts, no run needed; verdicts in `DATA_LAYER.md`.
4. ~~**F1 (snapshots)**~~ **F1 done (7/9)** — support matrix, snapshot-on-failure, and the by-hand restore demo in `SNAPSHOTS.md`; the agentic-trial demo upgrade transfers to B1/B2b.
5. **G1 (GEPA)** is similarly GPU-optional (API task model + API reflection model + the local sandbox scorer) and reuses the harness as-is — it can run in the same "CPU-parallel" lane as B1/C2/F1, budget-limited by API spend rather than node-hours. If A1's endpoint is up, point the task model there instead for a fully self-hosted variant.
6. ~~**C2** before C1 and C3~~ **C2 done (7/9)** — composed cleanly; its environment (`verifiers_c2/zenml_pipeline_env.py`) is the reusable artifact C1 and C3 were waiting on.
7. **A2** after A1 is green (overlap needs the warm server), with **E2** as its free rider.
8. **C1**, then **C3** — C2's environment now exists (7/9), so these are gated only on wanting A1's warm endpoint up.
9. **B3** rides directly on B1's campaign outputs — it's a conversion step over artifacts that already exist, so it costs almost nothing once B1 has run.
10. **B2a** once A1 is stable (needs the endpoint). **B2b** is independent of A1 (TRL colocates its own vLLM) but needs its Python 3.12 / transformers 5.x environment built first — sequence it alongside or after B1, since B1 builds that environment anyway.
11. **D1** last among the builds — it needs the C2 environment, both GPUs exclusively, and its findings are about the boundary, so it benefits from everything already learned. If B2b already answered "framework owns the loop, what does ZenML see?", D1's remaining value is the multi-process supervision/cancellation angle specifically.
12. **A3** only if A2 produced strain; ~~E1/E4 whenever a run is otherwise being abandoned~~ — both answered by the 7/9 training run's own failures (entries 14/15); no destructive tests needed.
13. **D2 (OpenRLHF), D3 (verl), E5 (SGLang)** — write the skip/defer rationale paragraphs; build nothing.

Hard dependency edges: A1 (done) → {A2, E2, B2a, C1, C3} — all now unblocked; B1 → {B3, B2b (shared 3.12 env)}; C2 (done) → {C1, C3, D1} — environment delivered; A2 → A3 (evidence gate); G1 → nothing (fully parallel; optionally consumes A1's endpoint); everything → the findings doc (`FINDINGS.md`, first edition written 7/9 — future entries update it).

---

## 5 · Risks and open unknowns to validate at build time

- **Package drift is the survey's biggest tax.** `verifiers` releases monthly and its trainer API already changed once (v0.1.7); `prime-rl` just left a major redesign; `harbor` upstream is at 0.16–0.18.x while the #5029 integration deliberately canaries **0.8** (explicit API canary test) — meaning the eval integration and the TRL/`environment_factory` RL path (which pulls current Harbor) will likely pin *different Harbor versions in different envs*. Acceptable, but make it a conscious decision, and treat the integration's version bump as tracked work. The GitHub org also moved to `harbor-framework/harbor`. Every entry above says "pin at build time" — treat re-checking latest versions as step zero of each build, and record the pin in the example's requirements the way `trl==1.7.1` is recorded now.
- **Environment fragmentation is unavoidable — plan it, don't fight it.** Three incompatible floors now coexist: the current spike (Python 3.11 images, `transformers>=4.56,<5`), Harbor 0.18.x (Python ≥3.12), and TRL's `environment_factory` path (`transformers>=5.2.0`, `vllm>=0.22.0`). One venv per candidate, one sandbox/pipeline image variant per Python floor, and `examples/rl_spike/requirements.txt` stays the baseline environment only — surveyed frameworks get sibling requirements files or sibling example directories. Also a caution for the findings doc: a decomposed ZenML+TRL loop and a one-step framework runner are not competing implementations of the same thing — they expose different ownership boundaries, and the comparison must say so or "framework X is easier" will be misread when the truth is "framework X hides the inner loop".
- **GPU budget:** A-track and C3/D1 need the 2-node warm topology (~$2.44/hr while up, per GPU_SETUP.md). B1, C2's dry variant, and all planning cost nothing. E-track destructive tests should be scheduled onto runs already slated for teardown.
- **The `rlft_harbor_daytona/` untracked directory** on the current branch appears to be generated Harbor `jobs/` output, not source; with #5029 landing `examples/harbor_agent_evals` as canonical, clean it up rather than migrate it.
- **Worktree → branch migration: resolved by #5029** — the integration supersedes both worktree examples; nothing from the worktrees should be copied forward.
- **#5030** (remote image builders re-apply `.dockerignore` and drop generated context files, found while validating the Modal-orchestrator path) is a BREAKAGE_LOG-grade finding from adjacent work — record it in the log so the findings doc is complete.
- **Namespace collision:** warm-vLLM assumes one run per namespace (fixed Deployment/Service names). A2's overlap and any parallel survey runs must respect that or parameterize the names first.

---

## 6 · References

- prime-rl: https://github.com/PrimeIntellect-ai/prime-rl (releases: https://github.com/PrimeIntellect-ai/prime-rl/releases)
- verifiers: https://github.com/PrimeIntellect-ai/verifiers · https://pypi.org/project/verifiers/
- Prime Intellect environment install/use docs: https://docs.primeintellect.ai/tutorials-environments/install
- TRL rollout_func decoupling: https://github.com/huggingface/trl/issues/5121 · multi-turn gap: https://github.com/huggingface/trl/issues/4543
- vLLM runtime LoRA loading: https://docs.vllm.ai/en/latest/features/lora/ · LoRA resolver plugins: https://docs.vllm.ai/en/stable/design/lora_resolver_plugins/
- TRL v1 + Harbor integration (`environment_factory`): https://huggingface.co/docs/trl/harbor · general environment contract: https://huggingface.co/docs/trl/openenv · https://pypi.org/project/trl/
- Harbor: https://www.harborframework.com/ · https://pypi.org/project/harbor/
- OpenRLHF: https://github.com/OpenRLHF/OpenRLHF · https://pypi.org/project/openrlhf/
- verl: https://pypi.org/project/verl/
- SGLang for RL systems: https://docs.sglang.io/advanced_features/sglang_for_rl.html
- GEPA: https://github.com/gepa-ai/gepa · https://pypi.org/project/gepa/ · paper: https://arxiv.org/abs/2507.19457 · dspy.GEPA: https://dspy.ai/api/optimizers/GEPA/overview/
- RELAI VCL case study (LLMOps database): https://www.zenml.io/llmops-database/verifiable-continual-learning-for-ai-agents-in-production
- Harbor × LangChain: https://www.langchain.com/blog/unified-stack-for-evaluating-agents · https://docs.langchain.com/langsmith/sandbox-harbor · Harbor GitHub: https://github.com/harbor-framework/harbor
- Anthropic on agent evals (names Harbor as standard infra): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- ZenML Harbor integration PR: https://github.com/zenml-io/zenml/pull/5029 · related image-builder issue: zenml-io/zenml#5030
- Repo-local: `examples/rl_spike/{PLAN,IMPLEMENTATION_NOTES,BREAKAGE_LOG,GPU_SETUP}.md`; `.worktrees/query-optimization-2026-07-03/examples/sandbox_harbor/`
