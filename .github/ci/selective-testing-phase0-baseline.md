# Selective Testing Phase 0 Baseline

## Purpose
This document defines the initial CI capacity guardrails and records the baseline metrics used to evaluate Phase 0/1 selective testing changes.

## Initial Capacity SLOs
- `ci-fast` integration queue-to-start p90: **<= 10 minutes**
- `ci-fast` integration queue-to-start p90 regression guard: **must not worsen by more than 20%** versus the baseline window
- Backlog rollback trigger for later phases: queue-to-start p90 **>= 15 minutes** for **24-48 hours**
- `ci-slow` queue-to-start p90 (provisional): **<= 20 minutes**
- `ci-slow` queue-to-start p90 regression guard: **must not worsen by more than 20%** versus the baseline window
- `ci-slow` backlog rollback trigger: queue-to-start p90 **>= 30 minutes** for **24-48 hours**

These thresholds are intentionally conservative because ZenML has a limited runner pool.

## Baseline Snapshot (captured February 21, 2026)
Source: `design/ci_selective_testing_investigation.md`

- `ci-fast` runs >= 5 minutes (sample n=45):
  - p50 wall-clock: **63.2 minutes**
  - p90 wall-clock: **258.9 minutes**
  - max wall-clock: **302.2 minutes**
- `ci-slow` runs >= 5 minutes (sample n=38):
  - p50 wall-clock: **102.5 minutes**
  - p90 wall-clock: **303.2 minutes**
  - max wall-clock: **496.4 minutes**
- Representative step timings from sampled runs:
  - `ci-fast` setup environment p50: **~1.3 minutes**
  - `ci-fast` sharded integration step p50: **~30.6 minutes**
  - `ci-slow` integration step p50: **~117.9 minutes**
- `ci-slow` queue-to-start p90 baseline: **TBD during refresh procedure**
- `ci-slow` runner-minutes baseline (`/timing` endpoint): **TBD during refresh procedure**

Interpretation: integration and migration execution are the dominant long poles; installation optimization is secondary unless future measurements show otherwise.

## Refresh Procedure
Use the following commands to refresh baseline numbers before changing capacity limits.
Replace `zenml-io/zenml` if you run this against a fork or mirror:

```bash
# Requires GitHub CLI auth with repo/workflow read access.
gh auth status

# Pull recent workflow runs for ci-fast and ci-slow.
gh api \
  "/repos/zenml-io/zenml/actions/runs?per_page=100&event=pull_request" \
  > /tmp/zenml-pr-runs.json

# For a given run id, inspect job queue and run duration details.
gh api "/repos/zenml-io/zenml/actions/runs/<RUN_ID>/jobs?per_page=100"

# Filter for ci-slow runs and capture queue-to-start timings.
gh api "/repos/zenml-io/zenml/actions/runs?per_page=100&event=pull_request&status=completed" \
  --jq '.workflow_runs[] | select(.name=="ci-slow") | {id,run_started_at,updated_at}'

# Runner-minute proxy (total)
gh api "/repos/zenml-io/zenml/actions/runs/<RUN_ID>/timing"
```

Record updated values in this file (with date and sample size) before adjusting selective-testing rollout gates.
For `ci-slow`, refresh queue-to-start p90 and runner-minutes baseline before enabling each subsequent rollout phase.
