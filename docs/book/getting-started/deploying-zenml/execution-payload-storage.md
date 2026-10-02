---
description: Moving large execution data out of the ZenML database into an object store.
---

# Execution payload storage

Every pipeline run stores large, write-once values in the ZenML database: the pipeline and step configurations of its snapshot, the pipeline spec, the client and orchestrator environments, and the source code and docstrings of its steps. On busy servers, these values make up a large share of the database and of its growth.

Execution payload storage moves these values into an object store (Amazon S3, Google Cloud Storage or Azure Blob Storage). The database keeps a reference to each value, which is stored once per distinct content: runs of the same pipeline that share a configuration also share its stored copy. Everything else, such as names, statuses, timestamps, relationships, error details and descriptions, stays in the database.

Payload storage is disabled by default. Local deployments and servers without an object store keep every value in the database, as before.

## How it works

With offloading enabled, the server stores the values of each new snapshot, step run and run in the object store before it writes the rows that reference them. When a response needs them, for example the configuration of a run, the server reads them back. Each server process keeps recently read values in memory, and reads that only need database columns, such as lists, statuses and heartbeats, never touch the object store.

Values are addressed by the SHA-256 of their content. The server never overwrites or deletes them, and it verifies their size and hash on every read.

If the object store is unavailable, requests that need a stored value fail with a `503 Service Unavailable` error, which ZenML clients retry. Status updates, failure reporting, heartbeats and lists keep working: an update is saved, and answered without the stored values. After three failed calls in a row, the server stops calling the object store for the length of `backendTimeoutSeconds` before it tries again, so an outage does not tie up request threads.

## Prerequisites

* A bucket or container, with a prefix used only by ZenML payloads.
* Read and write access to the objects under the prefix, from every server pod or container, and from every other process that opens the ZenML database directly, such as [worker deployments](deploy-with-helm.md).
* **Versioning enabled** on the bucket, and **no lifecycle rule that expires or deletes current objects** under the prefix. The database references these objects for as long as the runs exist.

The server authenticates with the cloud identity of its environment: an IAM role for the service account on EKS (IRSA), Workload Identity on GKE, or a managed identity on AKS. Environment variables supported by the underlying storage libraries (`s3fs`, `gcsfs`, `adlfs`), such as `AWS_ACCESS_KEY_ID`, also work. Azure additionally needs the storage account name in `AZURE_STORAGE_ACCOUNT_NAME`.

## Configuration

### Helm

Configure the `server.database.payloadStorage` values:

```yaml
server:
  database:
    url: mysql://...
    payloadStorage:
      # Leave this off for the first rollout (see "Enabling offloading" below).
      offloadEnabled: false
      # `s3`, `gcs` or `azure`.
      backend: s3
      # Where values are stored: `s3://...`, `gs://...` or `az://...`.
      path: s3://my-bucket/zenml-payloads
      # Only for `s3`: the region, and the endpoint of an S3-compatible store.
      region: eu-central-1
      endpointUrl: ""
      # Bytes of values each server process keeps in memory (see below).
      cacheMaxBytes: 134217728
      # Seconds before a call to the object store fails the request.
      backendTimeoutSeconds: 10
      # Moves the values of existing runs once offloading is enabled (see
      # "Moving existing runs" below).
      backfill:
        enabled: true
        startDelaySeconds: 600
        batchSize: 200
        pauseSeconds: 0.2
        # Rebuild the tables afterwards to release disk space (see
        # "Reclaiming disk space" below).
        optimizeTables: false
```

The chart validates these values and passes them to the server through its Kubernetes secret. Each time a request stores or reads values, it fails within `backendTimeoutSeconds` however many values that covers, or about a second later if the storage client itself hangs. A request can store values and then read some, so keep `backendTimeoutSeconds` at half the server's request timeout (20 seconds by default) or less, so that clients get the storage error instead of a timeout.

Every server process, and every worker or Job that opens the database, keeps up to `cacheMaxBytes` (128 MiB by default) of loaded values in memory. Raise the memory limits of the server and of the workers by that much, or lower `cacheMaxBytes` where memory is tight: a smaller cache only means more reads from the object store. The cache bounds the values it keeps, not those that requests in flight hold until they answer.

### Docker

Set the `ZENML_STORE_PAYLOAD_STORAGE` environment variable of the server container to a JSON object:

```shell
docker run -it -d -p 8080:8080 --name zenml \
    --env ZENML_STORE_URL=mysql://root:password@host.docker.internal/zenml \
    --env ZENML_STORE_PAYLOAD_STORAGE='{"offload_enabled": false, "backend": "s3", "backend_config": {"path": "s3://my-bucket/zenml-payloads", "client_kwargs": {"region_name": "eu-central-1"}}}' \
    zenmldocker/zenml-server
```

`backend_config` holds the `path` and any option of the storage library, such as `client_kwargs` for `s3fs`. The other settings are `cache_max_bytes` and `backend_timeout_seconds`.

## Enabling offloading

A server release that predates payload storage cannot read stored values. So offloading is enabled in two steps:

1. Upgrade the server with `backend` and `path` configured and offloading disabled. Wait until every server replica, and every other process that opens the database, runs the new release with this configuration.
2. Enable offloading (`offloadEnabled: true`) and roll out again.

A single server that is restarted without overlap, such as a Docker container, can do both at once. Then [move the existing runs](#moving-existing-runs): with Helm, the upgrade of step 2 starts that.

Once the server holds stored values, `backend` and `path` cannot change: the server refuses to start with a different location (see [Moving the payloads](#moving-the-payloads)). Disabling offloading again is possible: new rows then keep their values in the database, and stored values remain readable, as long as `backend` and `path` stay configured.

## Moving existing runs

Offloading applies to new rows. Rows written earlier keep their values in the database until the backfill moves them. The backfill runs in its own process, with the server's configuration and cloud identity. It moves the values in small batches, updates each row once and only if the row did not change in the meantime, and can be stopped and started again at any time: a new run scans the tables again and moves what remains. Once it finds nothing left to move, it records that in the database, and later runs stop at once.

### Helm

With an external database (`database.url`), the chart starts the backfill by itself: the upgrade that sets `offloadEnabled: true` also creates a Kubernetes Job, named `<release>-payload-backfill-<hash>`. The Job waits `backfill.startDelaySeconds` (10 minutes by default), a buffer for the rolling restart to replace every server, then runs in its own pod: it doesn't use the server's CPU or memory, but it shares the database and the object store with it. On a large database it can take hours. Helm does not wait for it, and the Job of every later upgrade exits at once when the backfill has completed. `backfill.batchSize` and `backfill.pauseSeconds` set its pace; changing them replaces the running Job with one that waits its start delay again, then moves what the first one left.

```shell
# Follow the backfill
kubectl -n zenml get jobs -l app.kubernetes.io/component=payload-backfill
kubectl -n zenml logs -f job/<job name>
```

The Job succeeds once the backfill has completed, and fails otherwise: its logs say why, such as rows that could not be moved (see below), or rows that still changed after several passes because a process with offloading disabled keeps writing values into the database. Once the cause is fixed, delete the Job and run `helm upgrade` again, which creates it again, or run the command below from a server pod.

Argo CD shows the application as progressing until the Job finishes. Tools that wait for Jobs to complete fail the upgrade that enables offloading, since the Job takes longer than their timeout: don't pass `--wait-for-jobs` to Helm for that upgrade, and set `disableWaitForJobs: true` under `spec.install` and `spec.upgrade` of a Flux `HelmRelease`.

To run the backfill yourself instead, for example to review its report first, set `backfill.enabled: false` and use the command below from a server pod.

### Docker, ECS and other deployments

Run the backfill once, from the server's container or a container started like it, after the restart that enabled offloading has replaced every server:

```shell
docker exec -it zenml python -m zenml.zen_server.payload_backfill
```

On ECS, run a task from the server's task definition with the command overridden to `python -m zenml.zen_server.payload_backfill`.

### The backfill command

```shell
# Rows left to update and the bytes they still hold; writes nothing
python -m zenml.zen_server.payload_backfill --report
# Move them
python -m zenml.zen_server.payload_backfill --batch-size 200 --pause-seconds 0.2
```

`--report` reads the tables in full, so run it outside of peak hours on large databases. The backfill needs offloading to be enabled, and refuses to run otherwise. If offloading was disabled for a while and enabled again, the rows written in between stay in the database until you run the backfill with `--force`.

On a large MySQL database, keep in mind:

Every updated row is written to the binary log, which grows by about the size of the moved data. On a large MySQL database, watch the binary log size, the replication lag and the write latency, and increase `--pause-seconds` or lower `--batch-size` if they climb.

The backfill visits step runs first, then step configurations, snapshots and runs. If a row cannot be read, for example a step run whose configuration is missing, the backfill lists it and does not continue with the next table, since that table's values are needed to read the row. ZenML cannot display these rows either: delete what they belong to, such as the pipeline run of a listed step run (`zenml pipeline runs delete <run ID>`), then run the backfill again.

### Reclaiming disk space

MySQL and MariaDB keep the space that the moved values freed inside each table, and reuse it for new rows, so the database files do not shrink on their own. To release the space, rebuild the tables once the backfill has completed:

```shell
python -m zenml.zen_server.payload_backfill --optimize-tables
```

This runs `OPTIMIZE TABLE` on the four tables the backfill updated and logs the size of each before and after. With Helm, set `backfill.optimizeTables: true`: the Job then rebuilds them right after the backfill completes, or at once if it completed earlier. On a test database, the four tables went from 10.95 GiB to 2.05 GiB.

The rebuild runs online: reads and writes continue, apart from a short lock at the start and end of each table. It needs free disk space about the size of the table it rebuilds and takes a while on large tables, so run it outside of peak hours. On Amazon RDS, the released space returns to the instance's free storage, but its allocated storage does not shrink.

## Backups and restore

A backup of a server that stores payloads consists of the database and the bucket.

Since stored values are never overwritten or deleted, a database backup can be restored as long as the bucket still holds every object the backup references. Restore the bucket first, to a state no older than the database backup, then the database. Bucket versioning protects against objects deleted by mistake.

If the database is restored in another region from a replicated bucket, keep in mind that bucket replication is asynchronous: the replica can miss the most recent objects. Choose a database recovery point that the replica has caught up with.

## Moving the payloads

To move the payloads to another bucket or prefix, for example after a restore in another region, stop every process that writes them first: otherwise a server could store a new value at the old location after the copy, and it would be missing at the new one.

1. Stop every server, worker and backfill that uses the database, for example by scaling them to zero and disabling the backfill Job (`backfill.enabled: false`).
2. Copy every object of the old prefix to the new one, keeping the object names. Then check that every value the database registers is there, with its size: each `sha256` of the `payload_blob` table must be an object of `size_bytes` bytes at the new prefix. Counting objects is not enough, since the old prefix can also hold objects that were stored but never registered. For S3, for example:

```shell
# Registered values: `<sha256> <size>`
mysql -N -e "SELECT CONCAT(sha256, ' ', size_bytes) FROM payload_blob" zenml | sort > registered.txt
# Copied objects: `<name> <size>`
aws s3 ls s3://new-bucket/zenml-payloads/ | awk '{print $4, $3}' | sort > copied.txt
# Registered values missing from the copy, or copied with another size: must print nothing
comm -23 registered.txt copied.txt
```
3. Configure the new `path` and start one server. It refuses to start and names both locations, as fingerprints stored in the database, for example: ``Execution payloads are stored at the payload storage location `s3:3f1a9c2b7e04d`, not at the configured `s3://new-bucket/zenml-payloads` (`s3:9b2e71c40ad85`).``
4. Point the stored values to the new location, using both fingerprints from the message:

```sql
UPDATE payload_blob
SET location_fingerprint = 's3:9b2e71c40ad85'
WHERE location_fingerprint = 's3:3f1a9c2b7e04d';
```

5. Start the servers and other processes again, with the new `path`, and open a few runs in the dashboard, which reads their values from the new location.
6. Keep the old location until you are sure nothing reads from it anymore.

## Limitations

* **No downgrade.** Once values are stored in the object store, ZenML releases that predate payload storage cannot read the affected runs, and the database migration refuses to downgrade.
* **No cleanup.** Deleting runs, snapshots or pipelines does not delete their stored values, since other runs can share them.
* **One location.** All values are read from and written to the configured `path` (see [Moving the payloads](#moving-the-payloads)).
