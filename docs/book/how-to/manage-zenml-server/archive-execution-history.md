---
description: Bound metadata database growth by tiering old execution payload into object storage.
---

# Archive execution history

Execution-history archiving bounds future growth of large, immutable payload
columns in the ZenML metadata database. It exports eligible execution trees
as verified, compressed objects and can then remove the covered payload from
SQL. This makes database exports, upgrades, and workspace migrations smaller;
it does not automatically shrink already allocated database storage.

The policy belongs to the workspace. One execution tree consists of a root
pipeline run, its nested runs and steps, their snapshots, and step
configurations. The feature covers their source code, environments, exception
details, definitions, and other large execution payload fields. SQL identity
rows, relationships, indexes, artifact and run metadata, logs, and other
workspace tables remain in the metadata database and continue to grow
normally.

{% hint style="warning" %}
Archiving is disabled by default. Export is non-destructive. SQL compaction is
a separate phase protected by a deployment-level safety gate. Deploy the
archive-aware release to every server replica before enabling that gate.
{% endhint %}

## Configure archive storage

Archive storage is server infrastructure, not a registered stack component.
Configure the same official artifact-store flavor, destination, and path
prefix on every replica. For example:

```bash
export ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR=s3
export ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION='{"path":"s3://example-history"}'
export ZENML_SERVER_EXECUTION_ARCHIVE_PATH_PREFIX=execution-archive
```

The server instantiates ZenML's official artifact-store implementation
directly. Installed official local, S3-compatible, GCS, and Azure flavors are
supported without depending on a mutable registered component. The target
uses the server's ambient identity, such as an IAM role or workload identity.
Credential values and ZenML secret references are rejected from this
configuration.

The local flavor is suitable only when its path is durable and shared by every
server replica. Do not use pod-local or ephemeral filesystems for compacted
history.

Objects are isolated below the immutable workspace ID:

```text
<path>/<prefix>/workspaces/<workspace-id>/projects/<project-id>/execution-archives/<archive-id>/<claim-token>.json.gz
```

The validated flavor name, path prefix, and values explicitly supplied in the
target configuration are fingerprinted into every generation. Implementation
defaults added by a later ZenML release therefore do not change target
identity. Treat the configured target as immutable after the first export. A
changed target fails closed instead of making existing generations unreadable;
v1 target rotation requires restoring and purging every generation first.

Use object-store encryption, versioning, retention, and lifecycle controls
appropriate for your environment. Once a generation is compacted, its
historical payload is only as available as this destination.

{% hint style="danger" %}
A restored database clone carries the workspace ID, archive policy, catalog,
and purge queue of its source. Do not start a server for that clone with write
or delete access to the source workspace prefix. Omit archive storage for an
ordinary clone. A compaction rehearsal that needs stored objects must use an
operator-prepared, fully isolated copy of both the database and object data.
{% endhint %}

## Choose the workspace policy

The workspace policy has two editable values:

| Setting | Default | Meaning |
| --- | --- | --- |
| `mode` | `disabled` | `disabled`, verified `export`, or full `archive` |
| `retention_days` | `180` | Minimum age since both completion and the latest execution-tree mutation |

Configure it with the Python client:

```python
from zenml.client import Client
from zenml.enums import ExecutionArchiveMode

Client().update_execution_archive_policy(
    mode=ExecutionArchiveMode.EXPORT,
    retention_days=180,
)
```

Or use the CLI:

```bash
zenml server archive configure --mode export --retention-days 180
zenml server archive status
```

The modes are intentionally progressive:

- `disabled` starts no new exports or compactions. Interrupted compaction,
  restoration, and queued purge work still resumes so disabling the policy
  cannot strand data.
- `export` writes and verifies archive objects while SQL remains authoritative.
  Use this mode to validate eligibility, throughput, and storage permissions.
- `archive` exports and then compacts eligible execution trees. If the deployment
  safety gate is off, its effective behavior remains `export` and status says
  which switch is blocking compaction.

Changing retention restarts the coordinator's fair traversal. It affects
future automatic work and whether a manually requested, first-time compaction
may begin. It never interrupts recovery or restores generations that are
already cold.

## Enable SQL compaction

After export-only operation is healthy and every replica runs the
archive-aware release, enable the independent deployment gate:

```bash
export ZENML_SERVER_EXECUTION_ARCHIVE_COMPACTION_ENABLED=true
```

The gate applies when a verified generation first becomes authoritative. If
it is switched off later, an already-started compaction still resumes to a
safe terminal state.

Each replica wakes a bounded coordinator. A workspace-wide fenced lease means
only one replica performs work. The coordinator scans old root runs with a
stable keyset cursor, advances past permanently blocked execution trees, and
limits both inspected trees and object/SQL operations per pass. The defaults can
be tuned with these server settings:

```text
ZENML_SERVER_EXECUTION_ARCHIVE_COORDINATOR_INTERVAL
ZENML_SERVER_EXECUTION_ARCHIVE_SCAN_LIMIT
ZENML_SERVER_EXECUTION_ARCHIVE_WORK_LIMIT
ZENML_SERVER_EXECUTION_ARCHIVE_TIME_BUDGET
ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS
```

Server shutdown signals the current pass to stop between atomic archive
operations. An in-flight object write or SQL authority switch reaches its safe
boundary, but shutdown does not wait for a slow remote call before continuing.
The next coordinator resumes any unfinished lifecycle state.

The status command is safe for monitoring. It resolves the configured
artifact-store flavor and validates its configuration and credential policy
locally, then reads SQL counters and the cached result of the last pass. It
never performs a synchronous object-store health check, so
`storage: configured` does not prove remote permissions or availability. It
does prove that the target remains compatible with the target fingerprint
adopted by existing generations. The last pass separates eligible and blocked
execution trees and reports stable blocker categories. A true
`scan_incomplete` value means the pass stopped at a scan, work, time, or shutdown
boundary; it is not an estimate of the remaining backlog.

## Understand export, compaction, and restore

The server first inspects identities and payload sizes without loading an
unbounded object. Every pipeline run in the tree must have status `completed`.
Individual steps may use any finished status, including `cached`, `skipped`,
or `retried`. The server also rejects a tree when a step is still active, a
snapshot is shared or remains an operational definition, runtime work remains
attached, the payload exceeds 128 MiB, or the tree contains more than 10,000
payload-bearing rows.

For an eligible execution tree, export:

1. inspects identities and payload sizes without loading an unbounded object;
2. rejects active, shared, operational, or oversized trees, with hard
   bounds on both payload bytes and row count;
3. captures every covered payload row;
4. writes one compressed, self-describing object to an immutable,
   fencing-token-scoped key;
5. reads back and checksum-verifies the stored bytes;
6. decodes and validates the complete object contract; and
7. captures SQL again and compares a semantic source fingerprint.

The generation then reaches `verified`. If SQL changed during export, SQL
remains authoritative and a retry creates or refreshes the correct generation.

In `archive` mode, compaction reads and validates the object again, locks the
complete execution tree, and compares its current fingerprint. It atomically
marks every run and snapshot as archived before replacing covered SQL payload
with compact markers in bounded, resumable batches. The lifecycle is
`verified` → `compacting` → `cold`.

There is no transparent object-store hydration. Payload-free list summaries
remain available, while a request that requires compacted payload returns a
typed HTTP 409 containing the archive ID. Restore is explicit and
checksum-verifies the object before writing payload back in bounded batches.
Only after all surviving rows are restored are the execution-tree fences
cleared. The lifecycle is `cold` → `restoring` → `restored`.

Use the CLI for an explicit execution tree or generation:

```bash
zenml server archive export <ROOT-RUN-ID> --project <PROJECT>
zenml server archive list --project <PROJECT>
zenml server archive compact <ARCHIVE-ID> --project <PROJECT>
zenml server archive restore <ARCHIVE-ID> --project <PROJECT>
```

Manual export is an intentionally non-destructive diagnostic. It may verify an
explicit execution tree even while the workspace policy is `disabled` or the
tree is younger than the retention period, and it never changes SQL authority.
Manual first-time compaction is destructive and therefore requires workspace
mode `archive`, retention eligibility, and the deployment compaction gate.
Those switches do not block an already-started `compacting` generation from
finishing safely.

New runs, steps, operational snapshot references, and updates cannot modify a
cold execution tree until it is restored. Deleting an individual cold run or
snapshot is also refused: partial deletion would break the tree closure and
make restoration ambiguous. Restore the tree first, perform the deletion, and
archive the remaining history again if needed.
Interrupted export, compaction, restoration, and purge operations are
idempotent and fenced. Write attempts use distinct object keys, so an expired
worker cannot overwrite the object committed by a newer worker. Failed
attempts are removed on a best-effort basis, and generation purge removes the
whole isolated generation directory so interrupted cleanup cannot leak old
attempt objects permanently. When a newer verified generation replaces an
older non-authoritative one, the older generation is queued for the same
retryable purge path.

The three source reads serve different safety boundaries: the first builds the
export, the second detects changes made while the object was uploaded, and the
third runs under row locks immediately before SQL authority moves. Removing
one would leave a different concurrent-write window unchecked.

## Purge archived objects

A live project cannot purge a generation that owns its only complete payload;
restore it first. Queue a safe generation with:

```bash
zenml server archive purge <ARCHIVE-ID> --project <PROJECT>
```

Purge removes one generation; it is not a per-tree exclusion. An enabled
workspace policy may export the still-eligible execution tree again on a later
pass.

Project deletion never waits for object storage. In the same SQL transaction,
it marks every project generation as purge-pending and retains the plain,
immutable project UUID needed to locate the objects. The coordinator then
deletes each generation directory before deleting its catalog row. Failures
are retried and cannot make database deletion depend on object-store
availability.

If an entire workspace database is destroyed, its local purge queue is also
destroyed. The deployment control plane must therefore retain the workspace
prefix and delete it as part of workspace-level deprovisioning.

## API authorization

The CLI and Python client use these protected endpoints. Without RBAC, callers
must be administrators. With RBAC enabled, callers need the corresponding
pipeline-run `read` or `update` permission at the workspace, project, or exact
root-run scope enforced by each operation:

```text
GET  /api/v1/archive/policy
PUT  /api/v1/archive/policy
GET  /api/v1/archive/status
POST /api/v1/archive/export
GET  /api/v1/archive?project_id=<PROJECT-ID>&state=<STATE>
GET  /api/v1/archive/<ARCHIVE-ID>?project_id=<PROJECT-ID>
POST /api/v1/archive/<ARCHIVE-ID>/compact
POST /api/v1/archive/<ARCHIVE-ID>/restore
POST /api/v1/archive/<ARCHIVE-ID>/purge
```

Export accepts `project_id` and `root_run_id`. Compact, restore, and purge
accept `project_id` in their JSON request body.

The product-coordination migration refuses to downgrade while authority work
or object purge is outstanding. Removing the archive foundation additionally
requires restoring every compacted generation and purging every stored
generation, so a downgrade cannot lose authoritative data or orphan known
objects.
