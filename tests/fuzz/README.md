# Optional fuzz tests

ZenML's generated filter, API, and CLI tests stay outside the ordinary test suite (`collect_ignore = ["fuzz"]` in `tests/conftest.py`). Run them through `scripts/fuzz.py`, which sets up an isolated environment, streams live output to `fuzz.log`, and records `run.json` in a fresh output directory.

## Install

Create a dedicated virtual environment beside an editable checkout (`uv` resolves `tests/fuzz/requirements.txt` jointly with `pyproject.toml`):

```shell
uv venv --python 3.11 .venv-fuzz
uv pip install --python .venv-fuzz/bin/python \
  --requirement tests/fuzz/requirements.txt \
  -e ".[server]"
uv pip check --python .venv-fuzz/bin/python
```

## Run locally

```shell
.venv-fuzz/bin/python scripts/fuzz.py --suite filters --backend sqlite --profile local
.venv-fuzz/bin/python scripts/fuzz.py --suite api --backend sqlite --profile local
.venv-fuzz/bin/python scripts/fuzz.py --suite cli --backend none --profile local
```

For MySQL 8.0, point `ZENML_FUZZ_MYSQL_URL` at a disposable service account that can create and drop databases. Each run creates a uniquely named `zenml_fuzz_*` database using the server's default collation (`utf8mb4_0900_ai_ci` on MySQL 8.0) and drops it on exit:

```shell
export ZENML_FUZZ_MYSQL_URL='mysql+pymysql://root:password@127.0.0.1:3306/mysql'
.venv-fuzz/bin/python scripts/fuzz.py --suite filters --backend mysql --profile local
.venv-fuzz/bin/python scripts/fuzz.py --suite api --backend mysql --profile local
```

Profiles control Hypothesis's `max_examples` (`local`: 25, `pr`: 100, `nightly`: 500) and the hard wall-clock timeout (`local`/`pr`: 15 minutes, `nightly`: 55 minutes) with a 60-second `SIGTERM` teardown grace period before `SIGKILL`.

## Reproduce a failure

Each run preserves `run.json`, `fuzz.log`, `junit.xml`, and (for API failures) `api-failures.jsonl`, `api-coverage.json`, and `api-server.log`, plus the Hypothesis example database.

Rerun a single test with `--reproduce` (and `--seed` or the printed `@reproduce_failure(...)` decorator):

```shell
.venv-fuzz/bin/python scripts/fuzz.py \
  --suite api \
  --backend sqlite \
  --profile local \
  --reproduce tests/fuzz/test_api.py::test_generated_requests_conform_to_api_contract \
  --output-dir .fuzz-results/replay
```

To replay a saved nightly corpus, extract the uploaded artifact's `.fuzz-corpus/<suite>-<backend>` directory and set `ZENML_FUZZ_CORPUS_DIR` to its path before running `scripts/fuzz.py`.

## CI workflows

- **PR workflow (`.github/workflows/fuzz-pr.yml`):** Adding the `run-fuzz` label to a PR targeting `develop` runs the PR profile across SQLite, MySQL 8.0, and CLI. Removing the label cancels active runs.
- **Nightly workflow (`.github/workflows/fuzz-nightly.yml`):** Runs at 02:30 UTC (once present on the repository's default branch) against one immutable `develop` SHA, or on demand via `workflow_dispatch`. Hypothesis corpora are restored before each run and saved with `if: always()` so failing examples carry over to subsequent nights. Scheduled failures or timeouts automatically open a deduplicated GitHub issue labeled `fuzz-nightly`.

## Known mismatches

Tracked product mismatches and strict `xfail` canaries are documented in [known_failures.md](known_failures.md).
