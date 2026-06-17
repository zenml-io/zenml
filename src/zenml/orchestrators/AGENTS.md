# ZenML Orchestrators — Agent Guidelines

Guidance for agents implementing or modifying ZenML orchestrators.

## Key Files

| File | Purpose |
|------|---------|
| `base_orchestrator.py` | Base class with abstract methods to implement |
| `containerized_orchestrator.py` | Base for orchestrators that run steps in containers |
| `utils.py` | Shared orchestrator utilities |
| `step_launcher.py` | Step execution launcher, including step-operator and isolated-step paths |
| `step_runner.py` | Runtime step execution logic |
| `cache_utils.py`, `input_utils.py`, `publish_utils.py` | Shared cache/input/status and metadata helpers |

## Methods to Implement

When implementing a custom orchestrator, there are two main submission methods:

### 1. `submit_pipeline` (line ~188)

For **static pipelines** where the DAG is known at submission time.

```python
def submit_pipeline(
    self,
    snapshot: "PipelineSnapshotResponse",
    stack: "Stack",
    base_environment: Dict[str, str],
    step_environments: Dict[str, Dict[str, str]],
    placeholder_run: Optional["PipelineRunResponse"] = None,
) -> Optional[SubmissionResult]:
    """Submit the pipeline to your orchestration backend."""
```

### 2. `submit_dynamic_pipeline` (line ~218)

For **dynamic pipelines** where the DAG can change during execution.

```python
def submit_dynamic_pipeline(
    self,
    snapshot: "PipelineSnapshotResponse",
    stack: "Stack",
    environment: Dict[str, str],
    placeholder_run: Optional["PipelineRunResponse"] = None,
) -> Optional[SubmissionResult]:
    """Submit a dynamic pipeline to your orchestration backend."""
```

Both methods ask you to submit the pipeline to your orchestration backend (e.g., starting a job in Vertex, starting a pipeline in SageMaker).

### 3. Isolated-Step APIs (for dynamic pipelines)

When implementing dynamic pipeline support, orchestrators can also override these methods to manage individual step execution:

- `submit_isolated_step(...)` — Submit a single step as an isolated job
- `get_isolated_step_status(...)` — Check the status of a submitted step
- `wait_for_isolated_step(...)` — Block until a step completes
- `stop_isolated_step(...)` — Cancel a running step

These are used by the `StepLauncher` when running steps via step operators or in dynamic pipeline contexts. See the Kubernetes orchestrator for a reference implementation.

### Replay/Cache-Aware Snapshots

`BaseOrchestrator.run(...)` now prunes the pipeline snapshot before submission: steps skipped by replay or resolved by client-side caching are removed before your `submit_pipeline`/`submit_dynamic_pipeline` method is called. Do not re-implement replay or caching pruning inside integration orchestrators.

---

### Nested Child Pipelines

Dynamic pipelines can now call other dynamic pipelines as child pipelines. A child pipeline may create its own pipeline run with `parent_run_id`, `child_key`, and `root_run_id` links back to the parent run. Inline child pipelines execute their steps inside the parent run instead.

When changing dynamic pipeline or orchestrator behavior, check the full chain:
- Dynamic execution: `src/zenml/execution/pipeline/dynamic/`
- Dynamic pipeline public API: `src/zenml/pipelines/dynamic/`
- Parent/child run models and schemas: `PipelineRun*` models, `pipeline_run_schemas.py`, and migrations
- Step launching: `src/zenml/orchestrators/step_launcher.py`
- Tests: `tests/unit/execution/pipeline/dynamic/test_child_pipelines.py`
- Docs: `docs/book/how-to/steps-pipelines/dynamic_pipelines.md`

Concrete failure story: the parent dynamic run launches a child pipeline, then resumes or retries. If the child key or orchestration run ID changes unexpectedly, ZenML can fail to find the existing child run and may start duplicate work. Keep child identifiers stable across replay/resume/retry paths.

---

## ⚠️ The Tricky Method: `get_orchestrator_run_id`

**Location:** `base_orchestrator.py:173`

This is where most implementers get confused, despite the docstring documentation.

```python
@abstractmethod
def get_orchestrator_run_id(self) -> str:
    """Returns the run id of the active orchestrator run.

    Important: This needs to be a unique ID and return the same value for
    all steps of a pipeline run.
    """
```

### Static Pipeline Case

**Key requirements:**
1. Must return the **same value** for all steps in a pipeline run
2. Must be **unique across runs** (can't return a fixed string)

**Why this is tricky:**
- In static pipelines, there's typically no orchestration container that gets spun up first
- For orchestrators like SageMaker, execution immediately starts with the first step
- No step knows in advance what the ZenML pipeline run ID is supposed to be (the run doesn't exist yet when steps start)
- The `get_orchestrator_run_id` allows the first step to create the run, and all downstream steps to find it

**How to get the ID:**
- Most orchestration backends expose a run ID as an environment variable
- Example: SageMaker has `TRAINING_JOB_ARN` or reads from `/opt/ml/config/processingjobconfig.json`
- This ID is unique for each run of the backend pipeline

**Size constraints:** Limited to ~250 characters due to MySQL database column limit, but any ID from orchestration backends should fit.

### Dynamic Pipeline Case

**Key differences:**
- There's always one initial container that gets spun up first: the "orchestration container"
- This container creates the pipeline run
- The ID needs to be unique for the orchestration environment and stable for retries of that same orchestration environment
- It does NOT need to be unique across all step containers that get spun up later

**What to use:**
- **Kubernetes:** Prefer the parent Kubernetes job name for the orchestration pod; fall back to the pod name only if the job lookup fails
- **SageMaker:** The job ID of the orchestration container

### Orchestration Exception: Kubernetes

Kubernetes is special because it **does** spin up an orchestration container first, even for static pipelines. This means:
- The Kubernetes orchestrator first checks for `ENV_ZENML_KUBERNETES_RUN_ID` (set for static pipelines)
- For dynamic pipelines, it tries to use the parent Kubernetes job name so retries of the orchestration pod resolve to the same run ID
- It falls back to `socket.gethostname()` only if the job-name lookup fails

---

## Reference Implementations

Study these implementations when building your own orchestrator:

### Kubernetes (recommended starting point)
**File:** `src/zenml/integrations/kubernetes/orchestrators/kubernetes_orchestrator.py:1080`

```python
def get_orchestrator_run_id(self) -> str:
    try:
        return os.environ[ENV_ZENML_KUBERNETES_RUN_ID]
    except KeyError:
        # Dynamic pipeline: use parent job name for retry stability,
        # falling back to pod name if the lookup fails.
        pod_name = socket.gethostname()
        return get_parent_job_name(...) or pod_name
```

### SageMaker (complex example)
**File:** `src/zenml/integrations/aws/orchestrators/sagemaker_orchestrator.py:270`

```python
def get_orchestrator_run_id(self) -> str:
    # Check multiple environment variables
    for env in [ENV_ZENML_SAGEMAKER_RUN_ID, "TRAINING_JOB_ARN"]:
        if env in os.environ:
            return os.environ[env]
    
    # Fall back to processing job config file
    config_file_path = "/opt/ml/config/processingjobconfig.json"
    if os.path.exists(config_file_path):
        with open(config_file_path, "r") as f:
            # Read job name from config...
```

### Vertex AI
**File:** `src/zenml/integrations/gcp/orchestrators/vertex_orchestrator.py:1004`

```python
def get_orchestrator_run_id(self) -> str:
    try:
        return os.environ[ENV_ZENML_VERTEX_RUN_ID]
    except KeyError:
        raise RuntimeError(
            f"Unable to read run id from environment variable {ENV_ZENML_VERTEX_RUN_ID}."
        )
```

---

## Implementation Checklist

When implementing a new orchestrator:

- [ ] Inherit from `ContainerizedOrchestrator` if your orchestrator runs steps in containers
- [ ] Implement `get_orchestrator_run_id()` following the static/dynamic patterns above
- [ ] Implement `submit_pipeline()` for static pipelines
- [ ] Optionally implement `submit_dynamic_pipeline()` for dynamic pipeline support
- [ ] Optionally implement `submit_isolated_step()` / `get_isolated_step_status()` / `wait_for_isolated_step()` for dynamic pipelines with step operators
- [ ] Handle scheduling if your backend supports it (see `update_schedule`/`delete_schedule` hooks)
- [ ] Handle resource settings from step configurations appropriately (CPU, memory, GPU, etc.)
- [ ] Return `SubmissionResult` with `wait_for_completion` for synchronous execution
- [ ] Use `self.get_image(deployment, step_name)` to get the Docker image for each step
- [ ] Use `orchestrator_utils.get_step_entrypoint_command(...)` for step container commands, so command steps can override the default ZenML step entrypoint

## Common Pitfalls

1. **Returning a non-unique ID**: Don't return a fixed string or timestamp that could collide across runs
2. **Different IDs for different steps**: All steps in a run MUST get the same ID
3. **Forgetting the dynamic case**: If you support dynamic pipelines, handle the fallback
4. **Not setting environment variables**: The entrypoint needs your run ID to be discoverable

## Additional Resources

- Custom orchestrator documentation: `docs/book/component-guide/orchestrators/custom.md`
