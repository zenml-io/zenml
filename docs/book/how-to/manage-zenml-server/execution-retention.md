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
server configured with an archive URI on SQLite refuses to start.

Retention reduces future database growth. It does not delete artifact files,
automatically reclaim database files, or shrink a database volume.

## Configure archive storage

Point the server at a bucket prefix or directory and restart every server
process:

```shell
ZENML_SERVER_ARCHIVE_URI=s3://my-bucket/zenml-archive
```

Setting the URI enables archiving. The server never stores credentials for
it: the SDK behind the URI's scheme uses the credentials of the server
process itself.

| Scheme | Typical credentials |
| --- | --- |
| `s3://` | An IAM role for the server's pod or instance, such as IRSA on EKS. |
| `gs://` | Workload Identity or the service account attached to the server. |
| `az://`, `abfs://` | A managed identity or the default Azure credential chain. |
| A local path | For test servers. With several replicas, the path must be shared storage every replica sees. |

The server image must include the matching integration, which the official
images do. The credentials must allow reading, writing, and deleting objects
below the URI.

At startup and before each archive pass, the server writes, reads back, and
removes a probe object at `{uri}/_probes/{uuid}`. A failed startup probe only
logs a warning, so a transient outage does not stop the server. Archive
objects live at `{uri}/{project_id}/{run_id}/{bundle_id}.json.gz`; the
database records each object's full URI.

Keep the storage and its objects available while any run is archived. ZenML
keeps committed archive objects, and restoring their detail becomes impossible
if they disappear. Unsetting the URI stops new passes and prevents restores
until it is set again.

## Save a policy

The CLI merges supplied values into the saved policy, so omitted options keep
their current values:

```shell
zenml project retention set default --archive-after-days 90
zenml project retention show default
```

The project argument accepts a name or ID and defaults to the active project.
Use `zenml project retention set default --disable` to clear the policy. The
same policy can be saved through the Python client:

```python
from zenml.client import Client
from zenml.models import RetentionSettings

Client().update_project(
    "default",
    retention=RetentionSettings(archive_after_days=90),
)
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `archive_after_days` | disabled | Minimum age of a finished run, at least **7 days**. |
| `archive_model_linked_runs` | `False` | Whether runs linked to a model version may be archived. |
| `restored_grace_days` | 30 | Days a restored run stays in the database before it may be archived again. |
| `max_runs_per_pass` (`--max-runs`) | 200 | Runs one archive pass examines. |

An archive pass examines runs in age order, starting from where the
previous pass stopped. Runs that are pinned, too recent, or linked to a
model version, when the policy protects them, are skipped before
examination. Every other examined run is archived unless one of these
applies, in which case a later pass reconsiders it:

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
passes skip it.

## Archive and check status

The archive command names the saved policy and asks for confirmation. Use
`--yes` for an unattended submit:

```shell
zenml project retention archive default
zenml project retention status default
```

A pass examines up to `max_runs_per_pass` runs for at most **60 seconds** and
saves its position, so the next pass continues from there. There is no
scheduler; run the command again, or from cron, until status stops
reporting archived runs. With a server connection, `accepted` means the
pass was submitted, not finished.

Status shows the latest pass outcome, when it finished, how many runs it
archived, skipped, found oversized, or failed on, and whether archiving is
enabled and its storage usable. It never scans runs or reads archive objects.

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `idle` | No pass has run for this project. | Start a pass. |
| `accepted` | The server accepted the pass and queued it. | Poll status. |
| `running` | The pass is working. | Poll status. |
| `succeeded` | The pass reached the end of the eligible runs. | Start another pass later to archive newly eligible runs. |
| `paused` | The pass stopped at its run or time budget, or because the policy changed. | Start another pass to continue. |
| `failed` | The pass stopped early; the server log has the failure code. | Use the table below, correct the cause, and retry. |
| `expired` | An accepted or running pass stopped updating for ten minutes, for example because its server process stopped. | Start a new pass; it takes over. |

| Failure | Meaning | Next action |
| --- | --- | --- |
| `storage_configuration` | The storage probe failed. | Check the archive URI, the integration, and the server's credentials. |
| `archive_failed` | The pass hit an unexpected error. | Inspect the server logs and retry. |
| `permission_revoked` | Authorization changed between submission and execution. | Restore the permission and resubmit. |
| `submission_failed` | The server accepted the pass but could not queue it. | Check the server's maintenance worker and logs, then resubmit. |

A run that changed while it was being archived is skipped and reconsidered
by a later pass. Runs whose archiving failed are counted in `failed`; the
server log names the error type.

Only one pass per project runs at a time: submitting while another pass holds
its lease returns **409**. Each server process runs maintenance jobs on **one
worker**, so a submission while it is busy returns **429**. Retry once the
other work finishes.

## What users see

Archived runs list normally without detail (`hydrate=False`). Their status,
identity, timestamps, artifact links, and retained step projections remain
available from SQL. Reading archived run, step, snapshot, or DAG detail returns
**409** with instructions to restore the owning run. A detailed list that
contains an archived row also returns **409**; list without detail or filter
with `archive_bundle_id="isnull:"` to see only unarchived detail.

Writes that change archived detail, such as updating status or adding a step,
also require restore. Metadata, tags, and pins still work. Deleting a snapshot
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
| `POST /api/v1/projects/{project}/retention/archive` | Start a pass; returns 202. | Project update |
| `GET /api/v1/projects/{project}/retention/status` | Read the latest pass. | Project read |
| `POST /api/v1/runs/{run_id}/restore` | Restore a run; returns the result. | Run update |

The background worker checks authorization again before it starts a pass.

## Limitations

1. **MySQL only.** SQLite servers cannot archive.
2. **Explicit restore is required** for archived detail and replay. Automatic
   archived reads are deferred to a later version.
3. **Archive objects are never deleted,** and archived detail depends on them staying available at the recorded URIs.
4. **Only archive format version 1 exists.** Other versions are integrity errors; there are no format adapters.
5. **Detailed lists fail with 409 if they contain an archived row.** Use
   `hydrate=False` or filter to unarchived rows.
6. **Only the latest pass is recorded.** There is no operation history.
7. **Metadata, hook invocations, and run wait conditions stay in the database.**

Physical reclamation remains separate database administration work. Measure
table and volume sizes after archiving, and use your own backup and
maintenance procedures if you rebuild tables. ZenML does not rebuild tables
or shrink volumes.
