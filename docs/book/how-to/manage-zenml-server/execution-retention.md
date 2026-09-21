---
description: Archive older execution details and restore them when needed.
---

# Execution retention

Execution retention moves the details of old, finished pipeline runs out of
the database into verified archive objects. Each archived run produces one
object holding the run's configuration and environment, its steps' detail,
the snapshots only that run uses, and their step configurations. Run
identities, statuses, timestamps, artifact links, tags, and all run metadata
stay in the database. Archived summaries remain readable, including in mixed
lists of archived and unarchived runs. API, SDK, and CLI callers restore a run
explicitly before reading its archived configuration, inspecting its DAG, or
replaying it. The bundled dashboard performs that restore when a user opens run
detail.

The schedule field `is_archived` is a separate scheduling concept and is
unrelated to execution retention.

Archiving is **disabled by default** and requires a **MySQL** database. A
server with archiving enabled on SQLite refuses to start.

Retention reduces growth from selected execution details. Retained rows,
metadata, indexes, and shared snapshots can continue growing. It does not
delete artifact files, automatically reclaim database files, or shrink a
database volume.

{% hint style="warning" %}
Archiving is server-wide and has **no opt-out**. Once enabled, the scheduled
sweep considers eligible finished runs past `after_days` in every project,
for every team on the server, subject to the protections below. There is no per-project switch and no way to pin a
run. Choose `after_days` with that in mind before enabling it.
{% endhint %}

## Configure archiving

Archiving is configured once per deployment through one environment group,
and every setting takes effect after a restart:

```shell
ZENML_SERVER_ARCHIVE__BACKEND=s3
ZENML_SERVER_ARCHIVE__URI=s3://my-bucket/zenml-archive
ZENML_SERVER_ARCHIVE__AFTER_DAYS=90
ZENML_SERVER_ARCHIVE__SCHEDULE_ENABLED=true
ZENML_SERVER_ARCHIVE__SCHEDULE="0 3 * * *"
```

Configuring storage only allows manual archiving. Scheduled sweeps archive
every eligible run on the server, so they stay off until you set
`SCHEDULE_ENABLED=true`. Preview what the policy selects first with
`zenml server retention archive --project <project> --dry-run`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKEND` | `disabled` | `disabled`, `local`, `s3`, `gcs`, or `azure`. A non-disabled backend configures storage and requires `URI`. |
| `ENABLED` | `true` | Allow new archives when storage is configured. Set `false` to pause new archiving while keeping restore available. |
| `SCHEDULE_ENABLED` | `false` | Run automatic sweeps on `SCHEDULE`. Off by default, so configuring storage alone only allows manual archiving. |
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
**During a rolling upgrade, keep `BACKEND` disabled or unset until every
replica runs the new version.** Do not introduce the new `ENABLED` or
`SCHEDULE_ENABLED` settings into a mixed-version deployment: older replicas
reject unknown archive settings. The migration is additive and safe to apply
first, but an old replica cannot see archive markers: it tries to load the
detail that archiving removed and answers requests for an archived run with
**500** errors. After all replicas are upgraded,
configure storage; set `ENABLED=false` if new archiving should remain paused.
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

The local backend is intended only for trusted local and test deployments. Set
`ZENML_SERVER_ALLOW_LOCAL_FILE_ACCESS=true` before starting the server so the
archive adapter can access the configured directory. This setting permits
server-side access to local paths for other artifact-store operations too; do
not enable it on an untrusted or multi-tenant server merely to configure
retention.

Set `CONNECTOR_ID` to authenticate through a ZenML **service connector**
instead; the server connects and refreshes it exactly as a registered stack
component would. A connector named there cannot be deleted while it is
configured, because deleting it would make archived runs unreadable.

The server image must include the matching storage integration. The credentials
must allow reading, writing, and deleting objects below the URI.

At startup and before each sweep, the server writes, reads back, and removes
a probe object at `{uri}/_probes/{uuid}`. A failed startup probe only logs a
warning, so a transient outage does not stop the server. Archive objects live
at `{uri}/{project_id}/{run_id}/{bundle_id}.json.gz`; the database records
each object's full URI.

Keep the storage and its objects available while any run is archived. ZenML
keeps committed archive objects, and restoring their detail becomes impossible
if they disappear. Keep the backend, URI, and credentials configured when
pausing archiving:

```shell
ZENML_SERVER_ARCHIVE__ENABLED=false
```

This blocks new manual and scheduled archives after restart. Summaries and
restore remain available. Leave `SCHEDULE_ENABLED` at its default of `false`
for manual-only archiving. Setting `BACKEND=disabled` removes access to archive
storage and therefore also prevents restore; use `ENABLED=false` to pause.

Changing the configured URI or provider does not migrate existing objects.
Restore reads each object at its recorded URI, so the earlier location must
stay in place, and the server's ambient credentials or configured
`CONNECTOR_ID` must still be able to read it. The server image must keep the
storage integration for the earlier provider installed.

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
run's uncompressed archive document must fit within 64 MiB, and one capture
accepts at most 128 MiB of text and binary source values read from SQL. A run
that turns out larger during capture stays in the database and counts as
`oversized`, and later sweeps skip it. These are document and source-transfer
limits, not a process-memory limit: model validation, serialization, and
compression require additional working memory.

Each server process admits at most four retention payload operations at once
across manual archiving, sweeping, and restoration. Manual batches process
their runs sequentially within one admitted operation. This bound is local to
one replica, not cluster-wide; the database-backed sweep lease separately
ensures that only one replica performs a scheduled sweep.

## The scheduled sweep

Every replica schedules the sweep on `SCHEDULE`, and a lease decides which
one actually runs it; the others do nothing. A sweep examines up to
`MAX_RUNS_PER_PASS` runs and uses a **60-second soft budget checked between
runs** before saving its position. A storage request, SQL lock wait, or an
already-started retirement can take the pass beyond that budget. A sweep that
stops on either budget reports `paused` and is resumed a few seconds later, so
a backlog drains over several sweeps rather than in one long transaction.
During server shutdown, cancellation is checked between phases and before a
new retirement starts; shutdown waits for an active scheduled sweep, including
an already-started transaction, to finish rather than interrupting its commit.
Manual archive and restore requests are not drained on shutdown; an
interrupted one rolls back or leaves its run unchanged and can be repeated.

For S3, each SDK request uses a 10-second connection timeout, a 60-second
socket-read timeout, and at most three total attempts. Those are per-request
transport bounds, not a deadline for a complete archive operation, which can
issue several requests. The current ZenML artifact-store contract exposes no
portable whole-operation deadline for GCS, Azure, local filesystems, or SQL.
Their provider and driver timeouts still apply, but this feature cannot promise
a fixed maximum shutdown duration for those backends.

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

Manual archiving applies the same age, model-link, and restore-grace policy
as the scheduled sweep. To deliberately override those three rules, add
`--force`. Because it sets aside the policy the server admin configured,
`--force` requires a server admin. The confirmation identifies the override.
Active runs, resumable runs, and other execution-safety exclusions remain
protected even with force.

A pipeline or project target examines a bounded batch of its finished runs,
earliest-created first. The response includes `pending` and `next_after_run_id`. When more
candidates remain, pass the returned ID with `--after-run-id` on the next
command. This advances past refused runs too; a page that archives nothing
can still have more work after it. The CLI prints the continuation ID.

Archiving requires update permission on every run it archives. Naming a
pipeline or project additionally requires update permission on that resource;
it does not by itself grant permission to archive the runs below it, and a
batch that contains a run the caller cannot update is refused. A continuation
ID must belong to the same target. If that run has been deleted, restart the
scan without a continuation ID.

Preview the same selection without archiving execution data or accessing
archive storage:

```shell
zenml server retention archive --project default --dry-run
```

Preview works while new archiving is paused and requires read permission on
the target and on the runs it selects. It reports eligible candidates and exclusion reasons, with the
same continuation behavior. It does not fetch payloads to estimate bytes;
a candidate can still exceed the byte limit during actual capture or change
before archiving.

The same is available from the Python client:

```python
from zenml.client import Client

client = Client()
result = client.archive_runs(pipeline="my-pipeline", dry_run=True)
print(result.eligible, result.refusals)
if result.pending:
    next_page = client.archive_runs(
        pipeline="my-pipeline",
        dry_run=True,
        after_run_id=result.next_after_run_id,
    )
```

## Check status

```shell
zenml server retention status
```

Status shows the latest sweep outcome, when it finished, how many runs it
archived, skipped, found oversized, or failed on, and whether storage is
configured, new archives are enabled, and automatic sweeps are enabled.
Counts accumulate across the resumed segments of one scan and reset when a
new scan starts from the oldest run.
`archive_configured` means storage settings are present; status does not
construct an adapter or check the health of stored objects. It never scans
runs or reads archive objects.
Reading it requires a server admin.

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `idle` | No sweep has run on this server. | Wait for the schedule. |
| `running` | A sweep is working. | Check again shortly. |
| `succeeded` | The sweep reached the end of the eligible runs. | Nothing; the next scheduled sweep picks up newly eligible runs. |
| `paused` | The sweep stopped at its run or time budget. | Nothing; it resumes automatically. |
| `failed` | The sweep stopped early; the server log has the failure code. | Read the failure code in server logs and correct the cause. |
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

Archived responses include an `archive` descriptor with the bundle ID and,
when available, the owning restore run ID. Snapshot lists omit the owner;
request an individual snapshot summary to obtain its restore run ID after
authorization. SQL-backed summaries remain available with
`hydrate=False`, including retained execution times and metadata. A detailed
list hydrates unarchived rows and returns explicitly marked summaries for
archived rows; one archived row does not fail the entire page.

Single-entity reads that request cold configuration, source, or DAG detail
return **409** with restore instructions. Request the summary to inspect the
retained information without restoring. The SDK's retained summary properties
do not trigger a detail fetch. Artifact links and log references stay in SQL;
log reads that do not need cold configuration do not require restore. The
artifact or log store must still be available to read its contents.

The bundled dashboard restores archived detail as part of the ordinary loading
state when a user deliberately opens a run page, a triggered child run's detail
sheet, or a create-snapshot page. Run lists and background refreshes remain
read-only and do not initiate a restore. Other dashboards and API clients must
handle the archived-detail 409 and call the restore route explicitly.

Use `archive_bundle_id="isnull:"` to filter to unarchived runs when a caller
specifically requires full detail for every row.

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
is protected from scheduled and normal manual archiving for
`restored_grace_days`; an explicit `--force` overrides this grace period.

Restore requires read permission on the run, so a user who can open a run can
also make its cold detail available; the dashboard relies on this when it
restores a run as its page opens. A restore puts back exactly what that user
could read before the run was archived. Updating any run detail still requires
update permission. Restoring one run does not recursively restore its child
runs.

**Replay requires a restore first.** Replaying an archived run returns 409
with the restore command.

Deleting an archived run is **irreversible**. Its archive object is kept, but
the run can no longer be restored. A snapshot archived with it keeps its SQL
header and can then be deleted; its archived detail cannot be restored without
the owning run.

## API routes

| Method and route | Purpose | Permission |
| --- | --- | --- |
| `POST /api/v1/retention/archive` | Archive or preview named runs, a pipeline, or a project. | Update on the target and on every archived run; read for `dry_run=true`; server admin for `force=true` |
| `GET /api/v1/retention/status` | Read the latest sweep. | Server admin |
| `POST /api/v1/runs/{run_id}/restore` | Restore a run; returns the result. | Run read |

Archiving and restoring can take a while. The shared SDK request layer sends
an `Idempotency-Key`; transport retries of that request reuse its result.
A separate SDK call or CLI invocation gets a new key. For project and
pipeline scans, use `next_after_run_id` to continue deliberately; retrying an
operation and advancing the scan are separate actions.

The ZenML client does not retry a busy (**429**) or unavailable (**503**)
response from these routes the way it does for other requests, because each
attempt can run for minutes; it raises the error at once so you can decide
when to try again. A client connected to a server that predates execution
retention gets an error saying so. `GET /api/v1/info` reports
`execution_archiving_enabled`, which is true when the server runs on MySQL
with archive storage configured and new archiving not paused.

## Archive compatibility

Version 1 objects remain readable when the server is upgraded. Changes to
execution payloads or SQL columns must preserve restoration of existing v1
objects; an SQL migration cannot transform copies already in object storage.
The compatibility tests restore frozen static, dynamic, and legacy v1 archives
into the current migrated schema and read their current response models.
A future incompatible format requires a specific compatible reader or restore
conversion before that release can support existing archives.

Do not remove archive objects as part of a server upgrade. Downgrading the
archive migration after archiving is unsupported, including after restoring
runs, because archive catalog records remain.

## Limitations

1. **MySQL only.** SQLite servers cannot archive.
2. **API, SDK, and CLI callers restore explicitly** before reading archived
   detail or replaying a run. The bundled dashboard performs the same restore
   only during deliberate run-detail loading; lists and background refreshes
   remain read-only.
3. **Archive objects are never deleted,** and archived detail depends on them staying available at the recorded URIs. A server process that is killed between uploading an object and committing its run can leave an object that no run refers to. Such an object only costs storage: it is any object below the archive root whose URI is not in the `archive_bundle.uri` column.
4. **Only archive format version 1 exists.** Other versions are integrity errors; there are no format adapters.
5. **Archived entries in detailed lists are summaries.** Check the archive
   descriptor before accessing cold detail; API clients restore explicitly
   when needed.
6. **Only the latest sweep is recorded.** There is no operation history.
7. **There is no opt-out.** Archiving is server-wide, and no project or run
   can be excluded once it is enabled.
8. **Metadata, hook invocations, and run wait conditions stay in the database.**
9. **Shared snapshots stay in SQL,** including snapshots referenced by other
   archived runs. This keeps each run independently restorable but limits
   the payload that archiving can remove.

Physical reclamation remains separate database administration work. Measure
table and volume sizes after archiving, and use your own backup and
maintenance procedures if you rebuild tables. ZenML does not rebuild tables
or shrink volumes.
