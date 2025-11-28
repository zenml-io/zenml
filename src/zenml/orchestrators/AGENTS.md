# ZenML Orchestrators — Agent Guidelines

Guidance for agents implementing or modifying ZenML orchestrators.

## Key Files

| File | Purpose |
|------|---------|
| `base_orchestrator.py` | Base class with abstract methods to implement |
| `containerized_orchestrator.py` | Base for orchestrators that run steps in containers |
| `utils.py` | Shared orchestrator utilities |

## Methods to Implement

When implementing a custom orchestrator, there are two main submission methods:

### 1. `submit_pipeline` (line ~179)

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

### 2. `submit_dynamic_pipeline` (line ~209)

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

---

## ⚠️ The Tricky Method: `get_orchestrator_run_id`

**Location:** `base_orchestrator.py:169`

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
- The ID only needs to be unique when running **inside the orchestration container**
- Does NOT need to be unique across all step containers that get spun up later

**What to use:**
- **Kubernetes:** The pod name (`socket.gethostname()`) — it's unique per container
- **SageMaker:** The job ID of the orchestration container

### Orchestration Exception: Kubernetes

Kubernetes is special because it **does** spin up an orchestration container first, even for static pipelines. This means:
- The Kubernetes orchestrator can use the pod name as the run ID
- It first checks for `ENV_ZENML_KUBERNETES_RUN_ID` (set for static pipelines)
- Falls back to `socket.gethostname()` for dynamic pipelines

---

## Reference Implementations

Study these implementations when building your own orchestrator:

### Kubernetes (recommended starting point)
**File:** `src/zenml/integrations/kubernetes/orchestrators/kubernetes_orchestrator.py:961`

```python
def get_orchestrator_run_id(self) -> str:
    try:
        return os.environ[ENV_ZENML_KUBERNETES_RUN_ID]
    except KeyError:
        # Dynamic pipeline: use pod name
        return socket.gethostname()
```

### SageMaker (complex example)
**File:** `src/zenml/integrations/aws/orchestrators/sagemaker_orchestrator.py:258`

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
**File:** `src/zenml/integrations/gcp/orchestrators/vertex_orchestrator.py:785`

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
- [ ] Handle `snapshot.schedule` if your backend supports scheduling
- [ ] Handle resource settings from step configurations appropriately (CPU, memory, GPU, etc.)
- [ ] Return `SubmissionResult` with `wait_for_completion` for synchronous execution
- [ ] Use `self.get_image(deployment, step_name)` to get the Docker image for each step
- [ ] Use `StepEntrypointConfiguration.get_entrypoint_command/arguments()` for container commands

## Common Pitfalls

1. **Returning a non-unique ID**: Don't return a fixed string or timestamp that could collide across runs
2. **Different IDs for different steps**: All steps in a run MUST get the same ID
3. **Forgetting the dynamic case**: If you support dynamic pipelines, handle the fallback
4. **Not setting environment variables**: The entrypoint needs your run ID to be discoverable

## Additional Resources

- Custom orchestrator documentation: `docs/book/component-guide/orchestrators/custom.md`
