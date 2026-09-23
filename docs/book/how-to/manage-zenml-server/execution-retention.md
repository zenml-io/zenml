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

Archiving runs only when you invoke the CLI or SDK. There is no built-in
archive scheduler. Choose a project, pipeline, or individual runs explicitly;
if you need periodic archiving, schedule the CLI command with your own job runner.

## Configure archiving

Archiving is configured once per deployment through one environment group,
and every setting takes effect after a restart:

```shell
ZENML_SERVER_ARCHIVE__URI=s3://my-bucket/zenml-archive
ZENML_SERVER_ARCHIVE__AFTER_DAYS=90
```

Configuring storage allows manual archiving. Preview the selected project
before changing execution data:
`zenml server retention archive --project <project> --dry-run`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ENABLED` | `true` | Allow new archives when storage is configured. Set `false` to pause new archiving while keeping restore available. |
| `URI` | unset | Archive root. Its scheme selects the storage provider; a plain directory path selects local storage. |
| `AFTER_DAYS` | 90 | Minimum age of a finished run, at least **7 days**. |

Setting `URI` configures archive storage. Leave it unset to disable storage.
An empty URI and unknown fields within the `ARCHIVE` group are rejected.
The archive adapter selects and validates the provider using ZenML's existing
artifact-store flavors when storage is initialized.

{% hint style="info" %}
**During a rolling upgrade, leave archive settings unset until every
replica runs the new version.** Do not introduce the new `ENABLED`
setting into a mixed-version deployment: older replicas
reject unknown archive settings. The migration is additive and safe to apply
first, but an old replica cannot see archive markers: it tries to load the
detail that archiving removed and answers requests for an archived run with
**500** errors. After all replicas are upgraded,
configure storage; set `ENABLED=false` if new archiving should remain paused.
{% endhint %}

### Credentials

The server stores no credentials for the archive: the SDK behind
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

Archive storage uses server credentials. Service connectors are not supported
in this iteration.

The server image must include the matching storage integration. The credentials
must allow reading, writing, and deleting objects below the URI.

Startup validates the archive configuration and database support without
contacting object storage. Storage availability and credentials are checked
when an archive, unarchive, or cleanup operation uses them. Archive objects live
at `{uri}/{project_id}/{run_id}/{bundle_id}.json.gz`; the database records
each object's full URI.

Keep the storage and its objects available while any run is archived. ZenML
keeps committed archive objects, and restoring their detail becomes impossible
if they disappear. Keep the URI and credentials configured when
pausing archiving:

```shell
ZENML_SERVER_ARCHIVE__ENABLED=false
```

This blocks new archives after restart. Summaries and unarchive remain
available. Unsetting `URI` removes access to archive
storage and therefore also prevents restore; use `ENABLED=false` to pause.

Changing the configured URI or provider does not migrate existing objects.
Restore reads each object at its recorded URI, so the earlier location must
stay in place, and the server's credentials must still be able to read it. The
server image must keep the storage integration for the earlier provider installed.

## Which runs can be archived

Archiving considers finished runs in the selected target. They must meet
`AFTER_DAYS` unless a server admin explicitly uses `--force`. Runs linked to
model versions follow the same rules as other runs. Execution safety still
prevents archiving in these cases:

| Reason | Meaning |
| --- | --- |
| `not_eligible` | The run, one of its steps, one of its child runs, or a replay using it is still active, or a wait condition is unresolved. |
| `resumable_failed` | The failed dynamic run can still be resumed, including locally without a server-runnable build. |
| `root_active` | The run is a child of a root run that is still active or can still be resumed. Resuming a root reruns its child runs, which needs their details. |
| `oversized` | The run exceeds 50,000 archived rows. |

Each run is archived on its own, including child runs of dynamic pipelines. A
run's uncompressed archive document must fit within 64 MiB, and one capture
accepts at most 128 MiB of text and binary source values read from SQL. A run
that turns out larger during capture stays in the database and counts as
`oversized`. These are document and source-transfer
limits, not a process-memory limit: model validation, serialization, and
compression require additional working memory.

Each server process admits at most four retention payload operations at once
across archiving, unarchiving, and archive-object cleanup. Manual batches process
their runs sequentially within one admitted operation. This bound is local to
one replica, not cluster-wide. Concurrent archive requests recheck each
run under database locks before removing any detail.

## Archive specific runs now

Archive eligible runs in a selected pipeline or project, or name individual
runs:

```shell
zenml server retention archive --pipeline my-pipeline
zenml server retention archive --run-id <uuid> --run-id <uuid>
zenml server retention archive --project default
```

Archiving applies the configured minimum age. To archive newly finished
runs before that age, add
`--force`. Because it sets aside the policy the server admin configured,
`--force` requires a server admin. The confirmation identifies the override.
Active runs, resumable runs, and other execution-safety exclusions remain
protected even with force.

The CLI examines finished, unarchived runs in creation order, in batches of
up to 200. It automatically requests the next batch until the selected scan
is complete, reporting each batch's results. Refused runs do not stop the scan.
A batch with failed operations stops the command with a nonzero exit code;
resolve the failure and rerun it. Already archived runs are skipped.

The API and SDK return one batch with `pending` and `next_after_run_id`.
Pass that ID as `after_run_id` to continue. The CLI also accepts
`--after-run-id` for explicitly resuming at a known position. Stop the CLI
with Ctrl+C; an in-flight server request may still finish its current batch.

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

Status reports whether archive storage is configured, whether new archives
are enabled, and the minimum archive age. It does not scan runs or check
storage health. Reading it requires a server admin. Batch results are reported
by the archive command; the server does not maintain a sweep history.

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
retained information without restoring. Run, step, and snapshot responses expose
retained fields in `body.summary`, independently of the archive descriptor.
Existing full metadata fields remain available for unarchived entities. Summary
fields can be read without a detail fetch. Artifact links and log references stay in SQL;
log reads that do not need cold configuration do not require restore. The
artifact or log store must still be available to read its contents.

The bundled dashboard restores archived detail as part of the ordinary loading
state when a user deliberately opens a run page, a triggered child run's detail
sheet, or a create-snapshot page. Run lists and background refreshes remain
read-only and do not initiate a restore. Other dashboards and API clients must
handle the archived-detail 409 and call the restore route explicitly.

Use `is_archived=False` to filter to unarchived runs, steps, or snapshots when a caller
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

## Unarchive

Restore writes an archived run's detail back into the database:

```shell
zenml pipeline runs unarchive my-run
```

The command accepts a run name, ID, or unique ID prefix and finishes when the
run is restored. Restore is all-or-nothing: it needs every archived row to
still exist with its archive marker, and any mismatch returns **409** without
changing anything. A run that is not archived returns `noop`. There is no grace
period after unarchiving: a later manual archive command can archive the run
again if its original completion time meets the minimum age.

Restore requires read permission on the run, so a user who can open a run can
also make its cold detail available; the dashboard relies on this when it
restores a run as its page opens. A restore puts back exactly what that user
could read before the run was archived. Updating any run detail still requires
update permission. Restoring one run does not recursively restore its child
runs.

**Replay requires a restore first.** Replaying an archived run returns 409
with the restore command.

Deleting an archived run first restores its detail, then deletes the run.
Its snapshot remains readable and reusable, just as after deleting an
unarchived run. Deletion requires delete permission on the run and available
archive storage; if restoration fails, the run remains intact. Deleting the
run is **irreversible**. After the database deletion commits, the server
schedules asynchronous deletion of that run's archive objects. Deleting a
project also schedules cleanup of its archived runs' objects. Unarchiving
alone keeps the archive object.

Object cleanup is best effort and uses the server's existing maintenance
executor after SQL deletion commits. Each pass considers pending objects from
earlier deletions too, attempts at most 200 objects, and stops starting storage
calls after 30 seconds; an in-flight call may exceed that budget. Failed objects
keep their catalog entries and move behind older entries for later retries.
A busy executor, storage failure, or shutdown can leave cleanup pending until
another run or project deletion triggers it. Database deletion success does not
confirm object deletion has finished.

## API routes

| Method and route | Purpose | Permission |
| --- | --- | --- |
| `POST /api/v1/retention/archive` | Archive or preview named runs, a pipeline, or a project. | Update on the target and on every archived run; read for `dry_run=true`; server admin for `force=true` |
| `GET /api/v1/retention/status` | Read archive configuration. | Server admin |
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
into the current migrated schema and check supported response models. Legacy
steps without a snapshot ID can be archived and restored, but full-detail step
reads remain unsupported: step response metadata still requires a snapshot UUID.
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
3. **Archive objects stay available until their run is deleted.** Run and
   project deletion trigger asynchronous cleanup; failures retain catalog
   entries for a later retry. A process killed between upload and SQL commit
   can still leave an uncataloged object. Do not delete objects solely by age:
   a live archived run may still depend on them.
4. **Only archive format version 1 exists.** Other versions are integrity errors; there are no format adapters.
5. **Archived entries in detailed lists are summaries.** Check the archive
   descriptor before accessing cold detail; API clients restore explicitly
   when needed.
6. **No built-in scheduler or operation history.** Run archiving manually or
   schedule the CLI externally.
7. **No unarchive grace period or model-link exception.** The selected runs
   all follow the same minimum-age and execution-safety rules.
8. **Metadata, hook invocations, and run wait conditions stay in the database.**
9. **Shared snapshots stay in SQL,** including snapshots referenced by other
   archived runs. This keeps each run independently restorable but limits
   the payload that archiving can remove.

Physical reclamation remains separate database administration work. Measure
table and volume sizes after archiving, and use your own backup and
maintenance procedures if you rebuild tables. ZenML does not rebuild tables
or shrink volumes.
