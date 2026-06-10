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

- **Run lineage.** Every trial is a ZenML pipeline run — dashboard, artifact store, replay, caching, the lot. The reward summary lands as one artifact and Harbor's full `jobs/` tree (agent/verifier logs, trajectory) as a second, tarred one, so the trial's raw output outlives the local tempdir.
- **No per-trial rebuild.** The Sandbox component owns the image. Task `[environment].docker_image` is translated to `ModalSandboxSettings(image=...)` — Modal-only today; no Dockerfile build per trial.
- **Portable substrate (in principle).** Tasks that don't pin `docker_image` only talk to the generic Sandbox interface, so swapping the flavor (Modal → GKE Agent Sandbox → …) should leave Harbor none the wiser. In practice the bridge has only been smoke-tested with the Modal flavor. **Warning:** the Local sandbox flavor executes commands directly on the host — do not point it at untrusted Harbor tasks.

## Files

- `zenml_sandbox_env.py` — `ZenMLSandboxEnvironment(harbor.BaseEnvironment)`, implements the Harbor environment methods (`start`/`stop`/`exec`/`upload_file`/`download_file`/`upload_dir`/`download_dir`). Known gaps are listed under [Open seams](#open-seams).
- `run.py` — the ZenML pipeline. Single step builds a Harbor `JobConfig` pointing at the bridge and runs it via `Job.create().run()`.
- `tasks/hello/` — a hermetic Harbor task: write `42` to `/app/answer.txt`, verifier scores 1.0 if it matches. Runs under the `oracle` agent so no LLM keys needed.
- `requirements.txt` — `harbor` + `zenml[local]`. The Modal SDK comes in via `zenml integration install modal`.

## Prereqs

Before running anything, you need an **active ZenML stack with a Modal Sandbox component registered** — see the [Modal sandbox docs](https://docs.zenml.io/component-guide/sandboxes/modal) for registration details:

```bash
zenml sandbox register modal-sb --flavor=modal
zenml stack register harbor-stack -o default -a default -sb modal-sb --set
```

Smoke-tested on:

```
orchestrator:    default
artifact_store:  s3
sandbox:         modal-sb       # Modal flavor of the Sandbox component
```

You also need **Modal credentials**: set them up via `modal token new` (writes `~/.modal.toml`) or export `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` — the Modal SDK reads them at import.

The sandbox image must provide `bash`, `timeout`(1), and `tar` — the bridge relies on them for command execution, timeouts, and directory transfer.

## Running

```bash
pip install harbor zenml[local]
zenml integration install modal

# Default task: tasks/hello, oracle agent
python run.py

# Or pass a different task / agent:
python run.py tasks/hello oracle
```

The pipeline prints the dashboard URL on start. Inspect the artifacts:

```python
from zenml.client import Client
run = Client().get_pipeline_run("<run-id-from-stdout>")
outputs = run.steps["run_harbor_trial"].outputs
result = outputs["harbor_trial_result"][0].load()
# {"job_id": "...", "n_total": 1, "n_completed": 1, "n_errored": 0, "mean_reward": 1.0}

# Gzipped tar of Harbor's jobs/ tree: agent + verifier logs, trajectory.
logs_tgz = outputs["harbor_trial_artifacts"][0].load()
open("harbor_trial_artifacts.tar.gz", "wb").write(logs_tgz)
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
8. Step returns the `JobResult` summary plus a tarball of the `jobs/` tree → saved as ZenML artifacts

## Open seams

- **`upload_dir` / `download_dir`** tar through `upload_file` / `download_file`. When the underlying Sandbox flavor grows native dir transfer this collapses to one call.
- **`timeout_sec`** is enforced inside the sandbox via coreutils `timeout` (genuine exit code 124 on expiry); the Modal session doesn't accept per-exec timeouts. Bump session-level TTL via `ModalSandboxSettings(timeout=...)` if a trial needs more than the default.
- **`user`** ignored — `SandboxSession.exec` doesn't take a user yet. Agent/verifier scripts run as the container default.
- **Resource translation** — Harbor's `task_env_config.cpus` / `memory_mb` / `gpus` don't yet flow into the active flavor's `ResourceSettings`. Add when the first GPU-flavored task comes through.

## A note on `harbor run`

The bridge implements the `BaseEnvironment` methods — with known gaps: no user switching, resource limits (`cpus`/`memory_mb`/`gpus`) are not enforced, and there is no network isolation — so technically `harbor run --environment-import-path zenml_sandbox_env:ZenMLSandboxEnvironment` works too. But that path skips the ZenML pipeline — no lineage, no artifact, ZenML invisible. We've intentionally made `python run.py` the one supported entry point so the lineage story stays honest.
