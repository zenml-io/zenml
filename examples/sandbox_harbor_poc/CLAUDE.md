# CLAUDE.md — sandbox_harbor_poc

Guidance for Claude Code when working inside this example. This is a standalone
ZenML example, not part of the `src/zenml` package.

## What this is

A ZenML pipeline that runs [Harbor](https://harborframework.org) agent
evaluations across an `agent x model` matrix. Every trial executes inside the
active stack's **Sandbox** component via a Harbor `BaseEnvironment` bridge —
not via the `harbor run` CLI and not via a Harbor env provider (Docker /
Daytona).

## Architecture

```
run.py
  -> harbor_eval_campaign  (@pipeline(dynamic=True))
       build_matrix      config YAML -> List[HarborRunSpec]
       run_harbor_job    one HarborRunSpec -> Harbor JobConfig -> Job.create().run() -> job_dir
       parse_harbor_job  job_dir -> JobSummary (dict)
       build_report      [JobSummary] -> CampaignReport + HTML report
```

`run_harbor_job` points `JobConfig.environment.import_path` at
`zenml_sandbox_env:ZenMLSandboxEnvironment`, which delegates each trial to
`Client().active_stack.sandbox.create_session()`.

## Hard rules — do not regress these

1. **No subprocess, no `harbor run`, no Daytona in `steps/run_harbor_job.py`.**
   Harbor must run programmatically via `Job.create(config)` + `job.run()`. The
   only acceptable mentions of those words are docstrings explaining what the
   step does NOT do.
2. **The bridge import path is load-bearing.** `run_harbor_job` must build
   `EnvironmentConfig(import_path="zenml_sandbox_env:ZenMLSandboxEnvironment")`.
   This is how every trial reaches the Sandbox.
3. **`zenml_sandbox_env.py` is the verified bridge.** Do not change its logic
   unless explicitly asked; docstring/comment cleanups are fine.
4. **`job_dir` must outlive the step.** Use `tempfile.mkdtemp` (not
   `TemporaryDirectory`) so ZenML's `PathMaterializer` can archive the tree
   after the step returns.
5. **Name every artifact** with `Annotated[..., "name"]` (`job_dir`,
   `job_summary`, `campaign_report`, `report`).

## Import convention

Steps and pipelines import via top-level packages (`from steps import ...`,
`from models.harbor_models import ...`, `from pipelines.harbor_eval_campaign
import ...`). The example runs with its own directory on `sys.path`, not as an
installed package. Keep imports flat — do not switch to relative imports.

## Agent model wiring

`_build_agent_config` in `steps/run_harbor_job.py` passes the LLM model via
`AgentConfig(name=..., model_name=...)` — verified against Harbor 0.8.0's
`AgentConfig` (the programmatic equivalent of the CLI's `-m` flag). The oracle
agent gets no `model_name`. If a future Harbor release renames the field, this
single helper is where to fix it.

## Verifying changes

Harbor and a live Sandbox component are not generally available in CI, so verify
statically:

```bash
# Compile everything except the task solution scripts
find . -name '*.py' -not -path './tasks/*' -print0 | xargs -0 python3 -m py_compile

# Lint
ruff check .
```

The `env_provider` field on `HarborRunSpec` and in the configs is intentionally
kept but ignored — do not "fix" it by removing it; that would break config
compatibility.
