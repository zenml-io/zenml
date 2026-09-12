# Optional fuzz tests

ZenML's generated filter, API, and CLI tests are separate from the ordinary
test suite. They run only through `scripts/fuzz.py`, which selects one suite,
backend, and profile and writes reproduction evidence to a new output
directory.

## Install

Create a dedicated environment beside an editable checkout. The server extra
is required by the API harness and is also used by CI:

```shell
uv venv --python 3.11 .venv-fuzz
uv pip install --python .venv-fuzz/bin/python \
  --requirement tests/fuzz/requirements.txt \
  -e ".[server]"
uv pip check --python .venv-fuzz/bin/python
```

## Run locally

Invoke the runner with an explicit suite, compatible backend, and profile:

```shell
.venv-fuzz/bin/python scripts/fuzz.py --suite filters --backend sqlite --profile local
.venv-fuzz/bin/python scripts/fuzz.py --suite api --backend sqlite --profile local
.venv-fuzz/bin/python scripts/fuzz.py --suite cli --backend none --profile local
```

Filter and API tests also support MySQL. Point them at an expendable MySQL 8.0
service account that can create and drop databases. The harness creates a
unique database whose name begins with `zenml_fuzz_` and refuses destructive
cleanup when it cannot prove that ownership:

```shell
export ZENML_FUZZ_MYSQL_URL='mysql+pymysql://root:password@127.0.0.1:3306/mysql'
.venv-fuzz/bin/python scripts/fuzz.py --suite filters --backend mysql --profile local
.venv-fuzz/bin/python scripts/fuzz.py --suite api --backend mysql --profile local
```

Use `--output-dir` to choose a new evidence directory. The runner refuses to
reuse an existing directory so an earlier failure cannot be overwritten.

## Reproduce a failure

The evidence directory records the source revision, exact pytest invocation,
dependency versions, backend details, seed, batch outcomes, logs, and the
Hypothesis example database. Rerun a single property using its pytest node ID:

```shell
.venv-fuzz/bin/python scripts/fuzz.py \
  --suite api \
  --backend sqlite \
  --profile local \
  --reproduce tests/fuzz/test_api.py::test_schema_generated_positive_requests \
  --output-dir fuzz-replay
```

If `run.json` contains a seed, pass it with `--seed` and `--batches 1` using
the same suite, backend, profile, and dependency lock. For a minimized failure
printed as a Hypothesis `@reproduce_failure(...)` blob, temporarily apply that
decorator to the named property and run the same node ID. Use a fresh output
directory for every replay.

The API suite starts the current checkout with Uvicorn, activates password
authentication, and uses a new SQLite file or MySQL database. The temporary
control credential is confined to that disposable server. Do not substitute a
personal ZenML server or database URL.

## CI behavior and budgets

Adding the `run-fuzz` label to a pull request targeting `develop` starts the
short five-job matrix, including on a draft. New commits, reopening the pull
request, and marking it ready for review rerun the matrix while the label is
present. Adding or removing an unrelated label neither starts nor cancels fuzz
work. Removing `run-fuzz` cancels that pull request's active fuzz run.

The nightly workflow runs at 02:30 UTC and can also be started manually with a
branch, tag, or SHA. Scheduled runs resolve `develop` once, then every matrix
job checks out that immutable revision. GitHub will not register the schedule
until the workflow exists on the repository's default branch, so calendar
activation remains pending until this change reaches that branch.

Each nightly suite/backend job restores its saved Hypothesis corpus before the
run. Hypothesis checks those prior examples and still generates fresh inputs;
the workflow saves the updated corpus under a new revision- and run-specific
cache key afterward.

Generation budgets exclude installation and service startup. Each local or PR
process also has a 15-minute hard limit; nightly processes have a 60-minute
hard limit.

| Suite and backend | Local | PR | Nightly |
|---|---:|---:|---:|
| Filters / SQLite | 1 minute | 3 minutes | 10 minutes |
| Filters / MySQL | 1 minute | 3 minutes | 10 minutes |
| API / SQLite | 3 minutes | 5 minutes | 10 minutes |
| API / MySQL | 3 minutes | 5 minutes | 40 minutes |
| CLI / none | 1 minute | 2 minutes | 5 minutes |

Both workflows run at most two matrix jobs at once. They upload each job's
evidence even after failure, retain it for 14 days, and fail if the evidence is
missing. Treat uploaded artifacts as public to everyone with repository read
access.

## Classify findings

The current issue-linked exclusions are recorded in
[known failures](known_failures.md).

Keep every failure visible until it has one of these dispositions:

- Correct a generator or oracle that contradicts an established contract, and
  add a focused check for the corrected expectation.
- Repair dependency, authentication, reset, database, or workflow failures in
  the fuzz infrastructure, then rerun the affected suite.
- For a small product defect within the targeted behavior, add a deterministic
  regression before making the narrow repair.
- For a broad, breaking, migration-related, or unrelated defect, preserve a
  synthetic reproduction and file a focused issue instead of expanding this
  change.
- For a security or data-integrity finding that cannot be contained safely,
  stop public reproduction, retain private evidence, and use ZenML's private
  security reporting process.

Do not turn a failure green with retries, a broad skip, or an unrestricted
`xfail`. A known noncritical exclusion must match the exact failure and link to
its issue; unexpected exceptions and unexpected passes must still fail.
