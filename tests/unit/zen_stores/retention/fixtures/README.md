# Frozen version-one restore fixture

These files contain synthetic data only. `v1-manifest.json` and
`v1-rows.tar.gz` freeze the four-section, metadata-free V1 format.
`v1-sql.json` stores the source SQL expectations and retained dependencies once.
The compatibility test derives the archived rows using an explicit frozen V1
clearing contract, then restores through the public store API and compares every
detail field, including retained `step_type` and finalized `substitutions`.
Public run, step, snapshot, list, and DAG parity is covered by the separate
round-trip test across static, dynamic, and legacy configuration ownership.

The behavior suite and generator share an independent schema-backed graph
builder. That builder never reads these files or imports a test module. Behavior
tests create fresh identities; explicit generation uses fixed synthetic identities
and timestamps. Tests read frozen bytes for compatibility checks but never call
the generation entry point.

For an intentional format-fixture replacement, use the existing local environment:

```sh
PYTHONPATH=src python -m tests.unit.zen_stores.retention.fixture_graph
```

Use `--output-dir /path/to/empty-directory` to inspect regeneration separately.
Generation builds typed records directly, creates no database, and writes only
the three V1 files after removing its temporary JSONL sections. Repeated generation
produces byte-identical SQL expectations, compressed records, and manifest,
including its fixed synthetic bundle ID. V1 timestamps are naive UTC, matching
SQL storage.

This fixture was intentionally replaced while defining the initial V1 format;
no deployed bundles predate it. Do not regenerate it merely to make a later
compatibility test pass. There are no legacy metadata sections or adapters.

Execution retention tests run only on MySQL. Point
`ZENML_RETENTION_TEST_MYSQL_URL` at a disposable server; each test session
creates and drops its own database:

```sh
docker run --name zenml-retention-mysql --rm -d -p 3307:3306 \
  -e MYSQL_ROOT_PASSWORD=<local-only> mysql:8
ZENML_RETENTION_TEST_MYSQL_URL=mysql://root:<local-only>@127.0.0.1:3307 \
  pytest tests/unit/zen_stores/retention
```

Without the variable the tests skip. CI passes `--require-retention-mysql` so
a missing database fails instead.
