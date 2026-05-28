# Harbor evals on ZenML Sandbox

Run [Harbor](https://harborframework.org) evaluation trials through a ZenML pipeline, with the trial's container backed by whatever Sandbox flavor is on the active stack — Modal today, GKE Agent Sandbox / Agent Substrate when that flavor lands.

```
ZenML pipeline (single step, the user's entry point)
  -> Harbor (programmatic: tasks, agent, verifier, ATIF, reward)
    -> ZenMLSandboxEnvironment (implements harbor.BaseEnvironment)
      -> Client().active_stack.sandbox.create_session()
        -> Modal sandbox
```

The pipeline is the only entry point. One command, one ZenML run, one queryable artifact carrying the trial's reward and metadata.

## What you get over plain `harbor run`

- **Run lineage.** Every trial is a ZenML pipeline run — dashboard, artifact store, replay, caching, the lot. Yurii's two complaints (not traceable, not reproducible) close at the pipeline layer.
- **No per-trial rebuild.** The Sandbox component owns the image. Task `[environment].docker_image` flows through to the underlying flavor's `base_image`; no Dockerfile build per trial.
- **Portable substrate.** Swap the Sandbox flavor (Modal → GKE Agent Sandbox → …) and Harbor sees nothing change. Same bridge, same task assets.

## Files

- `zenml_sandbox_env.py` — `ZenMLSandboxEnvironment(harbor.BaseEnvironment)`. ~290 LOC, implements the full Harbor environment contract (`start`/`stop`/`exec`/`upload_file`/`download_file`/`upload_dir`/`download_dir`).
- `run.py` — the ZenML pipeline. Single step builds a Harbor `JobConfig` pointing at the bridge and runs it via `Job.create().run()`.
- `tasks/hello/` — a hermetic Harbor task: write `42` to `/app/answer.txt`, verifier scores 1.0 if it matches. Runs under the `oracle` agent so no LLM keys needed.
- `requirements.txt` — `harbor` + `zenml[local]`. The Modal SDK comes in via `zenml integration install modal`.

## Prereqs

A ZenML stack with a Sandbox component. Smoke-tested on:

```
orchestrator:    default
artifact_store:  s3
sandbox:         modal-sb       # Modal flavor of the Sandbox component
```

Set up Modal credentials via `modal token new` (writes `~/.modal.toml`) or export `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` — the Modal SDK reads them at import.

## Running

```bash
pip install harbor zenml[local]
zenml integration install modal

# Default task: tasks/hello, oracle agent
python run.py

# Or pass a different task / agent:
python run.py tasks/hello oracle
```

The pipeline prints the dashboard URL on start. Inspect the artifact:

```python
from zenml.client import Client
run = Client().get_pipeline_run("<run-id-from-stdout>")
result = run.steps["run_harbor_trial"].outputs["harbor_trial_result"][0].load()
# {"job_id": "...", "n_total": 1, "n_completed": 1, "n_errored": 0, "mean_reward": 1.0}
```

## Smoke results

End-to-end wall clock on the default task: **~15s**, reward `1.0`. Full chain:

1. Pipeline run created on the active stack
2. Step `run_harbor_trial` builds `JobConfig(env.import_path="zenml_sandbox_env:ZenMLSandboxEnvironment")`
3. `Job.create(config)` → `job.run()` spawns 1 trial
4. Bridge opens a Modal Sandbox session via `Client().active_stack.sandbox.create_session()`
5. Oracle agent uploads `solve.sh` → execs → writes `/app/answer.txt`
6. Bash verifier reads the file → `reward = 1.0`
7. Bridge destroys the Modal session, returns `ExecResult`s to Harbor
8. Step returns the `JobResult` summary → saved as ZenML artifact

## Open seams

- **`upload_dir` / `download_dir`** tar through `upload_file` / `download_file`. When the underlying Sandbox flavor grows native dir transfer this collapses to one call.
- **`timeout_sec`** is enforced host-side via `asyncio.wait_for`; the Modal session doesn't accept per-exec timeouts. Bump session-level TTL via `ModalSandboxSettings(timeout_seconds=...)` if a trial needs more than the default.
- **`user`** ignored — `SandboxSession.exec` doesn't take a user yet. Agent/verifier scripts run as the container default.
- **Resource translation** — Harbor's `task_env_config.cpus` / `memory_mb` / `gpus` don't yet flow into the active flavor's `ResourceSettings`. Add when the first GPU-flavored task comes through.

## A note on `harbor run`

The bridge implements the full `BaseEnvironment` contract, so technically `harbor run --environment-import-path zenml_sandbox_env:ZenMLSandboxEnvironment` works too. But that path skips the ZenML pipeline — no lineage, no artifact, ZenML invisible. We've intentionally made `python run.py` the one supported entry point so the lineage story stays honest.
