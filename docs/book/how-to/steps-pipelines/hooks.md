---
description: Run custom code on pipeline and step lifecycle events and record hook invocations.
---

# Hooks

Hooks let you run custom code at lifecycle points of a run or a step, and record
those invocations as queryable `HookInvocation` records. The same machinery powers
the built-in lifecycle hooks ZenML fires for you and the public API you can call
from your own code. Common uses include sending notifications on success or
failure, logging run details, and triggering external workflows.

## Lifecycle hooks

Lifecycle hooks fire automatically and each fire creates one `HookInvocation`
row.

| Hook | Step scope | Pipeline scope (dynamic) |
|---|---|---|
| `on_start` | Each execution attempt, before the step body | Once before the run starts |
| `on_end` | Each execution attempt, regardless of outcome | Once when the run reaches a terminal state |
| `on_success` | Once when the step completes successfully | Once when the run completes successfully |
| `on_failure` | Once when the step fails terminally | Once when the run fails |
| `on_pause` | — | Once when the run pauses |
| `on_resume` | — | Once when a paused run resumes |

Step-level hooks fire for both static and dynamic pipelines, uniformly.

### Static pipelines propagate, dynamic pipelines fire

The same `@pipeline(on_*=...)` kwarg has two different runtime meanings depending
on whether the pipeline is dynamic.

| `@pipeline(on_*=X)` | Static pipeline | Dynamic pipeline |
|---|---|---|
| `on_start` | Propagates to each step's `on_start` default | Fires once at the pipeline level |
| `on_success` | Propagates to each step's `on_success` default | Fires once at the pipeline level |
| `on_failure` | Propagates to each step's `on_failure` default | Fires once at the pipeline level |
| `on_end` | Propagates to each step's `on_end` default | Fires once at the pipeline level |
| `on_pause` | Ignored | Fires once at the pipeline level |
| `on_resume` | Ignored | Fires once at the pipeline level |

For a static pipeline, a pipeline-level hook is a default that every step inherits
where it has not set its own. No pipeline-level hooks are run. For a dynamic
pipeline, the hook fires once at the run level and produces `RUN_*` entries. It fires
on every run, including each invocation of a deployed pipeline. Dynamic pipeline
users who want per-step defaults wire each `@step` directly.

## Registering hooks

Pass a callable or a source string to the decorator, `.configure(...)`, or
`.with_options(...)`.

```python
from zenml import step, pipeline

def notify_start():
    print("starting")

def notify_end(exception=None):
    print("finished")

@step(on_start=notify_start, on_end=notify_end)
def my_step() -> int:
    return 42

@pipeline(on_start=notify_start, on_end=notify_end)
def my_pipeline():
    my_step()

# Override at configuration time
my_step = my_step.with_options(on_failure="my_module.alert_on_failure")
```

### Hook signatures

`on_start`, `on_success`, `on_pause` and `on_resume` take no arguments.
`on_failure` and `on_end` optionally take a single `BaseException` argument.

```python
from typing import Optional

def on_end(): ...
def on_end(exception: Optional[BaseException] = None): ...
```

`exception` is set only when the attempt or run failed. Details about the
current step or run are available through the step or run context (see
below).

### Accessing step/run information in hooks

Step-scope hooks read the current step run and pipeline run through the step
context. Run-scope hooks on a dynamic pipeline fire outside any step and read
the run from the run context instead, via
`DynamicPipelineRunContext.get().run`.

```python
from zenml import get_step_context, step

def on_failure(exception: BaseException):
    context = get_step_context()
    print(f"Failed step: {context.step_run.name}")

@step(on_failure=on_failure)
def my_step(some_parameter: int = 1):
    raise ValueError("My exception")
```

### Sending alerts from hooks

Use the [Alerter stack component](https://docs.zenml.io/component-guide/alerters)
to send notifications when a step or run fails or succeeds.

```python
from zenml import get_step_context
from zenml.client import Client

def on_failure():
    step_name = get_step_context().step_run.name
    Client().active_stack.alerter.post(f"{step_name} just failed!")
```

ZenML ships built-in alerter hooks for the common case.

```python
from zenml.hooks import alerter_success_hook, alerter_failure_hook

@step(on_failure=alerter_failure_hook, on_success=alerter_success_hook)
def my_step():
    ...
```

## Behavior notes

* **Retries.** A retried step fires one `on_start` / `on_end` pair per attempt.
  `on_success` and `on_failure` fire exactly once, at the terminal outcome.
* **Cache hits.** A cached step fires no step-level hooks. Pipeline-level hooks on
  a dynamic run still fire even when every step was cached.
* **Hook failures are swallowed.** When a lifecycle hook raises, the run or step is
  not aborted. The exception is captured into the `HookInvocation` record with
  `status=FAILED` and execution proceeds.
* **Async hooks.** Hook functions can be defined with `async def`. When the hook
  fires, ZenML runs the coroutine to completion and blocks until it finishes.
* **Return values are discarded.** Set `ZENML_TRACK_LIFECYCLE_HOOK_OUTPUTS=true`
  in the execution environment to instead materialize lifecycle hook return
  values as output artifacts of the invocation, following the same rules as
  `store_return=True` on `run_hook` (see below).

## Init and cleanup hooks

`on_init` and `on_cleanup` are pipeline setup and teardown hooks. They initialize
and tear down shared run state rather than reacting to a single run or step
outcome, so they follow different rules from the lifecycle hooks above. They are
**not** recorded as `HookInvocation` records. When `on_init` fails, the run still
records `RUN_START`, `RUN_END`, and `RUN_FAILURE`, but never a row for `on_init`
itself. Find the root cause on `pipeline_run.exception_info`.

ZenML runs `on_init` **once per execution environment**, before any step body runs
in that environment, and `on_cleanup` once when that environment is torn down.
Where that lands depends on how the pipeline runs.

### Deployments

`on_init` runs once per deployment replica when the replica starts, and
`on_cleanup` once when it shuts down. Individual invocations of the deployed
pipeline reuse the initialized state and do not re-run either hook. Lifecycle
hooks like `on_start` and `on_end` still fire on every invocation.

### Regular runs

For a run that is not a deployment, `on_init` runs once per execution environment:

* **Dynamic pipeline:** once in the orchestrator environment, where the pipeline
  function executes.
* **Any step that runs outside the orchestration environment (static or
  dynamic):** once ahead of that step body, the first time its environment is
  used. A step that shares the orchestration environment skips the hook, because
  the run context is already initialized there.

## Recording custom invocations

Beyond the built-in lifecycle hooks, you can record arbitrary invocations from
inside a step or a dynamic pipeline function. This is useful for instrumenting
third-party callbacks such as the tool and model calls of an agent framework.

### `run_hook`

Call `run_hook(func, ...)` to run a function and record the invocation in one call.
The return value flows through to you.

```python
from zenml import run_hook, step

def call_tool(name: str) -> str:
    return f"result of {name}"

@step
def agent_step():
    # Records one CUSTOM HookInvocation, returns the function's result.
    result = run_hook(call_tool, "search")
```

Pass `store_return=True` to materialize the return value as an output artifact. A
single unannotated return becomes one artifact named `output`. An annotated tuple
return unpacks into one artifact per element.

```python
result = run_hook(call_tool, "search", store_return=True)
```

## Querying hook invocations

List the invocations recorded for a run through the client.

```python
from zenml.client import Client
from zenml.enums import HookType

invocations = Client().list_hook_invocations(
    pipeline_run_id=run.id,
    hook_type=HookType.CUSTOM,
)
for invocation in invocations.items:
    print(invocation.name, invocation.status)
```
