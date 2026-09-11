# Frozen version-one restore fixture

These files contain synthetic data only:

- `v1-document.json.gz` is the archive object of one two-step run in format
  version 1.
- `v1-bundle.json` describes its bundle row: identities, size, and the hash
  of the decoded content.
- `v1-sql.json` holds the run's SQL rows before archiving.

The compatibility test clears the detail columns using the frozen version 1
contract, inserts the bundle row, restores through the public store API, and
compares every detail field with `v1-sql.json`.

Version 1 was redefined before release, when archives became one JSON
document per run. No deployed bundles predate this fixture. Do not regenerate
it to make a later compatibility test pass; a format change needs a new
version and adapters, not a new golden file.

For an intentional replacement:

```sh
PYTHONPATH=src:. python -m tests.unit.zen_stores.retention.fixture_graph
```

Use `--output-dir /path/to/empty-directory` to inspect regeneration
separately. Generation uses fixed synthetic identities and timestamps and
needs no database; repeated runs produce byte-identical files.

## Running the suite

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
