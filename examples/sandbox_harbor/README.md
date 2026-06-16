# Harbor evals on ZenML Sandbox

Run [Harbor](https://www.harborframework.com/) evaluation trials through a ZenML pipeline, with the trial's container backed by whatever Sandbox flavor is on the active stack — Modal today, GKE Agent Sandbox / Agent Substrate when that flavor lands.

```
ZenML pipeline: build_matrix -> run_harbor_trial.map(...) -> build_report
  each mapped step runs ONE Harbor trial:
    -> Harbor (programmatic: task loading, agent loop, verifier, reward)
      -> ZenMLSandboxEnvironment (implements harbor.BaseEnvironment)
        -> Client().active_stack.sandbox.create_session()
          -> sandbox (Modal, Kubernetes, ...)
```

ZenML owns the outer orchestration — matrix expansion, per-trial steps (own
sandbox session, logs, retries, cache entry), and cross-trial aggregation into
a campaign report. Harbor keeps the trial eval kernel and runs exactly one
trial per step. One command, one ZenML run, per-trial artifacts plus a
markdown report on the dashboard.

## What you get over plain `harbor run`

- **Run lineage.** The campaign is one ZenML pipeline run and every trial is its own step — dashboard, artifact store, replay, caching, the lot. Each trial's reward summary lands as one artifact and Harbor's full `jobs/` tree (agent/verifier logs, trajectory) as a second, tarred one, so the trial's raw output outlives the local tempdir.
- **No per-trial rebuild.** The Sandbox component owns the image. Task `[environment].docker_image` is translated to `ModalSandboxSettings(image=...)` — Modal-only today; no Dockerfile build per trial.
- **Portable substrate (in principle).** Tasks that don't pin `docker_image` only talk to the generic Sandbox interface, so swapping the flavor (Modal → GKE Agent Sandbox → …) should leave Harbor none the wiser. In practice the bridge has only been smoke-tested with the Modal flavor. **Warning:** the Local sandbox flavor executes commands directly on the host — do not point it at untrusted Harbor tasks.

## Files

- `zenml_harbor_env.py` — `ZenMLSandboxEnvironment(harbor.BaseEnvironment)`, implements the Harbor environment methods (`start`/`stop`/`exec`/`upload_file`/`download_file`/`upload_dir`/`download_dir`). Known gaps are listed under [Open seams](#open-seams).
- `run.py` — the ZenML pipeline: `build_matrix` expands the campaign into per-trial parameters, `run_harbor_trial` runs one trial per mapped step (each builds a Harbor `JobConfig` pointing at the bridge and runs it via `Job.create().run()`), and `build_report` aggregates the results into a markdown report.
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

### Running a registry benchmark (Terminal Bench)

Instead of a local task directory, pass a `dataset:NAME@VERSION` spec naming
a dataset from the [Harbor registry](https://www.harborframework.com/) —
Terminal Bench, SWE-bench Verified, and friends. The spec expands into one
mapped trial step per benchmark task; each step fetches its own git-pinned
task at runtime (commit pins match `harbor run` exactly, nothing ships with
the example), and tasks that pin a prebuilt `docker_image` boot it directly:

```bash
# The 10-task Terminal Bench sample — a fast real-benchmark smoke test:
python run.py dataset:terminal-bench-sample@2.0 oracle 1

# The full 89-task Terminal Bench 2.0 (fans out 89 trial steps):
python run.py dataset:terminal-bench@2.0 oracle 1
```

The `oracle` agent runs each task's reference solution, so a registry run
needs no LLM keys — it validates the orchestration and environment path,
not model quality. Swap in a real agent (`terminus-2`, `claude-code-agent`,
...) plus its API key to benchmark a model.

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
2. Step `run_harbor_trial` builds `JobConfig(env.import_path="zenml_harbor_env:ZenMLSandboxEnvironment")`
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

The bridge implements the `BaseEnvironment` methods — with known gaps: no user switching, resource limits (`cpus`/`memory_mb`/`gpus`) are not enforced, and there is no network isolation — so technically `harbor run --environment-import-path zenml_harbor_env:ZenMLSandboxEnvironment` works too. But that path skips the ZenML pipeline — no lineage, no artifact, ZenML invisible. We've intentionally made `python run.py` the one supported entry point so the lineage story stays honest.
