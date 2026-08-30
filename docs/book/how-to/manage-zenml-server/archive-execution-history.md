---
description: Keep old execution history available without keeping its large payloads in the metadata database.
---

# Archive execution history

Execution archiving moves the large, immutable payload of completed pipeline
runs — snapshot configurations, step configurations, source code,
environments, exception details — out of the metadata database into object
storage, while every run, step and snapshot stays listable, filterable and
readable exactly as before. When an archived run is opened, the server loads
its payload from the archive, verifies it and returns the same response it
would have returned from the database.

{% hint style="info" %}
Archiving is explicit and administrator-driven: nothing is archived until an
administrator runs a pass; nothing leaves the database in this
version. Archiving never touches artifact or log data, and this
version never deletes archived objects.
{% endhint %}

This feature bounds snapshot, step-configuration, and execution payload growth
for eligible completed execution families. It does not yet archive failed or
stopped families, artifact metadata, run metadata, logs, relationships, or
other SQL records.

## Configure the archive storage

Archive storage is server infrastructure, not a stack component. Configure it
on every server replica with an artifact store flavor (`s3`, `gcp`, `azure`,
`local`, an S3-compatible service through the `s3` flavor's `client_kwargs`,
or a custom flavor), its configuration and a path prefix:

```bash
export ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR=s3
export ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION='{"path": "s3://example-archive-bucket/workspace"}'
export ZENML_SERVER_EXECUTION_ARCHIVE_PATH_PREFIX=execution-archive
```

The server authenticates to the destination with its own identity — an IAM
role, workload identity or credentials in its environment; the configuration
holds no credentials. The first archive pass writes a small probe object and
reads it back, and records the configuration as an immutable storage target
that every archive written under it points to. Changing the configuration
records another target; archives written to the previous one keep being read
from it, so never remove a destination that still holds archives.

{% hint style="warning" %}
A `local` destination is safe for a server with several replicas only when its
path is a shared, durable volume mounted at the same location on every
replica. Archives written through a ZenML integration flavor (`s3`, `gcp`,
`azure`, …) can only be read by replicas that have that integration installed;
archives written through a custom flavor depend on the import path recorded
when the target was created.
{% endhint %}

Bucket versioning, retention, encryption and lifecycle rules are properties of
the destination and stay under the operator's control. Archive objects are
content-addressed and verified by their SHA-256 digest on every read, so a
destination that returns corrupt or missing data fails closed: the request
returns HTTP 503 instead of incomplete history.

## Preview and export

Administrators preview what a pass would archive without writing anything:

```text
POST /api/v1/archive?dry_run=true
```

```json
{
  "project": "<PROJECT-ID>",
  "older_than_days": 180,
  "limit": 25
}
```

The request may also name the `root_run_ids` to consider. A family is
eligible once every run and step in it completed, nothing in it is still
waiting or active, its snapshots are used by nothing else, its payload is
below 128 MiB in the database, and its last change is older than
`older_than_days`. The response lists every considered family with its
eligibility, its payload size in the database and what blocks it. A dry run
reads identities and sizes only, never payload.

The same request with `dry_run=false` runs the pass on the server's
maintenance worker, one family at a time, and returns a task ID immediately;
search the server logs for it to follow progress. A second maintenance task
while one is running is rejected with HTTP 429.

An export writes the family's objects to the storage target, reads them back,
verifies them against a fresh capture of the database and records the
generation as `verified`. **The database keeps its payload and stays the
source of truth**; a verified archive is a checked copy. A family whose
payload changes between export and verification is recorded as `failed` and
archived again as a new generation on the next pass.

List archives with `GET /api/v1/archive?project_id=<PROJECT-ID>`, optionally
filtered by `state`.

## Compaction ships separately

Replacing the database payload of verified archives with a placeholder —
compaction — ships in a later release, after every server replica runs a
version that can read archived payload. Until then the database keeps every
byte and a verified archive is a checked copy.

## Downgrading

The database migration that introduces archiving refuses to downgrade while
any archive is still authoritative for rows in the database. Restore every
archive listed as `compacting`, `cold` or `restoring` first.
