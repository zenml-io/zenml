---
description: Storing large execution data once per distinct content, and moving the data of existing runs.
---

# Execution payload storage

Every pipeline run stores large, write-once values in the ZenML database: the pipeline and step configurations of its snapshot, the pipeline spec, the client and orchestrator environments, and the source code and docstrings of its steps. On busy servers, these values make up a large share of the database and of its growth, and most of them are identical between runs of the same pipeline.

ZenML stores each distinct value once, in the `execution_payload` table of the same database, and the rows that need it hold a reference. Backups, restores and permissions stay as they are: there is no extra service, bucket or setting to configure. Everything else, such as names, statuses, timestamps, relationships, error details and descriptions, stays in the rows it belongs to.

## How it works

Once references are on (see below), the server writes the values of each new snapshot, step run and run to the table before it writes the rows that reference them. When a response needs them, for example the configuration of a run, the server reads them back with the row. Reads that only need database columns, such as lists without details, statuses and heartbeats, never touch the table. Stored values are never changed, and deleting runs, snapshots or pipelines does not delete them, since other runs can share them.

A database created with execution payloads references values from the start. A database created by an older release keeps writing values inline, in the rows, until the backfill described below has started, because a server that predates execution payloads cannot read references. A SQLite database, which only one process opens, starts referencing values when it is migrated.

## Upgrading

1. Upgrade the server. If the database predates execution payloads, the migration that adds the table and its columns records when it ran. New rows keep their values inline, as before.
2. An hour after that migration, the server runs the backfill by itself: it turns on references for new rows and moves the values of existing rows into the table.

Every server replica, and every other process that opens the database directly, such as [worker deployments](deploy-with-helm.md), must run a release that reads references before the backfill starts. A server that predates execution payloads and is still running then fails to read the moved runs. The release before this one added execution payloads but never turned them on: if every process ran it before you upgraded, the hour has usually passed, the backfill starts as soon as the new servers do, and every server it can meet during the rolling update already reads references. If you skip that release, the hour gives the rolling update time to replace every older server. If your upgrade can take longer than an hour, for example because several server deployments share one database, raise the delay, or set it to `0` and [run the backfill yourself](#the-backfill-command) once everything is upgraded. The delay is set in seconds through the `ZENML_SERVER_PAYLOAD_BACKFILL_DELAY` environment variable of the server, for example in the Helm values:

```yaml
server:
  environment:
    # Start the backfill four hours after the migration
    ZENML_SERVER_PAYLOAD_BACKFILL_DELAY: "14400"
```

## Moving existing runs

Every server starts the backfill once it is due, and only one of them runs it at a time: on MySQL and MariaDB, a database lock picks the runner, and the others wait for it to finish. The backfill first turns on references for new rows and waits a minute for the requests that started before. Then it moves the values of existing rows in small batches, updating each row once and only if the row did not change in the meantime. It passes over the tables again until a pass finds nothing left to move, which also catches rows that a process still writing inline added in the meantime, and records that in the database. Servers that start later see the record and do nothing.

The backfill can be stopped at any time. When the server running it shuts down, it stops after the current batch, and the next server to start continues where it stopped. If it does not complete, for example because a process keeps writing values inline or a row cannot be moved, the server logs why and tries again later, waiting longer each time, up to an hour.

On a large database, the backfill can take hours, and it shares the database with the requests the servers answer. Follow it in the server logs. On a MySQL or MariaDB database set to the `READ COMMITTED` isolation level instead of the default `REPEATABLE READ`, a request that lists step runs while the backfill moves their snapshot can fail with an error; repeating the request succeeds.

### Checking that the backfill is healthy

Each attempt that does not complete logs one warning with the reason and the time of the next attempt, for example `The payload backfill did not complete: ... It retries in 1m23s, at 2026-10-21 10:32:00 UTC.` A batch of rows to update that takes longer than 30 seconds also logs a warning, which can mean the database is under load or the batch waited on locks. To check the state at any time, run the command below with `--report`: it prints when the backfill last completed (`never` until it has) and, for each table, the rows it still has to update. A backfill that is healthy shows these numbers going down between two reports, and `Last completed` set once it is done. Numbers that stay the same across reports, while no server log shows backfill batches, mean it is stuck: the server warnings give the reason.

### The backfill command

```shell
# Rows left to update and the bytes they still hold; writes nothing and
# changes no setting
python -m zenml.zen_server.payload_backfill_runner --report
# Move them
python -m zenml.zen_server.payload_backfill_runner --batch-size 200 --pause-seconds 0.2
```

Run it from a server container or pod, with the server's configuration, for example `kubectl exec` into a server pod or `docker exec -it zenml ...`. `--report` reads the tables in full, so run it outside of peak hours on large databases. `--force` runs the backfill again after it has completed, for example after you stopped a process that wrote values inline. The log shows how long the batches of each table took (minimum, median, mean, maximum and total), to size the next run.

On a large MySQL database, keep in mind that every updated row is written to the binary log, which grows by about the size of the moved data. Watch the binary log size, the replication lag and the write latency, and increase `--pause-seconds` or lower `--batch-size` if they climb.

The backfill visits step runs first, then step configurations, snapshots and runs. If a row cannot be read, for example a step run whose configuration is missing, the backfill lists it and does not continue with the next table. ZenML cannot display these rows either: delete what they belong to, such as the pipeline run of a listed step run (`zenml pipeline runs delete <run ID>`). The servers then try again on their own, or you can run the backfill again.

### Reclaiming disk space

MySQL and MariaDB keep the space that the moved values freed inside each table, and reuse it for new rows, so the database files do not shrink on their own. To release the space, rebuild the tables once the backfill has completed:

```shell
python -m zenml.zen_server.payload_backfill_runner --optimize-tables
```

This runs `OPTIMIZE TABLE` on the four tables the backfill updated, and logs the size of each before and after. Until the backfill has completed, the command refuses to rebuild the tables; `--force --optimize-tables` runs the backfill first and rebuilds them if it completes.

The rebuild runs online: reads and writes continue, apart from a short lock at the start and end of each table. To take that lock, the rebuild waits for the transactions that use the table, and queries on the table wait behind it, so it waits at most 3 seconds: if a long transaction, such as a backup with `mysqldump --single-transaction`, keeps the table busy, the command fails, and you can run it again once that transaction has finished. It needs free disk space about the size of the table it rebuilds and takes a while on large tables, so run it outside of peak hours. On Amazon RDS, the released space returns to the instance's free storage, but its allocated storage does not shrink. SQLite databases are left as they are.

## Limitations

* **No downgrade.** Once values are stored in the table, which the backfill does for every database, ZenML releases that predate this feature cannot read the affected runs, and the database migration refuses to downgrade.
* **Deleting does not erase the values.** Deleting runs, snapshots or pipelines does not delete the stored values, since other runs can share them. Their configurations, source code and environments then stay in the database and its backups, although no API returns them. Keep secrets out of step code and configurations, and use [secrets](../../how-to/secrets/secrets.md) instead.
