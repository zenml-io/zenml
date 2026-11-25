---
description: Pause a dynamic pipeline for external input and resume it after the input is resolved.
icon: hourglass-half
---

# Wait for external input and resume a run

Use `zenml.wait(...)` when a dynamic pipeline needs a human or external system to provide input before it can continue.

{% hint style="info" %}
`zenml.wait(...)` only works inside [dynamic pipelines](./dynamic_pipelines.md). It does not work in static pipelines or inside a step.
{% endhint %}

## Basic pattern

When the pipeline reaches `wait(...)`, ZenML creates a wait condition and pauses the run. Once the condition is resolved, the pipeline continues from that point.

```python
from zenml import pipeline, step, wait


@step
def prepare_candidate() -> str:
    """Prepare the candidate that may be released."""
    return "model:v17"


@step
def register_release(candidate: str, release_tag: str) -> None:
    """Register the release tag chosen for the candidate."""
    print(f"Registering {candidate} as {release_tag}")


@pipeline(dynamic=True)
def release_pipeline() -> None:
    """Pause until an external system provides a release tag."""
    candidate = prepare_candidate()
    release_tag = wait(
        schema=str,
        question="Provide the release tag for this candidate.",
    )
    register_release(candidate=candidate, release_tag=release_tag)
```

## Data schemas

The `schema=` argument defines the shape of the value that must be returned when the wait condition is answered.
You can use primitive types such as:

- `str`
- `int`
- `float`
- `bool`
- `list`
- `dict`

You can also use Pydantic objects for structured input:

```python
from pydantic import BaseModel
from zenml import pipeline, wait


class DeploymentConfig(BaseModel):
    """Structured deployment input returned to the waiting run."""

    environment: str
    replicas: int
    notify_slack: bool


@pipeline(dynamic=True)
def deployment_pipeline() -> None:
    """Pause until a structured deployment configuration is provided."""
    config = wait(
        schema=DeploymentConfig,
        question="Provide the deployment configuration for this run.",
    )
    print(config.environment, config.replicas, config.notify_slack)
```

## Agentic approval workflow

`wait(...)` is useful when an agentic workflow should prepare a recommendation
but a human should approve the final action. The example below plans multiple
agent tasks, runs them with dynamic mapping, summarizes the results, and then
continues only if the approval wait condition resolves to `true`.

```python
from zenml import pipeline, step, wait


@step
def plan_agent_tasks(goal: str) -> list[dict[str, str]]:
    return [
        {"task_id": "research", "instruction": f"Research {goal}"},
        {"task_id": "draft", "instruction": f"Draft a plan for {goal}"},
        {"task_id": "risk_check", "instruction": f"Review risks for {goal}"},
    ]


@step
def execute_agent_task(task: dict[str, str]) -> dict[str, str]:
    return {"task_id": task["task_id"], "result": "completed"}


@step
def summarize_agent_work(results: list[dict[str, str]]) -> list[dict[str, str]]:
    return results


@step
def take_final_action(summary: list[dict[str, str]]) -> None:
    print(f"Acting on {len(summary)} reviewed tasks.")


@pipeline(dynamic=True)
def agentic_approval_pipeline(goal: str) -> None:
    tasks = plan_agent_tasks(goal=goal)
    results = execute_agent_task.map(task=tasks)
    summary = summarize_agent_work(results)
    approved = wait(
        schema=bool,
        question="Approve the agent recommendation and continue?",
        metadata={"goal": goal},
        name="human_approval",
    )

    if approved:
        take_final_action(summary)
```

For a runnable version that also logs metadata and returns tabular artifacts,
see the
[`agentic_hitl_pipeline` example](https://github.com/zenml-io/zenml/tree/main/examples/agentic_hitl_pipeline).

## Timeouts and pausing

`wait(...)` accepts a `timeout` (default: 600 seconds). When the timeout
elapses without a resolution, ZenML transitions the run to `PAUSED` so the
orchestration process can be torn down — picking it back up later via
[resume](#resolve-and-resume).

There is one subtlety to know about for nested or concurrent dynamic
pipelines: the run only pauses once all *tree-wide* work has settled.

- A run with concurrent steps (`step.submit(...)`), maps
  (`step.map(...)`), or child pipelines (`child(...)`,
  `child.submit(...)`) keeps the orchestration process up so it can
  monitor that work.
- While that process is up anyway, pausing the run wouldn't free any
  resources — the wait keeps polling and refreshing its lease even past
  `timeout`.
- Once the tree quiesces (concurrent steps and child runs have all
  finished, or themselves paused), the wait gives up and publishes
  `PAUSED`.

In other words, `timeout` is the earliest moment the run can pause, not
a hard upper bound on how long the wait blocks. For a run with no
concurrent or nested work it behaves as the simple bound it appears to
be. For richer pipelines, treat it as a "stop polling once everything
else is also idle" hint.

If you want the run to pause as soon as the timeout elapses regardless of
sibling work, design the pipeline so the `wait(...)` call is the only
in-flight work at that point — for example, by `.wait()`-ing on the
relevant futures before calling `wait(...)`.

## Resolve and resume

You can resolve wait conditions either in the UI or from the CLI.

To review and resolve the pending wait conditions for a specific run interactively, use:
```bash
zenml pipeline runs wait-conditions resolve --run <RUN_ID_OR_NAME> --interactive
```

If you want to resolve a condition non-interactively, pass the result as JSON:

```bash
zenml pipeline runs wait-conditions resolve <WAIT_CONDITION_ID> \
  --resolution continue \
  --result '{"environment": "production", "replicas": 3, "notify_slack": true}'
```

In ZenML Pro, the run should start resuming automatically after the wait condition is resolved. If it remains paused, or if you are using OSS, resume it manually:

```bash
zenml pipeline runs resume <RUN_ID_OR_NAME>
```

If manual resume fails, check the error message before retrying. The common
causes are concrete:

- The run is a child run. Resume the parent run ID shown in the error instead;
  the parent is the run that can safely continue the whole nested execution
  tree.
- The run is not currently `PAUSED`. A run that is still running, already
  completed, failed, or stopped cannot be resumed with this command.
- The run still has an active wait condition. Resolve the wait condition first,
  then resume the run.
- ZenML can no longer find the snapshot or stack that the paused run needs in
  order to continue. In that case, the run cannot be resumed until the missing
  reference is restored or recreated.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
