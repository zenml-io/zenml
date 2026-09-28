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

If the object store is unavailable, requests that need a stored value fail with a `503 Service Unavailable` error, which ZenML clients retry. Status updates, failure reporting, heartbeats and lists keep working. After three failed calls in a row, the server stops calling the object store for the length of `backendTimeoutSeconds` before it tries again, so an outage does not tie up request threads.

## Prerequisites

* A bucket or container, with a prefix used only by ZenML payloads.
* Read and write access to the objects under the prefix, from every server pod or container, and from every other process that opens the ZenML database directly, such as [worker deployments](deploy-with-helm.md).
* **Versioning enabled** on the bucket, and **no lifecycle rule that expires or deletes current objects** under the prefix. The database references these objects for as long as the runs exist.

The server authenticates with the cloud identity of its environment: an IAM role for the service account on EKS (IRSA), Workload Identity on GKE, or a managed identity on AKS. Environment variables supported by the underlying storage libraries (`s3fs`, `gcsfs`, `adlfs`), such as `AWS_ACCESS_KEY_ID`, also work. Azure additionally needs the storage account name in `AZURE_STORAGE_ACCOUNT_NAME`.

## Configuration

### Helm

Configure the `zenml.database.payloadStorage` values:

```yaml
zenml:
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
      # Bytes of values each server process keeps in memory.
      cacheMaxBytes: 134217728
      # Seconds before a call to the object store fails the request.
      backendTimeoutSeconds: 10
```

The chart validates these values and passes them to the server through its Kubernetes secret. Keep `backendTimeoutSeconds` below the server's request timeout (20 seconds by default), so that clients get the storage error instead of a timeout.

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

A single server that is restarted without overlap, such as a Docker container, can do both at once.

Once the server holds stored values, `backend` and `path` cannot change: the server refuses to start with a different location (see [Moving the payloads](#moving-the-payloads)). Disabling offloading again is possible: new rows then keep their values in the database, and stored values remain readable, as long as `backend` and `path` stay configured.

## Moving existing runs

Offloading applies to new rows. Rows written earlier keep their values in the database until the backfill moves them. The backfill runs as a command with the server's configuration and cloud identity, for example inside a server pod or container:

```shell
# Kubernetes, with the name of the ZenML server deployment
kubectl -n zenml exec -it deploy/zenml-server -- python -m zenml.zen_server.payload_backfill --report
# Docker, with the name of the ZenML server container
docker exec -it zenml python -m zenml.zen_server.payload_backfill --report
```

`--report` only reads: it prints, for each table, the rows left to update and the bytes of values they still hold. It reads the tables in full, so run it outside of peak hours on large databases.

Without `--report`, the command moves the values of existing rows in small batches, and it can be stopped and run again at any time: it continues with the rows that remain. Each row is updated once, and only if it did not change in the meantime. The backfill needs offloading to be enabled, and it refuses to run otherwise.

```shell
python -m zenml.zen_server.payload_backfill --batch-size 200 --pause-seconds 0.2
```

On a large MySQL database, keep in mind:

* Every updated row is written to the binary log, which grows by about the size of the moved data. Watch the binary log size, the replication lag and the write latency, and increase `--pause-seconds` or lower `--batch-size` if they climb.
* MySQL does not return freed disk space to the operating system on its own. Tables shrink only after they are rebuilt, for example with `OPTIMIZE TABLE`, which is best done in a maintenance window.

The backfill visits step runs first, then step configurations, snapshots and runs. If a row cannot be read, for example a step run whose configuration is missing, the backfill lists it and does not continue with the next table, since that table's values are needed to read the row. Delete or fix the listed rows, then run the backfill again.

## Backups and restore

A backup of a server that stores payloads consists of the database and the bucket.

Since stored values are never overwritten or deleted, a database backup can be restored as long as the bucket still holds every object the backup references. Restore the bucket first, to a state no older than the database backup, then the database. Bucket versioning protects against objects deleted by mistake.

If the database is restored in another region from a replicated bucket, keep in mind that bucket replication is asynchronous: the replica can miss the most recent objects. Choose a database recovery point that the replica has caught up with.

## Moving the payloads

To move the payloads to another bucket or prefix, for example after a restore in another region:

1. Copy every object of the old prefix to the new one, keeping the object names.
2. Configure the new `path` and start the server. It refuses to start and names both locations, as fingerprints stored in the database, for example: ``Execution payloads are stored at the payload storage location `s3:3f1a9c2b7e04d`, not at the configured `s3://new-bucket/zenml-payloads` (`s3:9b2e71c40ad85`).``
3. Point the stored values to the new location, using both fingerprints from the message:

```sql
UPDATE payload_blob
SET location_fingerprint = 's3:9b2e71c40ad85'
WHERE location_fingerprint = 's3:3f1a9c2b7e04d';
```

4. Start the server again.

## Limitations

* **No downgrade.** Once values are stored in the object store, ZenML releases that predate payload storage cannot read the affected runs, and the database migration refuses to downgrade.
* **No cleanup.** Deleting runs, snapshots or pipelines does not delete their stored values, since other runs can share them.
* **One location.** All values are read from and written to the configured `path` (see [Moving the payloads](#moving-the-payloads)).
