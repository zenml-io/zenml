---
description: Archive older execution details and restore them when needed.
---

# Execution retention

Execution retention moves the details of old, finished pipeline runs out of
the database into verified archive objects. Each archived run produces one
object holding the run's configuration and environment, its steps' detail,
the snapshots only that run uses, and their step configurations. Run
identities, statuses, timestamps, artifact links, tags, and all run metadata
stay in the database. Archived runs remain visible in ordinary lists. Restore
a run explicitly before reading its archived detail, inspecting its DAG, or
replaying it.

The schedule field `is_archived` is a separate scheduling concept and is
unrelated to execution retention.

Archiving is **disabled by default** and requires a **MySQL** database. A
server with archiving enabled on SQLite refuses to start.

Retention reduces future database growth. It does not delete artifact files,
automatically reclaim database files, or shrink a database volume.

{% hint style="warning" %}
Archiving is server-wide and has **no opt-out**. Once enabled, the scheduled
sweep archives every finished run past `after_days`, in every project, for
every team on the server. There is no per-project switch and no way to pin a
run. Choose `after_days` with that in mind before enabling it.
{% endhint %}

## Configure archiving

Archiving is configured once per deployment through one environment group,
and every setting takes effect after a restart:

```shell
ZENML_SERVER_ARCHIVE__BACKEND=s3
ZENML_SERVER_ARCHIVE__URI=s3://my-bucket/zenml-archive
ZENML_SERVER_ARCHIVE__AFTER_DAYS=90
ZENML_SERVER_ARCHIVE__SCHEDULE="0 3 * * *"
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKEND` | `disabled` | `disabled`, `local`, `s3`, `gcs`, or `azure`. Anything but `disabled` turns archiving on and requires `URI`. |
| `URI` | unset | Archive root. Its scheme must match the backend. |
| `AFTER_DAYS` | 90 | Minimum age of a finished run, at least **7 days**. |
| `SCHEDULE` | `0 3 * * *` | Cron expression for the sweep, in UTC. |
| `MAX_RUNS_PER_PASS` | 200 | Runs one sweep examines. |
| `RESTORED_GRACE_DAYS` | 30 | Days a restored run stays in the database before it may be archived again. |
| `MODEL_LINKED_RUNS` | `false` | Whether runs linked to a model version may be archived. |
| `CONNECTOR_ID` | unset | Service connector to authenticate with, instead of ambient credentials. |

An incomplete or inconsistent group fails startup naming the exact variable,
so a typo cannot silently leave archiving half-configured.

{% hint style="info" %}
**During a rolling upgrade, keep `BACKEND` at `disabled` until every replica
runs the new version.** The migration is additive and safe to apply first, but
an old replica cannot see the archive markers and would serve archived runs as
if their detail were still there.
{% endhint %}

### Credentials

By default the server stores no credentials for the archive: the SDK behind
the URI's scheme uses the credentials of the server process itself.

| Backend | Typical credentials |
| --- | --- |
| `s3` | An IAM role for the server's pod or instance, such as IRSA on EKS. |
| `gcs` | Workload Identity or the service account attached to the server. |
| `azure` | A managed identity or the default Azure credential chain. |
| `local` | For test servers. With several replicas, the path must be shared storage every replica sees. |

Set `CONNECTOR_ID` to authenticate through a ZenML **service connector**
instead; the server connects and refreshes it exactly as a registered stack
component would. A connector named there cannot be deleted while it is
configured, because deleting it would make archived runs unreadable.

The server image must include the matching integration, which the official
images do. The credentials must allow reading, writing, and deleting objects
below the URI.

At startup and before each sweep, the server writes, reads back, and removes
a probe object at `{uri}/_probes/{uuid}`. A failed startup probe only logs a
warning, so a transient outage does not stop the server. Archive objects live
at `{uri}/{project_id}/{run_id}/{bundle_id}.json.gz`; the database records
each object's full URI.

Keep the storage and its objects available while any run is archived. ZenML
keeps committed archive objects, and restoring their detail becomes impossible
if they disappear. Disabling the backend stops new sweeps and prevents
restores until it is enabled again.

## What the sweep archives

A sweep examines runs across every project in age order, starting from where
the previous sweep stopped. Runs that are too recent or linked to a model
version, when the configuration protects them, are skipped before
examination. Every other examined run is archived unless one of these
applies, in which case a later sweep reconsiders it:

| Reason | Meaning |
| --- | --- |
| `not_eligible` | The run, one of its steps, or one of its child runs is still active, or a wait condition is unresolved. |
| `resumable_failed` | The failed run can still be resumed. |
| `root_active` | The run is a child of a root run that is still active or can still be resumed. Resuming a root reruns its child runs, which needs their details. |
| `restored_grace` | The run was restored within the grace period. |
| `oversized` | The run exceeds 50,000 archived rows. |

Each run is archived on its own, including child runs of dynamic pipelines. A
run's archived detail must fit within 64 MiB. A run that turns out larger
during capture stays in the database and counts as `oversized`, and later
sweeps skip it.

## The scheduled sweep

Every replica schedules the sweep on `SCHEDULE`, and a lease decides which
one actually runs it; the others do nothing. A sweep examines up to
`MAX_RUNS_PER_PASS` runs for at most **60 seconds** and saves its position. A
sweep that stops on either budget reports `paused` and is resumed a few
seconds later, so a backlog drains over several sweeps rather than in one
long transaction.

There is no command to trigger a sweep. To archive something now, use the
targeted command below.

## Archive specific runs now

Age-based sweeping cannot help when one noisy pipeline is filling the
database today, so runs can also be archived on demand:

```shell
zenml server retention archive --pipeline my-pipeline
zenml server retention archive --run-id <uuid> --run-id <uuid>
zenml server retention archive --project default
```

This **ignores** the run age, model-version links, and the restore grace
period. It never ignores the rules that keep a run readable while something
is still using it: archiving an active run would strip configuration the
orchestrator is reading. Runs it refuses are listed with their reason.

A pipeline or project target archives a bounded batch of its oldest finished
runs and reports whether more remain, so repeat the command until it stops
saying so. Naming runs directly requires update permission on each run;
naming a pipeline or project requires update permission on that resource.

The same is available from the Python client:

```python
from zenml.client import Client

result = Client().archive_runs(pipeline="my-pipeline")
print(result.archived, result.refusals)
```

## Check status

```shell
zenml server retention status
```

Status shows the latest sweep outcome, when it finished, how many runs it
archived, skipped, found oversized, or failed on, and whether archiving is
enabled and its storage usable. It never scans runs or reads archive objects.
Reading it requires a server admin.

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `idle` | No sweep has run on this server. | Wait for the schedule. |
| `running` | A sweep is working. | Check again shortly. |
| `succeeded` | The sweep reached the end of the eligible runs. | Nothing; the next scheduled sweep picks up newly eligible runs. |
| `paused` | The sweep stopped at its run or time budget. | Nothing; it resumes automatically. |
| `failed` | The sweep stopped early; the server log has the failure code. | Use the table below and correct the cause. |
| `expired` | A running sweep stopped updating for ten minutes, for example because its server process stopped. | The next sweep takes over. |

| Failure | Meaning | Next action |
| --- | --- | --- |
| `storage_configuration` | The storage probe failed. | Check the archive URI, the integration, and the server's credentials. |
| `archive_failed` | The sweep itself hit an unexpected error, such as an unreachable database. | Inspect the server logs. |

A run that changed while it was being archived is skipped and reconsidered
later. A run whose own archiving failed is counted in `failed` and the sweep
carries on with the next one, so a sweep can report `succeeded` with a
non-zero `failed` count; the server log names each error type. Those runs are
reconsidered by the next sweep.

## What users see

Archived runs list normally without detail (`hydrate=False`). Their status,
identity, timestamps, artifact links, and retained step projections remain
available from SQL. Reading archived run, step, snapshot, or DAG detail returns
**409** with instructions to restore the owning run. A detailed list that
contains an archived row also returns **409**; list without detail or filter
with `archive_bundle_id="isnull:"` to see only unarchived detail.

Archived steps are excluded from cache lookups. New runs execute those steps
again unless an unarchived cache candidate is available.

Writes that change archived detail, such as updating status or adding a step,
also require restore. Metadata and tags still work. Deleting a snapshot
archived with a run returns **409** while that run exists.

Ordinary reads never access archive storage, so an archive storage outage does
not affect header reads. A restore during an outage returns **503** with
`Retry-After`; an object that fails verification returns **500**. Either
failure leaves the archived SQL rows unchanged.

## Restore

Restore writes an archived run's detail back into the database:

```shell
zenml pipeline runs restore my-run
```

The command accepts a run name, ID, or unique ID prefix and finishes when the
run is restored. Restore is all-or-nothing: it needs every archived row to
still exist with its archive marker, and any mismatch returns **409** without
changing anything. A run that is not archived returns `noop`. A restored run
is protected from re-archiving for `restored_grace_days`.

**Replay requires a restore first.** Replaying an archived run returns 409
with the restore command.

Deleting an archived run is **irreversible**. Its archive object is kept, but
the run can no longer be restored. A snapshot archived with it keeps its SQL
header and can then be deleted; its archived detail cannot be restored without
the owning run.

## API routes

| Method and route | Purpose | Permission |
| --- | --- | --- |
| `POST /api/v1/retention/archive` | Archive named runs, a pipeline, or a project now. | Update on each run, or on the named pipeline or project |
| `GET /api/v1/retention/status` | Read the latest sweep. | Server admin |
| `POST /api/v1/runs/{run_id}/restore` | Restore a run; returns the result. | Run update |

Archiving runs happens within the request and can take a while. The route
honors an `Idempotency-Key` header: a client that sends one and reuses it on
retry gets the stored result instead of archiving a second batch. The ZenML
CLI and Python client do not send one, so a retried pipeline or project
request archives the *next* batch. Named runs are unaffected, because an
already archived run is simply refused.

## Limitations

1. **MySQL only.** SQLite servers cannot archive.
2. **Explicit restore is required** for archived detail and replay. Automatic
   archived reads are deferred to a later version.
3. **Archive objects are never deleted,** and archived detail depends on them staying available at the recorded URIs.
4. **Only archive format version 1 exists.** Other versions are integrity errors; there are no format adapters.
5. **Detailed lists fail with 409 if they contain an archived row.** Use
   `hydrate=False` or filter to unarchived rows.
6. **Only the latest sweep is recorded.** There is no operation history.
7. **There is no opt-out.** Archiving is server-wide, and no project or run
   can be excluded once it is enabled.
8. **Metadata, hook invocations, and run wait conditions stay in the database.**

Physical reclamation remains separate database administration work. Measure
table and volume sizes after archiving, and use your own backup and
maintenance procedures if you rebuild tables. ZenML does not rebuild tables
or shrink volumes.
