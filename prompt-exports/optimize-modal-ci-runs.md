# Optimize: Modal CI Runtime

**Metric:** GitHub Actions job wall-clock duration for Modal-backed CI lanes, measured from job `started_at` to `completed_at` via the Actions jobs API.
**Stop criterion:** Both `linux-fast-modal / modal-fast-ci` and `ubuntu-latest-modal-server-mysql-integration-test / modal-server-mysql-offload` complete under 5 minutes on successful Modal runs.
**Scope:** `.github/workflows/linux-fast-modal.yml`, `.github/workflows/linux-modal-server-mysql.yml`, `offload.toml`, `offload-modal-server-mysql.toml`, `scripts/ci/modal_sandbox.py`, `scripts/ci/provision_modal_server.py`, `scripts/ci/create_modal_server_mysql_sandbox.sh`, and adjacent regression tests.

## Baseline Collection

Collected 2026-04-27 with public GitHub Actions API because local Modal credentials are not available and `gh` is not authenticated in this workspace.

Fast Modal samples from recent `ci-fast.yml` completed workflow runs on `feature/modal-ci-harness`:

| Run | SHA | Result | Duration | Notes |
|---|---|---|---|---|
| 10531 | 7c146ee9 | cancelled | 15m 16s | cancelled outlier |
| 10522 | 566ecb8b | success | 5m 34s | successful warm run |
| 10521 | 17f16658 | cancelled | 4m 58s | cancelled before full completion |
| 10520 | d2aa777e | success | 6m 11s | successful warm run |
| 10519 | 24832657 | success | 9m 55s | successful run, likely cold/noisy |
| 10518 | 3d24f91e | cancelled | 13m 24s | cancelled outlier |

Modal server MySQL samples from recent `ci-fast.yml` completed workflow runs on `feature/modal-ci-harness`:

| Run | SHA | Result | Duration | Notes |
|---|---|---|---|---|
| 10531 | 7c146ee9 | failure | 15m 58s | failure/outlier |
| 10522 | 566ecb8b | failure | 2m 23s | failed before a successful full run |
| 10521 | 17f16658 | failure | 0m 49s | early failure |
| 10520 | d2aa777e | failure | 0m 44s | early failure |
| 10519 | 24832657 | success | 5m 45s | only recent successful full run |

## Runs

| # | Change | Fast Modal Median | Fast Modal p95 | Server MySQL Median | Server MySQL p95 | Notes |
|---|---|---|---|---|---|---|
| baseline | Existing Modal offload workflow | 8m 03s all samples; 6m 11s successful-only median | 13m 24s all samples; 9m 55s successful-only p95 | 2m 23s all samples; 5m 45s successful-only sample | 5m 45s all non-outlier p95; 5m 45s successful-only sample | Target is <5m for successful full Modal runs. Fast lane is 34-295s over target depending on sample; server successful sample is 45s over target. |
| 1 | Add same-OS/Python `.offload-image-cache` restore fallback to both Modal workflows | Pending GitHub Actions re-measurement | Pending GitHub Actions re-measurement | Pending GitHub Actions re-measurement | Pending GitHub Actions re-measurement | Code updated in `linux-fast-modal.yml` and `linux-modal-server-mysql.yml`; regression coverage added for both restore steps. Bare `python -m pytest tests/unit/scripts/ci/test_modal_offload_config.py -q` could not start because `python` is unavailable in this workspace; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/unit/scripts/ci/test_modal_offload_config.py -q` (`6 passed`). No push/CI trigger was performed, so Actions wall-clock impact remains pending. |
