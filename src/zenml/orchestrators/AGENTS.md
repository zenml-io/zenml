# ZenML Orchestrators Agent Guidelines

This file applies when Codex starts in `src/zenml/orchestrators/` or below. For
detailed examples and implementation recipes, use
`.agents/skills/zenml-repo-workflows/SKILL.md`.

## Key Files

- `base_orchestrator.py` - base class and abstract methods.
- `containerized_orchestrator.py` - base for containerized orchestrators.
- `step_launcher.py` - step-operator and isolated-step execution paths.
- `step_runner.py` - runtime step execution logic.
- `utils.py`, `cache_utils.py`, `input_utils.py`, `publish_utils.py` - shared
  orchestration helpers.

## Submission Methods

- `submit_pipeline(...)` submits static pipelines where the DAG is known.
- `submit_dynamic_pipeline(...)` submits dynamic pipelines where the DAG can
  change during execution.
- Dynamic pipeline support may also need isolated-step APIs:
  `submit_isolated_step`, `get_isolated_step_status`,
  `wait_for_isolated_step`, and `stop_isolated_step`.

`BaseOrchestrator.run(...)` already removes steps skipped by replay or
client-side caching before submission. Do not re-implement that pruning inside
integration orchestrators.

## `get_orchestrator_run_id`

This method must return a value that is:

- Unique across backend runs.
- The same for all steps in one ZenML pipeline run.
- Stable across retries of the same dynamic orchestration environment.

Do not return a fixed string or a value that changes between steps. If dynamic
pipelines are supported, handle the orchestration-container case explicitly.

Kubernetes is special because it has an orchestration container even for static
pipelines. Prefer the configured Kubernetes run ID for static runs and the
parent Kubernetes job name for dynamic runs, falling back only when needed.

## Dynamic Child Pipelines

When changing dynamic pipeline behavior, check:

- `src/zenml/execution/pipeline/dynamic/`
- `src/zenml/pipelines/dynamic/`
- `src/zenml/orchestrators/step_launcher.py`
- pipeline run models, schemas, migrations, tests, and docs.

If a child key or backend run ID changes during retry/resume, ZenML can fail to
find the existing child run and start duplicate work.
