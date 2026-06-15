---
description: Trigger pipelines by schedule or event.
icon: server
---

# Triggers

{% hint style="info" %}
Triggers are part of ZenML's paid features. For details on availability and supported plans, visit the [pricing page](https://www.zenml.io/pricing)
{% endhint %}

In the [snapshots](./snapshots.md) section, you learned how to prepare snapshots and execute them on demand via 
the dashboard, CLI, or SDK. In many cases, however, pipelines need to run automatically - either on a schedule or in 
response to an event.

Triggers enable this behavior. A trigger is a configuration that defines one or more conditions under 
which a pipeline is automatically started.

## Schedule Triggers

*Schedule Triggers* allow pipelines to run automatically based on time-based rules, such as fixed intervals
or cron expressions. They are ideal for recurring workflows, on a predictable timeline, like daily retraining, 
batch processing, or periodic data ingestion.

When defining a scheduled trigger, you can configure both when and how your pipeline runs. Choose between 
one-off executions, interval-based schedules, or cron expressions for fine-grained timing control. 
Additional options, such as time boundaries, concurrency limits, and activation settings, let you 
tailor the trigger to your workflow requirements.

| Attribute           | Description                                                             | Notes                        |
|---------------------|-------------------------------------------------------------------------|------------------------------|
| name                | The name of the schedule                                                | Unique within project        |
| cron_expression     | A cron expression describing your schedule's frequency                  | Standard 5-field cron format |
| interval            | An interval (in seconds) describing the schedule's frequency            | Combined with start_time     |
| run_once_start_time | One-off execution at a specific time in the future                      | UTC                          |
| start_time          | The beginning of the schedule                                           | UTC                          |
| end_time            | The end time of the schedule                                            | UTC                          |
| active              | Status of the schedule (active/inactive)                                | -                            |
| concurrency         | Option to control how concurrent runs should be handled                 | Skip is the default option   |
| max_runs            | Option to control maximum runs (per attached snapshot) for the schedule | -                            |

### Create a schedule

Let's start by creating a schedule. We can do so, via the SDK or the CLI.

Via the SDK:

~~~python
from zenml.client import Client
from zenml.enums import TriggerRunConcurrency

client = Client()

daily_schedule = client.create_schedule_trigger(
    name='daily-schedule-6-am',
    cron_expression='0 6 * * *',
    active=True,
    concurrency=TriggerRunConcurrency.SKIP,
)
~~~

Via the CLI:

~~~bash
zenml trigger schedule create daily-schedule-6-am --cron-expression "0 6 * * *"
~~~

### Attach/Detach schedules and snapshots

So far we have instructed our system with *when* to execute but not *what*. To do so,
we need to *attach* a schedule to a snapshot.

For the CLI, commands that take a trigger or snapshot accept its name or ID
(exact match, not a prefix). Positional order is always trigger first, then snapshot.

Via the SDK:

~~~python
from uuid import UUID
from zenml.client import Client

client = Client()
client.attach_trigger_to_snapshot(
    trigger_id=UUID("<TRIGGER_UUID>"),
    pipeline_snapshot_id=UUID("<SNAPSHOT_UUID>"),
)
~~~

Via the CLI:

~~~bash
zenml trigger schedule attach "<TRIGGER_NAME_OR_ID>" "<SNAPSHOT_NAME_OR_ID>"
~~~

Users can provide a configuration object to define the parameters of pipeline runs
triggered from this attachment.

Via the SDK:

~~~python
from uuid import UUID
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration

client = Client()
client.attach_trigger_to_snapshot(
    trigger_id=UUID("<TRIGGER_UUID>"),
    pipeline_snapshot_id=UUID("<SNAPSHOT_UUID>"),
    run_configuration=PipelineRunConfiguration(
        enable_step_logs=True,
        enable_pipeline_logs=True,
    )
)
~~~

Via the CLI (using a `PipelineRunConfiguration` YAML file):

~~~bash
zenml trigger schedule attach "<TRIGGER_NAME_OR_ID>" "<SNAPSHOT_NAME_OR_ID>" \
  --config=<path-to-your-config>.yml
~~~

To stop a trigger from launching runs for a specific snapshot, you can *detach* the
trigger from that snapshot.

Via the SDK:

~~~python
from uuid import UUID
from zenml.client import Client

client = Client()
client.detach_trigger_from_snapshot(
    trigger_id=UUID("<TRIGGER_UUID>"),
    pipeline_snapshot_id=UUID("<SNAPSHOT_UUID>"),
)
~~~

Via the CLI:

~~~bash
zenml trigger schedule detach "<TRIGGER_NAME_OR_ID>" "<SNAPSHOT_NAME_OR_ID>"
~~~

The ability to detach and attach snapshots is particularly useful as pipelines evolve. When a new pipeline 
version becomes available, you can update the schedule to use it by detaching the previous 
snapshot and attaching the new one.

{% hint style="warning" %}
As with on-demand execution, scheduling requires snapshots with a **remote stack** with at least:
- Remote orchestrator
- Remote artifact store
- Container registry 
{% endhint %}

### Update schedules

You can update a schedule's configuration at any point. In the example, we will de-activate and rename the schedule.

Via the SDK:

~~~python
from zenml.client import Client

client = Client()
client.update_schedule_trigger(
    trigger_name_id_or_prefix="daily-schedule-6-am",
    active=False,
    name="daily-schedule-6-am[DO NOT TOUCH]",
)
~~~

Via the CLI:

~~~bash
zenml trigger schedule update "daily-schedule-6-am" --active=false \
  --name="daily-schedule-6-am-(dont-touch)"
~~~

### View Schedules

Triggers are a first-level citizen of the ZenML platform. You can view detailed information in the
dashboard as well as via the SDK and CLI.

Via the dashboard:

To view schedules, you need to navigate to the `Triggers` tab:

![Image Showing Triggers tab](../../.gitbook/assets/schedule_list_dsb.png)

You can inspect a schedule's information:

![Image Showing Schedule View](../../.gitbook/assets/schedule_view_dsb.png)

Or its attached snapshots and executed pipeline runs:

![Image Showing Schedule Snapshots](../../.gitbook/assets/schedule_snaps_dsb.png)

![Image Showing Schedule Runs](../../.gitbook/assets/schedule_runs_dash.png)

For each trigger–snapshot attachment, ZenML can persist the **dispatch state**.
This is the small status record that answers, "what happened the last time this
trigger tried to launch this snapshot?" The status can be:

- `SUCCESS`: a run was launched successfully.
- `SKIPPED_CONCURRENCY`: a run was skipped because the trigger's concurrency
  rule said not to start another one yet.
- `SKIPPED_MAX_RUNS`: a run was skipped because the configured run limit for
  this trigger-snapshot attachment has already been reached.
- `ERROR`: ZenML tried to dispatch the run, but something failed.

When the last status is `ERROR`, the dispatch state can also include the last
error message, error type, severity, stack trace, first/last error timestamps,
and an error count. After you fix the underlying problem, you can acknowledge
the error and clear the stored dispatch state (see the next section). In the
normal failure case, clearing errors removes the `ERROR` status record for that
trigger-snapshot attachment, so the next dispatch can start from a clean state.
Use `get_schedule_trigger` with `trigger_name_id_or_prefix` to load a schedule
by name, full ID, or ID prefix; set `allow_name_prefix_match=False` if you need
an exact name match.

Via the SDK:

~~~python
from zenml.client import Client

client = Client()

active_schedules = client.list_schedule_triggers(
    active=True,
)  # list schedules

schedule = client.get_schedule_trigger(
    trigger_name_id_or_prefix="my-schedule",
)

for snapshot in schedule.snapshots:  # iterate a schedule's attached snapshots
    print(snapshot.id)
~~~

Via the CLI:

~~~bash
zenml trigger schedule list --active=true
~~~

### Stopping Criteria

You can control when a schedule stops by limiting it in time or by number of runs. This helps avoid unintended 
long-running schedules and gives you tighter control over resource usage.

#### `end_time`

Defines the point in time after which the schedule will no longer trigger runs. 
The schedule remains visible but inactive for future executions.

~~~python
from datetime import datetime, timedelta
from zenml.client import Client

client = Client()

client.create_schedule_trigger(
    name="limited-schedule",
    cron_expression="0 0 * * *",
    end_time=datetime.now() + timedelta(days=2),
)
~~~

#### `max_runs`

Limits how many times a schedule can trigger a pipeline. Once the limit is
reached for a trigger-snapshot attachment, no further runs are scheduled for
that attachment. Later dispatch attempts can show up as `SKIPPED_MAX_RUNS` in
the dispatch state. This is not an error that needs to be cleared; it is ZenML
saying, "the run limit you configured has been reached."

Note that this limit applies per attached snapshot, for example, with a limit of
2 and two attached snapshots, you will see a total of 4 runs.

~~~python
from zenml.client import Client

client = Client()

client.create_schedule_trigger(
    name="limited-schedule",
    cron_expression="0 0 * * *",
    max_runs=24,
)
~~~

#### Combined usage

If both are set, the schedule stops when the first condition is reached (time or run limit).

#### Clear dispatch errors

To clear stored dispatch error details after the issue is resolved, use the SDK
or the `clear-errors` command under `zenml trigger schedule`. With no snapshot argument, errors are cleared for **all** snapshots attached to that trigger.

Via the SDK:

~~~python
from uuid import UUID
from zenml.client import Client

client = Client()
trigger = client.get_schedule_trigger(
    trigger_name_id_or_prefix="my-schedule",
    allow_name_prefix_match=False,
    hydrate=False,
)
client.clear_trigger_dispatch_error(
    trigger_id=trigger.id,
    pipeline_snapshot_id=None,
)
~~~

To clear the error only for one attached snapshot, pass that snapshot’s UUID
(in addition to the `client` and `trigger` values from the example above):

~~~python
from uuid import UUID

client.clear_trigger_dispatch_error(
    trigger_id=trigger.id,
    pipeline_snapshot_id=UUID("<SNAPSHOT_UUID>"),
)
~~~

Via the CLI:

~~~bash
zenml trigger schedule clear-errors "my-schedule"
zenml trigger schedule clear-errors "my-schedule" "my-snapshot"
~~~

### Delete schedules

Triggers in ZenML are archivable objects. When a Trigger is archived (soft-deleted), it is deactivated and can no 
longer be used, but it remains in the system to preserve references for visibility and debugging.

Archiving (soft deletion) is the default deletion mode. Triggers can also be permanently deleted. Neither 
operation can be reversed.

Via the dashboard:

![Image Showing Schedule Deletion](../../.gitbook/assets/delete_schedule_soft.png)

You can view archived schedules by setting the `Display archived` filter, where
you can also hard delete them.

![Image Showing Schedule Hard Deletion](../../.gitbook/assets/delete_schedule_hard.png)

Via the SDK:

~~~python
from uuid import UUID
from zenml.client import Client

client = Client()
client.delete_trigger(
    trigger_id=UUID("<TRIGGER_UUID>"),
    soft=True,
)
~~~

Via the CLI:

Default behavior is **soft** deletion (the trigger is archived). Pass
`--hard` to remove the trigger and its associated references permanently. To
operate on an **archived** trigger, add `--archived` (for example, to hard
delete a trigger that is already archived).

~~~bash
zenml trigger schedule delete "my-schedule"
zenml trigger schedule delete "my-schedule" --hard
zenml trigger schedule delete "my-old-schedule" --archived --hard
~~~

## Triggers vs OSS schedules

ZenML provides [scheduling](../../how-to/steps-pipelines/scheduling.md) as an open-source feature. This section 
outlines the differences between open-source schedules and schedule-based Triggers, and explains why Triggers are 
better suited for production workloads:

* Lifecycle management
  * Triggers: You can update or delete a schedule at any time, and changes are automatically applied across the system.
  * OS Schedules: Updates and deletions must be managed manually on the orchestrator side (except when using the `KubernetesOrchestrator`).
* Feature support
  * Triggers: All scheduling features are consistently available across stacks.
  * OS Schedules: Feature availability depends on the scheduling capabilities of the selected orchestrator.
* Flexibility
  * Triggers: Snapshots and schedules are managed independently. You can dynamically attach or detach snapshots to or from schedules.
  * OS Schedules: Schedules are bound to individual pipelines and cannot be shared across multiple pipelines.
* Visibility
  * Triggers: Extended dashboard visibility and management.
  * OS Schedules: Limited dashboard exposure.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>


## Platform Event Triggers

*Platform Event Triggers* extend ZenML’s trigger system by enabling pipelines to run automatically in response
to events occurring within the ZenML platform itself. Instead of relying on time-based schedules, these
triggers allow users to define downstream pipeline executions that react to lifecycle events, such as
the completion of another pipeline. This makes it easy to build event-driven workflows where pipelines are 
seamlessly chained based on platform activity.

When defining a platform event trigger, you configure what resource to listen to and which events should 
initiate a pipeline run. The source_type and source_id identify the ZenML entity you want to react 
to (e.g., a specific pipeline), while target_events define the events of interest (e.g., completed or failed). 
Additional options, such as activation state and concurrency behavior, allow you to control how the 
trigger operates within your workflow.

| Attribute     | Description                                               | Notes                              |
|---------------|-----------------------------------------------------------|------------------------------------|
| name          | The name of the trigger                                   | Unique within project              |
| source_type   | The type of ZenML entity to listen to (e.g., pipeline)    | Defines the event source category  |
| source_id     | The UUID of the source entity                             | e.g., a specific pipeline UUID     |
| target_events | List of events that will activate the trigger             | Depends on the source type         |
| active        | Status of the trigger (active/inactive)                   | -                                  |
| concurrency   | Option to control how concurrent runs should be handled   | Skip is the default option         |

You can manage platform event triggers using the same set of commands (create, update, attach, detach, list, delete, clear-errors)
as for schedule triggers. While some parameters and responses differ slightly, additional utilities are 
available to help you work more effectively with this trigger type.

Supported target events depend on the source type:

| Source type | Meaning | Target events |
|-------------|---------|---------------|
| `pipeline` | React to runs of a pipeline | `run_completed`, `run_failed` |
| `pipeline_run` | React to one specific pipeline run | `completed`, `failed` |
| `pipeline_snapshot` | React to runs of a pipeline snapshot | `run_completed`, `run_failed` |

That distinction is easy to miss. If the source is a pipeline, the event name
includes the word `run` because the pipeline itself is not what completes; one
of its runs does. Pipeline snapshot events follow the same naming pattern. If
the source is already a pipeline run, the event is simply `completed` or
`failed`.


### Create Platform Event Trigger

Let's start by creating a Platform Event Trigger. In this example, we want to react to the successful 
completion of a specific pipeline.

Via the SDK:

```python
from zenml.client import Client
from zenml.enums import PipelineEvent
from zenml.utils.trigger_utils import create_platform_event_trigger

source_pipeline = Client().get_pipeline(name_id_or_prefix="hello-pipeline")

trigger = create_platform_event_trigger(
    name="on-hello-pipeline-complete",
    source_pipeline_id=source_pipeline.id,
    target_events=[PipelineEvent.RUN_COMPLETED],
)
```

Via the CLI:

The SDK provides helpful overloads that guide you toward valid configurations by suggesting the supported target 
events for a given source type as you type. To improve discoverability in the CLI, an additional helper 
command is available:

```bash
zenml trigger platform-event list-supported-events pipeline
```

Then we can create the trigger as follows:

```bash
zenml trigger platform-event create "on-hello-pipeline-complete" pipeline <PIPELINE_UUID> --target_events=run_completed
```

### Update Platform Event Triggers

Let's continue by updating our existing trigger. In this example, we want to add multiple target events. 
The trigger initially reacted to successful completion, and we will now extend it to react to failures as well.

Via the SDK:

```python
from zenml.enums import PipelineEvent
from zenml.utils.trigger_utils import update_platform_event_trigger

trigger = update_platform_event_trigger(
    trigger_name_id_or_prefix="on-hello-pipeline-complete",
    target_events=[PipelineEvent.RUN_FAILED, PipelineEvent.RUN_COMPLETED],
)
```

Via the CLI:

```bash
zenml trigger platform-event update "on-hello-pipeline-complete" \
  --target_events=run_completed --target_events=run_failed
```

### Remaining Platform Event Trigger operations

The remaining operations (list, attach, detach, delete, and clear-errors) match schedule triggers.
In the CLI, they are grouped under a different command namespace, but the syntax remains the same. 
You can explore the available platform event trigger commands with:

```bash
zenml trigger platform-event
```

To view platform event triggers via the SDK:

```python
from uuid import UUID
from zenml.client import Client

# By name, ID, or ID prefix
trigger = Client().get_platform_event_trigger(
    trigger_name_id_or_prefix="on-hello-pipeline-complete",
)

# List with filtering & sorting
triggers = Client().list_platform_event_triggers()
```

To attach, detach, and delete triggers via the SDK, the methods are shared across
all trigger types (IDs are UUIDs):

```python
from uuid import UUID
from zenml.client import Client

c = Client()
c.attach_trigger_to_snapshot(
    trigger_id=UUID("<trigger_uuid>"),
    pipeline_snapshot_id=UUID("<snapshot_uuid>"),
)
c.detach_trigger_from_snapshot(
    trigger_id=UUID("<trigger_uuid>"),
    pipeline_snapshot_id=UUID("<snapshot_uuid>"),
)
c.delete_trigger(trigger_id=UUID("<trigger_uuid>"), soft=True)
```

### Upstream information

When a downstream pipeline is executed, it can be useful to access information about the upstream run 
that triggered it. The following example shows how to retrieve this information within a running pipeline step:


```python
from zenml import step, get_step_context
from zenml.utils.trigger_utils import get_upstream_run

@step
def my_step():
    current_run = get_step_context().pipeline_run
    upstream_run = get_upstream_run(pipeline_run=current_run)
    print(f"Upstream run ID: {upstream_run.id} name: {upstream_run.name}")
```

### Chaining pipelines with triggers

Platform Event Triggers can be used to build simple multi-pipeline workflows by chaining pipelines together. 
For example, you can configure a trigger so that when Pipeline A completes, it starts Pipeline B, which in 
turn can trigger Pipeline C. This enables lightweight orchestration patterns directly within ZenML, allowing you 
to break down complex workflows into smaller, reusable pipeline components that execute in sequence based on platform events.

{% hint style="warning" %}
However, care must be taken when designing such workflows. Since cyclic dependencies are not currently validated, 
it is possible to create loops where pipelines continuously trigger each other (for example, Pipeline 
A triggers B, and B triggers A). This can lead to unintended behavior such as infinite execution cycles and 
resource exhaustion. Users should ensure that their trigger configurations form an acyclic graph and avoid circular dependencies.
{% endhint %}
