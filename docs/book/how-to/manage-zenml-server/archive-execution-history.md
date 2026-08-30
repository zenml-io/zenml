---
description: Store verified copies of old execution payload outside the metadata database.
---

# Archive execution history

Execution-history archiving moves selected immutable pipeline-run payload to a
separate storage tier. Its purpose is to bound future growth of large payload
columns and make database exports and workspace migrations smaller. It does
not shrink provisioned database storage automatically.

This feature covers pipeline snapshots, run and step payload fields, source
code, environments, exception details, and step configurations in a closed
execution tree. An execution tree is one root pipeline run together with its
nested runs, steps, snapshots, and step configurations. SQL identity rows,
indexes, artifact and run metadata, logs,
relationships, and other workspace tables remain in the metadata database and
continue to grow normally.

{% hint style="warning" %}
The export endpoint in this release is a non-destructive administrator tool.
It creates a verified object but does not remove or replace any SQL payload.
SQL remains authoritative until compaction support is enabled in a later
release.
{% endhint %}

## Configure the storage tier

Archive storage is server infrastructure, not a registered stack component.
Configure the same official artifact-store flavor, destination, and path
prefix on every server replica. For example:

```bash
export ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR=s3
export ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION='{"path":"s3://example-history"}'
export ZENML_SERVER_EXECUTION_ARCHIVE_PATH_PREFIX=execution-archive
```

The server builds the existing ZenML artifact-store implementation directly.
This supports installed official local, S3-compatible, GCS, and Azure artifact
store flavors without depending on a mutable registered component. The target
must use the server's ambient identity, such as an IAM role or workload
identity. Credential values and ZenML secret references are rejected from the
archive configuration.

The target identity includes its complete validated configuration, path
prefix, and immutable workspace ID. Treat it as immutable after the first
export. Archive operations fail closed if it differs from an existing catalog
entry; restore and purge existing generations before deliberately moving the
archive tier.

Use object-store encryption, versioning, retention, and lifecycle controls
appropriate for your environment. Once SQL is compacted in a later release,
historical payload availability also depends on this destination.

## Export one execution tree

An administrator can export a specific root run:

```text
POST /api/v1/archive/export
```

```json
{
  "project_id": "<PROJECT-ID>",
  "root_run_id": "<ROOT-RUN-ID>"
}
```

The server first inspects identities and payload sizes without loading an
unbounded object. Every pipeline run in the tree must have status `completed`.
Individual steps may use any finished status, including `cached`, `skipped`,
or `retried`. The server also rejects a tree when a step is still active, a
snapshot is shared or remains an operational definition, runtime work remains
attached, the payload exceeds 128 MiB, or the tree contains more than 10,000
payload-bearing rows.

For an accepted execution tree, the server:

1. captures every covered payload row;
2. claims one catalog generation with a fenced lease;
3. writes one deterministic, compressed, self-describing object;
4. reads and checksum-verifies the stored bytes;
5. decodes and validates the complete object contract;
6. captures SQL again and compares a semantic source fingerprint; and
7. records the generation as `verified`.

If SQL changes during the operation, the generation fails and SQL remains
authoritative. A retry exports the changed source as a new generation. If an
existing verified object no longer matches its checksum or format, the catalog
records it as `corrupt` while the untouched SQL payload remains usable.

List generations with
`GET /api/v1/archive?project_id=<PROJECT-ID>`, optionally filtered by `state`.
Get one generation with
`GET /api/v1/archive/<ARCHIVE-ID>?project_id=<PROJECT-ID>`.

## Current read and downgrade behavior

Ordinary hot reads do not contact archive storage. This release never writes
archive markers, so existing reads and writes retain their current behavior.
The schema already contains fail-closed conversion guards needed by later
compaction support: if a future compacted row is encountered, a full-payload
request returns a typed HTTP 409 that names the archive to restore, while
payload-free list summaries remain available.

The database migration refuses to downgrade while any future archive is
authoritative. Verified-only generations do not block downgrade because SQL
still contains their full payload.
