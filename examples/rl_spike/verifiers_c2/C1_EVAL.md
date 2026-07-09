# C1 — verifiers environment eval as a mapped ZenML campaign

Task C1 from `../framework_breakout.md` (Track C), 2026-07-09, on branch
`spike/c1-verifiers-eval`. The question: verifiers already owns rollout,
parsing, and rubric scoring (C2 proved the rubric-opens-a-ZenML-Sandbox path
composes), so does wrapping `env.evaluate(...)` in a ZenML pipeline add
anything the bare `vf-eval` CLI doesn't?

## Verdict: the wrapping earns its keep — but only for *campaigns*, not single evals

For a one-off "how good is model X on this env" question, `vf-eval` is
strictly less friction: no shard step, no materializer story, no zenml
context. The pipeline version starts paying off exactly where the CLI stops:

1. **Versioned, comparable eval artifacts across models.** The two headline
   runs (gpt-5-mini `d30d6da8`, gpt-5-nano `c04577b1`, same 10-task mix)
   live on the staging server as first-class runs with identical structure:
   per-shard rollout datasets (prompt, completion, reward, error columns),
   token/wall-clock metadata on every shard step, and a rendered markdown
   report artifact. "nano drops to 0.94 because `word_ladder` fails with
   `pipeline exited nonzero`" is answerable from the dashboard alone;
   `vf-eval` gives you local JSONL files and your own bookkeeping.
2. **The report artifact is real.** `MarkdownString` renders in the run page
   — mean reward, per-task ladder, and the infra-vs-scorer error split
   (entry-16 hygiene) in one place, next to the lineage graph.
3. **Mapped shards actually parallelize and would actually retry.** On the
   local orchestrator the two shard steps overlapped (21.3s + 23.8s wall
   but 38.8s total run), and each shard is a separate step that a retry
   config or re-run could recover independently — with per-shard artifacts
   surviving. `vf-eval` restarts are all-or-nothing (it does have its own
   resume, but per-shard fan-out across nodes it does not).

The honest qualifier: at this scale (10 tasks, hosted API) none of that is
*necessary* — the pipeline's value is the campaign shape (many models ×
many shards × history on a server), not the single eval. "ZenML adds
nothing" would have been the verdict for the single-eval case; for the
model-comparison case the artifacts genuinely beat the CLI.

## The sub-questions, answered

**(a) Does `asyncio.run` inside a step behave?** Yes — `env.evaluate` is
async by design and `asyncio.run` inside the mapped step worked unmodified,
including the rubric's own `asyncio.to_thread` + semaphore machinery from
C2 (nested: step thread → asyncio loop → scoring threads → sandbox
sessions). What does NOT behave is verifiers *environment construction*
off the main thread — see finding 2 below.

**(b) Is the HF-datasets materializer story clean?** No — two independent
walls, both worth knowing:

- ZenML's huggingface integration pins `datasets>=2.16.0,<4.0.0`;
  verifiers 0.1.14 requires `datasets` 4.x (4.6.1 here). So the proper
  `HFDatasetMaterializer` **cannot activate in a verifiers venv at all** —
  it's a version-cap conflict, not a missing install. The artifact falls
  back to `CloudpickleMaterializer`, which works but warns on load about
  Python-version fragility (and would genuinely break loading a 3.11
  pickle from a 3.12 consumer).
- Even before ZenML sees anything, Arrow's one-schema-per-column rule
  fights this workload twice: the env dataset crashed `Dataset.from_list`
  because task specs are heterogeneous (`expected_output.value` is int `7`
  in one task, str `'hello zenml'` in another), and verifiers' own
  `env.make_dataset(results)` crashed on its own `evaluate` outputs
  (prompt columns still hold pydantic `Message` objects). Both fixed the
  same way: nested/varying structures ride as JSON-string columns
  (`spec_json`, `prompt_json`, ...), scalars stay native.

**(c) What do you get over `vf-eval`?** See the verdict above. Concretely
delivered by this pipeline: per-shard rollout datasets + token/timing
metadata + a dashboard-rendered report + cross-model run history on the
server, for ~180 lines of pipeline code on top of the C2 environment.

## Findings beyond the sub-questions (BREAKAGE_LOG-grade candidates)

These live here per the batch rules (spike branch; shared docs updated
only after go-ahead):

1. **`datasets<4.0.0` cap blocks the HF materializer for the current RL
   ecosystem.** verifiers (and increasingly the HF RL stack) is on
   datasets 4.x; ZenML's huggingface integration caps at <4. Any user
   returning an HF Dataset from a step in such a venv silently gets
   cloudpickle + a load-time warning. Core question: bump the cap or ship
   a standalone datasets materializer.
2. **verifiers environments cannot be constructed off the main thread —
   and ZenML runs mapped dynamic steps in worker threads.**
   `Environment.__post_init__` (v0.1.14, `envs/environment.py`)
   unconditionally calls `signal.signal(...)` for SIGINT/SIGTERM teardown
   ("safer sandbox lifecycle", the C2 finding's other half); Python only
   allows that in the main thread, so `load_environment()` inside a mapped
   step dies with "signal only works in main thread of the main
   interpreter". Workaround in `c1_eval_pipeline.py`
   (`tolerate_non_main_thread`): no-op `signal.signal` during env
   construction off-main-thread — safe inside a step, where ZenML owns
   process lifecycle and sessions are context-managed. This is an
   ecosystem collision every "run framework X inside a ZenML step" user
   will hit if X installs signal handlers.
3. **The entry-16 ambiguity is one refactor away, always.** C2's rubric
   caught its own exceptions and recorded `state["infra_error"]` — but the
   completion-parsing call sat one line *above* the `try:`, so when the
   live rollout path delivered pydantic `Message` objects instead of dicts
   (shape C2's canned states never exercised), verifiers swallowed the
   crash into a bare reward 0.0 with no error recorded. Ten plausible
   completions scored 0.0 with empty scorer results and nothing flagged.
   The fix is trivial (hoist everything into the `try`); the lesson is
   structural: in verifiers, *any* uncaught line in a reward function
   silently becomes "the model failed".
4. **Prime Intellect is the default at every layer of verifiers, third
   sighting.** `ClientConfig` defaults to `api_key_var="PRIME_API_KEY"`
   and `api_base_url="https://api.pinference.ai/api/v1"` (C2 found the
   same hardcoding in both sandbox layers). A raw `AsyncOpenAI` client is
   rejected ("Unsupported client type") — you must pass a `ClientConfig`,
   which is at least a serializable pydantic model and therefore a
   step-parameter-friendly shape.
5. **Plain-string `task` columns are rejected by the 0.1.14 rollout
   path** ("use info['env_id'] for routing") — v1-schema seepage into the
   0.x env API; the env dataset had to drop the informational `task`
   label. Symptom of the pin-and-expect-movement discipline the breakout
   doc mandates for this ecosystem.
6. **Repo-scoped zenml context has two sharp edges in worktrees.**
   (i) Before the worktree's own `zenml init` exists, `zenml project set`
   / `stack set` walk *up* past `.worktrees/` and silently mutate the main
   checkout's `.zen`. (ii) A process isolated via `ZENML_CONFIG_PATH`
   (compare_rewards.py) still *shares* the repo `.zen` — when its
   throwaway store lacks the repo's active project, the client "helpfully"
   resets the repo-scoped active project/stack to `default`, a mutation
   that outlives the isolated process. Both bit this thread within one
   session.

## The runs (staging, project `rl-spike`, stack `rl-spike-local`)

| run | model | tasks | result |
|---|---|---|---|
| `5aefe8ea` | gpt-5-mini | first 10 (easy prefix) | mean 1.00 — machinery proof |
| `d30d6da8` | gpt-5-mini | 10-task mix incl. OOD (`fake_triple`, `crossed_reports`, `mixed_signs`, ...) | mean 1.00 — mini clears the anti-prior tasks the spike built for Qwen3-4B |
| `c04577b1` | gpt-5-nano | same mix | mean 0.94 — `word_ladder` 0.40, scorer error `pipeline exited nonzero` visible end-to-end |

Cost: ~1k tokens/task on gpt-5-mini — the whole campaign set was cents.

## Layout

- `c1_eval_pipeline.py` — the campaign: `make_shards` →
  `eval_shard.map(...)` (each shard: build env → `asyncio.run(env.
  evaluate(...))` against the hosted model → flat Arrow-safe rollout
  Dataset) → `aggregate_report` (MarkdownString). CLI flags: `--model`,
  `--num-tasks`, `--num-shards`, `--rollouts-per-example`, `--task-ids`.
- `zenml_pipeline_env.py` gained: `task_ids` selection for sharding,
  JSON-encoded specs in `info` (Arrow schema), pydantic-Message handling
  in `completion_text`, and the whole reward body inside the `try`
  (finding 3). C2's `compare_rewards.py` re-verified 18/18 after these
  changes.

## Setup / run

Same venv recipe as C2 (see README) **plus** `zenml integration install
s3 --uv -y` (the staging stack's artifact store), then, from this dir
(zenml context: `zenml init` + `zenml project set rl-spike` + `zenml
stack set rl-spike-local` run inside `examples/rl_spike/`):

```bash
OPENAI_API_KEY=... .venv/bin/python c1_eval_pipeline.py \
    --model gpt-5-mini --num-tasks 10 --num-shards 2
```
