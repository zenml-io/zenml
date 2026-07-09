# Harbor Agent Evals with ZenML

Run [Harbor](https://www.harborframework.com/) agent-eval campaigns as ZenML pipelines, with each trial's container backed by whatever Sandbox flavor is on the active stack — powered by the `zenml.integrations.harbor` integration.

**ZenML version**: 0.96+ (Python 3.12+, required by Harbor)

```
ZenML pipeline: build_harbor_matrix -> run_harbor_shard.map(...) -> build_harbor_report
  each mapped step runs ONE campaign shard (a single-cell Harbor job):
    -> Harbor (programmatic: task loading, agent loop, verifier, reward)
      -> ZenMLSandboxEnvironment (implements harbor.BaseEnvironment)
        -> Client().active_stack.sandbox.create_session()
          -> sandbox (Modal, Kubernetes, ...)
```

ZenML owns the outer orchestration — matrix expansion, per-shard steps (own sandbox sessions, logs, retries, cache entry), and cross-shard aggregation into a campaign report. Harbor keeps the trial eval kernel. One command, one ZenML run, per-shard artifacts plus a markdown report on the dashboard.

## 🎯 What You'll Learn

- Compose the integration's reusable steps into a ~20-line campaign pipeline
- Expand local tasks and Harbor registry datasets into mapped shard steps
- Rerun a campaign and re-execute only failed shards via step caching
- Query per-shard rewards, errors, and cost from the metadata store

## 🏃 Quickstart

```bash
pip install "zenml[local]"
zenml integration install harbor modal -y

# Default campaign: tasks/hello, oracle vs nop head-to-head, 3 trials each
python run.py
```

## 📋 Prerequisites

- Python 3.12 or higher (Harbor's minimum)
- An active ZenML stack with a Modal Sandbox component registered — see the [Modal sandbox docs](https://docs.zenml.io/component-guide/sandboxes/modal):

  ```bash
  zenml sandbox register modal-sb --flavor=modal
  zenml stack register harbor-stack -o default -a default -sb modal-sb --set
  ```

- Modal credentials: `modal token new` (writes `~/.modal.toml`) or export `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`
- The sandbox image must provide `bash`, `timeout`(1), and `tar` — the bridge relies on them for command execution, timeouts, and directory transfer

## 🏗️ What's Inside

```
📁 harbor_agent_evals/
├── run.py           - The campaign pipeline + post-run receipts (report, metadata query, log restore)
├── tasks/hello/     - Hermetic smoke task: write "42", verifier scores 1.0
└── requirements.txt
```

All the machinery lives in `zenml.integrations.harbor`:

- `steps/` — `build_harbor_matrix` (campaign → shards), `run_harbor_shard` (one Harbor job per shard), `build_harbor_report` (markdown aggregation)
- `environment.py` — `ZenMLSandboxEnvironment`, Harbor's environment interface routed through the active stack's Sandbox component
- `materializers/` — persists each shard's summary plus Harbor's full job directory (agent/verifier logs, trajectories) as a tar archive
- `models.py` / `utils.py` — typed campaign contracts, stable trial identities, deterministic shard packing

## 🔑 Key Concepts

### Shards: the retry/cache unit

`build_harbor_matrix` packs the campaign into *shards* — up to `trials_per_step` trials of one (task, agent, model) cell. Each shard runs as one mapped step and one Harbor job, so a failure invalidates the narrowest possible slice of the campaign:

```python
shards = build_harbor_matrix(
    tasks=["tasks/hello"],
    agents=[{"name": "oracle"}],
    trials_per_cell=3,
    trials_per_step=1,   # 1 = one trial per step; raise to trade pod overhead for granularity
)
results = run_harbor_shard.map(shard=shards)
build_harbor_report(results=results)
```

### Caching reruns only what failed

Unlike the pre-integration example (which set `enable_cache=False`), caching is now on: rerunning an identical campaign cache-hits every shard that already completed and re-executes only failed or new shards. Pass `fail_on_trial_error=True` via `run_harbor_shard.with_options(...)` to make infra-errored shards fail (and thus rerun) instead of completing with errors recorded.

### Queryable per-shard metadata

Every shard step logs `harbor.*` metadata to the metadata store:

```python
from zenml.client import Client

flaky = Client().list_run_steps(
    pipeline_run_id="<run-id>",
    run_metadata=["harbor.n_errored:gt:0"],
)
```

### Shard artifacts carry the full Harbor job tree

```python
run = Client().get_pipeline_run("<run-id-from-stdout>")
result = run.steps["map:run_harbor_shard:0"].outputs["harbor_shard_result"][0].load()
result.trials[0].rewards          # {"reward": 1.0}
result.mean_reward                # {"reward": 1.0}
result.download_jobs_dir("logs")  # restores agent/verifier logs + trajectory
```

## 🚀 Run the Example

1. **Run the default head-to-head** (hermetic, no LLM keys): the `oracle` agent runs each task's reference solution (reward 1.0) while `nop` attempts nothing (reward 0.0), 3 trials each, packed 2 trials per shard — the report shows the contrast, a metadata query finds the losing shards, and one shard's Harbor logs are restored to `harbor_logs/`:

   ```bash
   python run.py
   ```

2. **Run a real registry benchmark.** Pass a `dataset:NAME@VERSION[:N]` spec naming a dataset from the Harbor registry (the optional `:N` slices to the first N tasks). The spec expands via Harbor's own resolver into git-pinned per-task refs (commit pins match `harbor run` exactly, nothing ships with the example); tasks that pin a prebuilt `docker_image` boot it directly on the sandbox:

   ```bash
   # Three Terminal Bench tasks — a fast real-benchmark smoke test (~2 min):
   python run.py dataset:terminal-bench-sample@2.0:3 oracle 1

   # The full 89-task Terminal Bench 2.0 (fans out 89 shard steps):
   python run.py dataset:terminal-bench@2.0 oracle 1
   ```

   The three-task run produces this report (oracle runs each task's reference solution, so green rewards validate the orchestration and environment path, not model quality):

   | Task | Agent | Trials | Succeeded | Errored | Mean reward |
   |---|---|---|---|---|---|
   | chess-best-move | oracle | 1 | 1 | 0 | reward=1.000 |
   | polyglot-c-py | oracle | 1 | 1 | 0 | reward=1.000 |
   | sqlite-with-gcov | oracle | 1 | 1 | 0 | reward=1.000 |

   The registry has 30+ benchmarks beyond Terminal Bench (quixbugs, BFCL, SWE-bench multilingual, spreadsheetbench, ...) — list them with `harbor dataset list`.

3. **Benchmark a real LLM agent.** Harbor's agents read their provider key from the *host* environment and inject it into the sandbox (`claude-code` reads `ANTHROPIC_API_KEY`, `terminus-2` reads the key matching its litellm model prefix). The model rides the agent spec:

   ```python
   # export ANTHROPIC_API_KEY=sk-ant-...   (host env — never in code or config)
   harbor_agent_evals(
       dataset={"name": "terminal-bench-sample", "version": "2.0", "n_tasks": 1},
       agents=[{"name": "claude-code", "model_name": "claude-sonnet-4-5"}],
       trials_per_cell=1,
   )
   ```

   Token usage and cost flow into the trial results, the `harbor.cost_usd` step metadata, and the report's Cost column:

   | Task | Agent | Model | Succeeded | Errored | Mean reward | Cost (USD) |
   |---|---|---|---|---|---|---|
   | chess-best-move | claude-code | claude-sonnet-4-5 | 1 | 0 | reward=0.000 | 0.1193 |

   (A real result: the oracle scores 1.000 on this task, so the harness is fine — finding the best chess move from a board image is just genuinely hard for the model.) Note that the key is visible to code running inside the sandbox, so treat sandboxed tasks as able to read it.

The pipeline prints the dashboard URL on start; the campaign report lands as a markdown artifact on the run.

## 🧪 Customization Ideas

- **Batch trials per step**: set `trials_per_step=10` in `run.py` to run 10 trials per pod via Harbor's internal concurrency (`run_harbor_shard(n_concurrent_trials=...)`)
- **Add step retries**: `run_harbor_shard.with_options(retry=StepRetryConfig(max_retries=2))` for flaky-infrastructure resilience
- **Compare agents**: pass several dicts in `agents=[...]`, each optionally with `model_name`, `kwargs`, `env`
- **Gate on errors**: `run_harbor_shard.with_options(parameters={"fail_on_trial_error": True})` so a rerun re-executes exactly the errored shards. Before failing, the step rescues the shard result and its full log archive as a manual artifact named `harbor_shard_result_<shard_id>_failed` — load it and call `download_jobs_dir()` to debug the errored trials. Without the flag, an errored shard *completes* and gets cached, so an identical rerun returns the errored result instead of retrying

## ⚠️ Known limitations

Preserved deliberately in the bridge (`zenml.integrations.harbor.environment`) rather than papered over:

- Harbor resource requests (`cpus`/`memory_mb`/`gpus`) are not translated to sandbox settings
- Tasks with `allow_internet=false` are refused (isolation can't be enforced yet)
- `exec(user=...)` is ignored — commands run as the container default user
- Task-level `docker_image` overrides are Modal-only
- Multi-step tasks and separate verifier sandboxes are rejected with `NotImplementedError`
- The Local sandbox flavor executes commands directly on the host — do not point it at untrusted Harbor tasks

## A note on `harbor run`

The bridge is a regular Harbor environment provider, so this works from any directory once the integration is installed:

```bash
harbor run --environment-import-path zenml.integrations.harbor.environment:ZenMLSandboxEnvironment ...
```

But that path skips the ZenML pipeline — no lineage, no artifacts, no report. `python run.py` is the supported entry point so the lineage story stays honest.

## 📚 Learn More

- [Harbor framework](https://www.harborframework.com/)
- [Modal Sandbox component](https://docs.zenml.io/component-guide/sandboxes/modal)
- [Dynamic pipelines & `.map`](https://docs.zenml.io/concepts/steps_and_pipelines)
- [Metadata & querying runs](https://docs.zenml.io/concepts/metadata)
