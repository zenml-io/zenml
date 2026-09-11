---
description: Archive older execution details while keeping runs readable.
---

# Execution retention

Execution retention moves the details of eligible, completed executions from
SQL into verified archive bundles. A **tree** means one canonical root run, its
nested runs, their steps, and the snapshots and configurations owned only by
those runs. Run identities, statuses, timestamps, artifact links, and all run
metadata remain in SQL. Archived runs remain visible in ordinary lists, and
detail reads load archived run, step, snapshot, and DAG data automatically.

The schedule field `is_archived` is a separate scheduling concept and is
unrelated to execution retention.

Archiving is **disabled by default**. Upgrade every execution writer to support
the archive write protections and validate archive, read, and restore behavior
before enabling it.

Retention reduces future SQL detail growth. It does not delete artifact files,
automatically reclaim database files, or shrink a database volume. Logical byte
estimates are not physical disk savings.

## Configure a registered artifact store

Register an artifact store using the existing ZenML artifact-store workflow.
Make its integration and credentials available to every server process that
reads or writes execution data. For a local artifact store, every replica must
see the same durable files.

First set the registered component ID and, optionally, a path prefix, then
restart the server processes:

```shell
ZENML_SERVER_ARCHIVE_ARTIFACT_STORE_ID=<registered-artifact-store-uuid>
ZENML_SERVER_ARCHIVE_PATH_PREFIX=execution-retention
```

The component ID is required for archival and archived reads. The path prefix
defaults to an empty prefix beneath the component's path. The server uses the
registered component's credentials, timeouts, and retries. There is no separate
archive flavor, URI, namespace, or credentials configuration.

The server checks storage once per archive pass by writing, reading, and
removing a temporary object at
`{store.path}/{prefix}/_retention-probes/{uuid}`. Bundles are stored below
`{store.path}/{prefix}/archive/`; an empty prefix omits that path segment.
Credentials scoped to the configured prefix must allow the probe operations as
well as access to archive objects.

After those deployment checks pass, enable archiving and restart the server
processes again:

```shell
ZENML_SERVER_ARCHIVE_ENABLED=true
```

Setting the gate back to `false` prevents new archive passes. Archived reads and
explicit restore remain available with the configured component. Keep its
identity, access, and stored paths available while archives depend on it. Reads
honor the full paths recorded in the SQL catalog; changing the prefix affects
new bundles, not existing paths.

## Save a policy and preview it

The CLI merges supplied values into the saved policy, so omitted options keep
their current values:

```shell
zenml project retention set default --archive-after-days 90
zenml project retention show default
zenml project retention dry-run default
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

Choose an age appropriate to the data your team needs; 90 days above is an
example. `archive_after_days` has a minimum of **7 days**. An age of `None`
disables the project policy. Saving a complete `RetentionSettings` object with
the Python client replaces the saved policy.

Preview uses the saved policy without request-level overrides or data changes.
An unset policy returns no candidates. It reports eligible and examined trees,
the covered row count and one exclusion reason for each tree, one overall
estimated archive size, and whether its bounded batch was truncated. The size
is a predictable planning estimate: runs and steps count as 4 KiB each, step
configurations as 8 KiB, and snapshots as 16 KiB. It does not read payload
lengths and is not a measurement of SQL storage or physical database savings.

Active, pinned, recently restored, and otherwise protected trees are excluded.
Model-linked runs are protected unless the saved policy permits their archival.
A pin on any member protects the whole tree. Pinning an archived run does not
restore it.

The policy limits `max_trees`, `max_rows`, and `max_bytes` default to 200
examined trees, 500,000 covered rows, and a 512 MiB estimated-byte budget per
invocation. `restored_grace_days` defaults to 30 days, and
`archive_model_linked_runs` defaults to `False`. Each archive pass also has a
**60-second budget**; it stops between trees and saves its progress. Each tree
must fit within 10,000 records and 16 MiB of serialized, decoded archive detail.
Trees are indivisible; a large tree can remain in SQL even when it is old enough.
Capture also checks the actual serialized size before any SQL detail is removed.

## Archive and check status

The archive command always previews the eligible data and asks for confirmation.
Use `--dry-run` to stop after the preview or `--yes` for an unattended submit:

```shell
zenml project retention archive default
zenml project retention status default
```

With a server connection, `accepted` means the work was submitted, not
completed. The response carries a maintenance `task_id`, and the command prints
the status command to run next. Status shows the latest outcome and finish time,
storage configuration, enablement, and policy age. It reads SQL and loads the
registered component without opening archive objects.

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `idle` | No pass or restore is currently recorded. A completed archive can also be idle until a restore is requested. | Submit an archive pass or restore if needed. |
| `expired` | An accepted restore worker lost its lease before completion. | Resubmit the restore. A new worker safely replaces the expired claim. |
| `accepted` | The server reserved the operation and queued its maintenance task. | Poll the matching status command; use the returned `task_id` for server-log correlation. Resubmit if it remains unchanged after ten minutes. |
| `running` | An archive pass has committed progress and is continuing. | Wait and poll status. Resubmit if it makes no progress for ten minutes. |
| `succeeded` | The requested pass or restore completed. | No action is required. |
| `failed` | The operation stopped and recorded a safe failure classification. | Use the failure table below, inspect server logs, correct the cause, and retry. |
| `noop` | Restore found that the execution was already unarchived. | No action is required. |
| `paused` | The 60-second pass budget or a saved row/byte bound stopped the pass between trees. | Submit the archive pass again; raise the saved limits if one tree cannot fit. |

| Failure | Meaning | Next action |
| --- | --- | --- |
| `lease_expired` | The worker no longer owned its archive or restore lease. | Retry; the fencing token prevents the expired worker from committing. |
| `archive_failed` | Capture, upload, verification, or SQL retirement failed. | Inspect server logs and storage/database health, then retry. |
| `restore_failed` | The restore stopped outside the more specific failure classes below. | Inspect server logs, preserve the bundle, and retry after correcting the cause. |
| `integrity` | The catalog, manifest, object bytes, or recorded ownership did not agree. | Do not overwrite the object. Investigate the catalog and bundle before retrying. |
| `storage_configuration` | The registered archive component could not be loaded or read. | Restore the component ID, integration, credentials, and access, then retry. |
| `permission_revoked` | Authorization changed after submission and before worker execution. | Restore the required permission and resubmit. |
| `submission_failed` | The server reserved the operation but could not queue the task. | Check the server maintenance worker and logs, then resubmit. |
| `busy` | Another operation owns the execution, or its identities changed during the attempt. | Wait for the other operation or resolve the change, then retry. |
| `pass_budget` | The current time, row, or byte allowance could not cover the next unit of work. | Resubmit to continue, or increase the saved row/byte limits for an indivisible tree. |

Each server process has **one maintenance worker shared with artifact pruning**.
A long artifact prune blocks restore because both use that worker. Archive or
restore submissions while it is occupied receive **429**; retry after the
current maintenance work finishes.

There is no scheduler. Submit another pass to continue from the saved cursor.
The cursor advances past examined roots, including excluded ones, so a protected
root does not prevent progress through the rest of the project. Concurrent
passes can repeat capture work; claims prevent two workers from committing the
same archive. Accepted and running project state expires after ten minutes
without committed progress, allowing a new submission to recover work abandoned
by a stopped server process.

## What users see

Archived runs list normally when `hydrate=False`. Hydrated reads fetch and
verify archived detail automatically, so an archived run, step, or snapshot
returns the same response it returned before archiving. Archiving never clears
a step's `snapshot_id`; only legacy steps recorded without a snapshot report it
as `None`, archived or not.
A hydrated run or step list returns detail only when all cold rows on its page
belong to one bundle. A mixed-bundle page returns **409**; narrow the filter, or
list without details with `hydrate=False` in the client and by omitting
`--hydrate` in the CLI.

A storage failure returns 503 with `Retry-After`; lists without details remain
available. Integrity failures return 500.

## Restore

Restore writes the complete tree's detail back into SQL and clears its archive
markers:

```shell
zenml pipeline runs restore my-run
zenml pipeline runs restore-status my-run
```

Both commands accept a run name, ID, or unique ID prefix. An already unarchived
tree returns `noop`. Poll an accepted restore until it finishes. Restore requires
every archived identity row to remain present with the expected bundle marker.
A missing row, deleted root, or foreign marker causes a conflict and no detail
is written. Resolve the conflict before retrying; restore does not recreate a
deleted root.

Deleting an archived run is **irreversible**. Deleting the root leaves the
catalog row with a null root reference and retains the bundle object; a snapshot
in that bundle remains readable. Restore cannot recreate the deleted root.
Retention does not automatically delete these catalog rows or objects.

**Replay requires explicit restore first.** Replaying an archived run returns
409 with a restore instruction. After restore succeeds, replay uses the normal
execution checks. Other operations that need writable detail also require
restore.

## API lifecycle

The lifecycle keeps five routes because preview is a synchronous report,
archive and restore submit distinct asynchronous jobs, and each job needs a
read-only status route that can be polled without resubmitting work. Accepted
archive and restore responses carry the maintenance `task_id`; terminal status
responses carry the durable outcome.

| Method and route | Purpose |
| --- | --- |
| `POST /api/v1/projects/{project}/retention/dry-run` | Preview the saved policy synchronously. |
| `POST /api/v1/projects/{project}/retention/archive` | Submit the saved policy; no body. |
| `GET /api/v1/projects/{project}/retention/status` | Read the latest pass outcome. |
| `POST /api/v1/runs/{run_id}/restore` | Submit restore; no body. |
| `GET /api/v1/runs/{run_id}/restore` | Read the restore outcome. |

Preview and archive submission require project update permission. Restore
submission requires update permission on the canonical root. Status requires
read permission on the corresponding project or root. Background workers
recheck authorization before executing accepted work.

## Accepted v0 limitations

1. **Restore is all-or-nothing.** Conflicts fail clearly; operators resolve and retry. There are no partial restores.
2. **Replay needs explicit restore first** for archived runs.
3. **Storage is a registered component.** Its integration controls timeouts and retries. Deleting or breaking the component makes archived detail unavailable until the configured component identity, access, and recorded paths are restored administratively. Re-registering a component does not automatically recover the original ID.
4. **Only archive format version 1 exists.** Unsupported versions are integrity errors, not retryable storage errors. There are no format adapters.
5. **Hydrated run and step lists read one bundle.** A mixed-bundle page returns 409; narrow the filter or list without details.
6. **Only the latest operation state is retained.** Restore status comes from the catalog; project state contains an operation ID and expiry, cursor, last outcome, and finish time. There is no operation history.
7. **Metadata never leaves SQL.** Metadata filtering and cache inheritance continue to use SQL; bundles contain no metadata sections.
8. **Hook invocations and run wait conditions remain hot.** V0 does not archive these rows or their detail; they stay in SQL when the owning execution is archived.

Physical reclamation remains separate database administration work. Measure
table and volume sizes after a verified archive batch, and use deployment-specific
backup and maintenance procedures if rebuilding tables or migrating storage is
required. ZenML does not automate table rebuilds, archive-object deletion, or
volume shrinking.
