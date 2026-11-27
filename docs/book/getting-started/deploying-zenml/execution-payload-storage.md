---
description: Storing large execution data once per distinct content.
---

# Execution payload storage

Every pipeline run stores large, write-once values in the ZenML database: the pipeline and step configurations of its snapshot, the pipeline spec, the client and orchestrator environments, and the source code and docstrings of its steps. On busy servers, these values make up a large share of the database and of its growth, and most of them are identical between runs of the same pipeline.

ZenML stores each distinct value once, in the `execution_payload` table of the same database, and the rows that need it hold a reference. Backups, restores and permissions stay as they are: there is no extra service, bucket or setting to configure. Everything else, such as names, statuses, timestamps, relationships, error details and descriptions, stays in the rows it belongs to.

## How it works

Once references are on (see below), the server writes the values of each new snapshot, step run and run to the table before it writes the rows that reference them. When a response needs them, for example the configuration of a run, the server reads them back with the row. Reads that only need database columns, such as lists without details, statuses and heartbeats, never touch the table. Stored values are never changed, and deleting runs, snapshots or pipelines does not delete them, since other runs can share them.

A database created by this release references values from the start. A database created by an older release keeps writing values inline, in the rows, because a server of an older release can still run against it during a rolling upgrade and cannot read references. The next ZenML release moves the values of existing rows into the table and then turns on references for new rows. A SQLite database, which only one process opens, starts referencing values when it is migrated.

## Upgrading

Upgrade the server as usual. The database migration adds the table and its columns, and records when it ran. Existing rows stay as they are, and on MySQL and MariaDB, new rows keep their values inline.

Before you upgrade to the next release, make sure that every server replica, and every other process that opens the database directly, such as [worker deployments](deploy-with-helm.md), runs this release: once the next release turns on references, older releases fail to read the affected runs. The next release waits a while after this migration before it switches, so upgrading through this release, rather than skipping it, lets it switch as soon as it starts.

## Limitations

* **Downgrade only while no values are stored.** Once values are stored in the table, ZenML releases that predate this feature cannot read the affected runs, and the database migration refuses to downgrade. Databases created by this release and SQLite databases store values from their first run; upgraded MySQL and MariaDB databases store none in this release.
* **Deleting does not erase the values.** Deleting runs, snapshots or pipelines does not delete the stored values, since other runs can share them. Their configurations, source code and environments then stay in the database and its backups, although no API returns them. Keep secrets out of step code and configurations, and use [secrets](../../how-to/secrets/secrets.md) instead.
