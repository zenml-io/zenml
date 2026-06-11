# ZenML GitHub Actions Guidelines

This document provides guidance for AI assistants working with ZenML's GitHub Actions workflows.

## Workflow Organization

### Categories

| Category | Workflows | Purpose |
|----------|-----------|---------|
| **CI/Testing** | ci-fast.yml, ci-medium.yml, ci-slow-develop.yml, slow-ci-on-pr.yml, unit-test.yml, integration-test-*.yml, base-package-functionality.yml | Primary PR, merge-queue, develop qualification, and reusable test jobs |
| **Linting/Quality** | linting.yml, spellcheck.yml, zizmor.yml, check-links.yml, check-markdown-links.yml, gitbook-redirect-check.yml, validate-changelog.yml | Code quality, docs links, changelog, and workflow security checks |
| **Release/Nightly** | release.yml, release_prepare.yml, release_finalize.yml, publish_*.yml, nightly_build.yml | PyPI, Docker, Helm, stack template, and nightly publishing |
| **Security** | codeql.yml, trivy-*.yml, zizmor.yml | Static analysis and vulnerability/supply-chain scanning |
| **Maintenance** | stale-prs.yml, pr_labeler.yml, require-release-label.yml, snack-it.yml, notify-*.yml, dependabot.yml | Repo automation and project notifications |
| **Special/Examples** | templates-test.yml, update-templates-to-examples.yml, vscode-tutorial-pipelines-test.yml, weekly-agent-pipelines-test.yml, performance-profiling.yml | Template syncing, tutorial/example regression tests, and profiling |

### Entry Points vs Reusable Workflows

**Entry points** (triggered externally): ci-fast.yml, ci-medium.yml, ci-slow-develop.yml, slow-ci-on-pr.yml, release.yml, nightly_build.yml, check-links.yml, check-markdown-links.yml, gitbook-redirect-check.yml, validate-changelog.yml, zizmor.yml, offload-image-warm.yml

**Reusable workflows** (called via `workflow_call`): unit-test.yml, linting.yml, integration-test-*.yml, base-package-functionality.yml, publish_*.yml, offload-tests.yml

Some entrypoint/orchestration workflows are also callable. For example, `ci-slow-develop.yml` exposes `workflow_call` so `slow-ci-on-pr.yml` can reuse the develop qualification matrix.

All reusable workflows use `secrets: inherit` for centralized secret management.

## CI Architecture

### ci-fast.yml (Every PR)

Runs automatically on all PRs, merge queue entries, and pushes to develop:
- SQLite migration testing (random, sqlite only)
- Static checks (ubuntu, Python 3.13) — spellcheck, Ruff, and pydoclint
- Serial-only tests (ubuntu, Python 3.13) — tests marked `@pytest.mark.serial_only`
  that must not run in parallel Modal sandboxes
- API docs buildability test
- Template example updates (same-repo, non-draft PRs only)

**For same-repo, non-dependabot PRs when Modal is enabled:**
- `offload-unit-tests` — unit test suite on Modal via offload (required)
- `offload-integration-tests` — integration test suite on Modal via offload (required)

**Fallback (fork PRs, dependabot, or `ZENML_CI_MODAL_DISABLED=true`):**
- `unit-test` — runner-based unit tests via `unit-test.yml`
- `default-integration-test` — runner-based default-environment integration tests

Both the offload lanes and the runner lanes are in the `ci-fast-required` rollup with
`allowed-skips` for whichever side is inactive, so exactly one path is required at a time.

### ci-medium.yml (Merge Queue)

Runs merge-queue validation beyond fast PR checks:
- Random database migration coverage (MySQL, MariaDB, SQLite) with random seed per run
- Python 3.13 linting (via `linting.yml`) and unit tests (via `unit-test.yml`)
- Docker-orchestrator MySQL integration tests (via `integration-test-fast.yml`)
- Base package functionality tests (via `base-package-functionality.yml`)
- `remote-mysql-modal-offload` — integration suite against a Modal-hosted MySQL server
  (skipped when `ZENML_CI_MODAL_DISABLED=true`; docker-orchestrator-mysql provides coverage)

### ci-slow-develop.yml and slow-ci-on-pr.yml (Develop Qualification)

`ci-slow-develop.yml` runs scheduled/manual develop qualification and can be called by other workflows. `slow-ci-on-pr.yml` triggers that same slow matrix for a PR when maintainers add the `run-slow-ci` label.

The slow matrix includes:
- Multi-OS: Ubuntu, Windows, macOS
- Python 3.10, 3.11, 3.12, and 3.13 coverage where supported by the lane
- Full database migration tests (MySQL, MariaDB, SQLite)
- VSCode tutorial pipeline tests
- Base package functionality tests

`slow-ci-on-pr.yml` is advisory for labeled PRs and must not publish develop-red incidents; only scheduled/manual develop qualification should do that.

## Release Process

Triggered by tag push. Sequence:

1. Unit tests (ubuntu, Python 3.13)
2. Database migration tests (MySQL, SQLite, MariaDB) - parallel
3. Publish to PyPI (trusted publishing with OIDC)
4. Wait 4 minutes (PyPI CDN propagation)
5. Publish Docker image (Google Cloud Build)
6. Publish Helm chart (AWS ECR Public)
7. Wait 4 minutes
8. Publish stack templates
9. Tag zenml-cloud-plugins repo

## Security Hardening with zizmor

[zizmor](https://woodruffw.github.io/zizmor/) is a GitHub Actions security linter. Configuration is in `.github/zizmor.yml`.

### Running zizmor locally

```bash
# Run analysis using the repo config; uvx installs/runs zizmor in one step
GH_TOKEN=$(gh auth token) uvx zizmor --config=.github/zizmor.yml .github/workflows/

# Auto-fix SHA pinning (IMPORTANT: requires GH_TOKEN and manual review)
GH_TOKEN=$(gh auth token) uvx zizmor --fix=all --config=.github/zizmor.yml .github/workflows/
```

**Critical**: zizmor requires `GH_TOKEN` (not `GITHUB_TOKEN`) environment variable for SHA lookups when auto-fixing.

### Current Security Posture

**Enforced:**
- All actions SHA-pinned (prevents supply chain attacks)
- Malformed conditional detection
- Template injection detection (with documented exceptions)

**Disabled with TODOs:**
- `excessive-permissions`: Many workflows use default permissions. Audit incrementally.
- `artipacked`: Many workflows need `persist-credentials: true` for pushing commits.

### Documented Exceptions in zizmor.yml

- **Unpinned uses**: ZenML template repos intentionally stay on `@main` branch
- **Template injection**: Step outputs within same workflow are trusted
- **Cache poisoning**: Protected release branch workflows (docs only)
- **Secrets inherit**: First-party workflows calling other first-party workflows,
  including `offload-tests.yml` (called by ci-fast.yml and ci-medium.yml;
  `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET` flow through without per-call-site
  enumeration)
- **artipacked (pending)**: `artipacked` rule is globally disabled. When it is
  re-enabled, `offload-image-warm.yml` must be listed as an explicit
  exception — it intentionally uses `persist-credentials: true` to push
  `refs/notes/offload-images` to the protected `develop` branch.

## Common Patterns

### Dependency and security audit gating

When a security/audit tool needs custom pass/fail policy, prefer a three-step
workflow shape:

1. A read-only PR/push job gathers raw tool output, writes a Markdown summary to
   `$GITHUB_STEP_SUMMARY`, and uploads larger JSON/Markdown reports as artifacts.
2. A small read-only gate job consumes only compact outputs such as counts,
   booleans, and result flags, then decides the final CI status.
3. Any issue or repository mutation runs in a separate scheduled/manual-only job
   with the narrow write permission it needs (for example `issues: write`).

Keep PR and push paths read-only. Do not grant write permissions to the audit or
gate jobs just because scheduled maintenance needs them.

### Environment Variables

Standard settings used across workflows:

```yaml
env:
  ZENML_DEBUG: true
  ZENML_ANALYTICS_OPT_IN: false
  PYTHONIOENCODING: utf-8
  UV_HTTP_TIMEOUT: 600
```

For testing stability:
```yaml
env:
  ZENML_LOGGING_VERBOSITY: INFO
  AUTO_OPEN_DASHBOARD: false
  ZENML_ENABLE_RICH_TRACEBACK: false
  TOKENIZERS_PARALLELISM: false
```

### Concurrency

Most CI workflows use:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This cancels previous runs when new commits are pushed to the same branch. Qualification workflows can intentionally differ; for example, `ci-slow-develop.yml` keeps in-progress develop qualification runs instead of canceling them.

### Path Filtering

Path filtering is workflow-specific. Do not assume required aggregate workflows can skip docs-only changes; required rollup jobs may still need to report a status even when expensive test jobs are skipped. Check each workflow's `paths`, `paths-ignore`, and job-level conditions before changing branch protection behavior.

`ci-fast.yml` does not use `paths-ignore` — docs-only PRs run the full ci-fast suite. This is intentional: the ci-fast rollup is a required check on PRs and merge-queue entries, so it must always report a status regardless of changed files. The extra runner minutes for docs-only PRs are the price of reliable required-status reporting.

### Caching

uv cache key pattern:
```yaml
key: uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
```

Cache invalidates when integrations change.

`generate-test-duration.yml` refreshes `.test_durations` on a weekly schedule. This file feeds `pytest-split` sharding in the runner-based integration lanes (ci-fast and ci-slow-develop). Do not delete or rekey `.test_durations` without also updating the workflows that consume it; stale shard data degrades test parallelism but does not break correctness.

## Modal Execution via offload (PR 2)

### offload-tests.yml — the reusable offload workflow

`offload-tests.yml` (~150 lines) replaces the old 502-line `linux-fast-offload.yml`. It
accepts three inputs: `suite` (unit|integration|integration-mysql), `environment`
(default|remote-mysql-modal), and `parallel` (max sandboxes).

Lifecycle:
1. Checkout with `fetch-depth: 50` so offload's `[checkpoint]` can locate the
   build-input ancestor.  Fetches `refs/notes/offload-images` for the image cache.
2. Install offload v0.9.7 from the pre-built binary, cached by version string.
3. Install driver-side ZenML dependencies via `uv pip install -e ".[server,templates,dev]"`.
4. Copy `Dockerfile.ci.dockerignore` to `.dockerignore` (offload reads `.dockerignore`
   from cwd, not from the Dockerfile-named file).
5. *(integration-mysql only)* Start the Modal MySQL sandbox via `modal_mysql_sandbox.py start`.
6. Run `offload -c <lane>.toml run --parallel N --record-history --ci`.
7. *(integration-mysql only, `always()`)* Stop the sandbox.
8. Upload `.ci/offload` artifacts (junit.xml + offload logs) for failure inspection.

Exit codes: 0 = pass, 2 = flaky-only (only with `retry_count > 0`), 1 = failed.
Exit 0 and 2 are both treated as success; exit 1 fails the job.

Modal auth: `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` are job-level env vars inherited
via `secrets: inherit`. They are absent on fork PRs and dependabot PRs — callers
must route those to the runner fallback (see ci-fast.yml conditions).

No coverage upload: offload lanes run plain `pytest` with no `coverage run`
instrumentation. This is a deliberate decision — the complexity of running coverage
inside Modal sandboxes and merging distributed reports is not worth it at this stage.
Coverage was never present for the offload path; this is not a regression.

### offload TOML config files (THREE standalone files)

offload v0.9.7 has no `include`/`extends` mechanism and no per-run group-selection
CLI flag, so three standalone TOML files are required (one for each test group).
The plan's "one config" ideal (§2.1) was superseded by these verified v0.9.7 facts.

| File | Group | Key settings |
|------|-------|-------------|
| `offload-unit.toml` | `tests/unit -m 'not serial_only'` | `max_parallel=2` |
| `offload-integration.toml` | `tests/integration -m 'not slow and not serial_only'` | `max_parallel=20` |
| `offload-integration-mysql.toml` | `tests/integration -m 'not slow and not global_state'` | `max_parallel=20` |

Select a lane with `offload -c <file> run ...`.  Never `cp` over `offload.toml`.

`${VAR:-default}` expansion is valid ONLY in `[provider.env]` values.  Do NOT use
`${...}` in `[framework].run_args` or `[groups.*].filters` — it is not expanded there.

### offload version pin

offload is pinned to **v0.9.7** (crates.io upstream, not a fork).  There is NO fork
reference anywhere in the workflow or TOML files.  An unexplained fork pin is a
`CHANGES_REQUESTED` blocker per the PR review guidelines.

To upgrade: bump the version string in `offload-tests.yml` and `offload-image-warm.yml`
(two cache keys + two install steps), then verify the new version's TOML schema
against the field list in the TOML comments.

### Image cache via git notes

offload stores Modal image IDs in `refs/notes/offload-images`.  The `[checkpoint]`
section in each TOML specifies `build_inputs = ["Dockerfile.ci", "pyproject.toml"]`;
offload reuses the cached image when the most recent ancestor commit that touched
any build input is the same as the last build.  This requires `fetch-depth: 50`
(not 0 or 1) so the ancestor lookup succeeds.

PR jobs run with `contents:read` and cannot push notes.  The separate
`offload-image-warm.yml` workflow (triggered by push to develop when
`Dockerfile.ci` or `pyproject.toml` changes) runs with `contents:write` and
`persist-credentials: true` to warm the cache.

Security posture of `offload-image-warm.yml`: `persist-credentials: true` is a
deliberate exception to the repo-wide `persist-credentials: false` posture.  It
is scoped to a single workflow that only runs on `push` to the protected `develop`
branch (a trusted ref, no pull-request trigger).  The artipacked rule in
`zizmor.yml` is globally disabled; when it is re-enabled, `offload-image-warm.yml`
must be listed as an explicit exception.

The notes push in `offload-image-warm.yml` is `continue-on-error: true` because
concurrent develop pushes can race.  A missed warm is non-critical (next PR run
rebuilds the image).

### Dual timing systems

The codebase intentionally maintains TWO test timing systems:

| File | Purpose | Feeds |
|------|---------|-------|
| `.test_durations` | pytest-split shard weights | runner-lane integration tests |
| `offload-history.jsonl` | offload LPT scheduling | offload-based test lanes |

Do not remove either file.  `generate-test-duration.yml` refreshes `.test_durations`
weekly.  `offload-history.jsonl` is updated by `--record-history` on every offload run
(merge driver configured in `.gitattributes` handles concurrent updates).

### Kill switch

`vars.ZENML_CI_MODAL_DISABLED=true` routes all test execution to GitHub runner lanes:
- In `ci-fast.yml`: offload lanes are skipped; `unit-test` and `default-integration-test`
  runner jobs become active.
- In `ci-medium.yml`: `remote-mysql-modal-offload` is skipped; the always-present
  `docker-orchestrator-mysql-integration-test` provides database integration coverage.

The kill switch is a repository variable (`vars.*`), not a secret.

### Fork and dependabot routing

Fork PRs (`github.event.pull_request.head.repo.full_name != github.repository`) do not
have access to repo secrets, so offload lanes would fail to authenticate with Modal.

Dependabot PRs are same-repo but get Dependabot secrets instead of repo secrets, so
`MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` are absent — the same fallback applies.

Both cases are handled by the static condition on offload lanes in `ci-fast.yml`:
```yaml
&& github.event.pull_request.head.repo.full_name == github.repository
&& github.actor != 'dependabot[bot]'
&& vars.ZENML_CI_MODAL_DISABLED != 'true'
```

### merge_group double-run policy

`ci-fast.yml` fires on both `pull_request` and `merge_group`.  When a PR is merged,
offload lanes run twice — once for the PR head SHA and once for the merge-queue
temporary merge commit.  This is intentional: the merge-queue commit is a different
SHA (squash or merge), so re-running tests against it is correct.  The extra Modal
cost per merge is bounded and accepted.

## Key Supporting Files

| File | Purpose |
|------|---------|
| `actions/setup_environment/action.yml` | Composite action for Python + ZenML dev setup |
| `zizmor.yml` | Security linter configuration used by `scripts/lint.sh` and `.github/workflows/zizmor.yml` |
| `codecov.yml` | Coverage reporting (lenient thresholds) |
| `dependabot.yml` | Weekly GitHub Actions updates on Tuesdays 07:00 Europe/Amsterdam, grouped by minor/patch updates with cooldowns |
| `teams.yml` | Internal team members for privileged workflows |
| `branch-labels.yml` | Auto-labeling rules based on branch patterns |
| `markdown_check_config.json` | Markdown link checker configuration |

## Template Workflows

### update-templates-to-examples.yml

Syncs external template repos to `examples/` folder:
- `zenml-io/template-e2e-batch` → `examples/e2e`
- `zenml-io/template-nlp` → `examples/e2e_nlp`
- `zenml-io/zenml-project-templates` → `examples/mlops_starter`
- `zenml-io/template-llm-finetuning` → `examples/llm_finetuning`

**Important**: These template repos use `@main` branch intentionally and are excluded from SHA pinning.

### templates-test.yml

Tests template compatibility by running test actions from template repos. Failure indicates breaking changes that need template updates.

## Special Workflows

### claude.yml

AI code review integration. Triggered by `@claude` mentions in issues/PRs. Gated to internal team members via `teams.yml`.

### snack-it.yml

Creates tracking issues from PRs when `snack-it` label is applied. Adds to GitHub Projects roadmap.

### zizmor.yml

Runs GitHub Actions security analysis on workflow/config changes, pushes to `main`/`develop`, a weekly schedule, and manual dispatch. Use the same config locally with `GH_TOKEN=$(gh auth token) uvx zizmor --config=.github/zizmor.yml .github/workflows/`.

### check-links.yml / check-markdown-links.yml / gitbook-redirect-check.yml

Documentation link safety net. Use these as the source of truth when changing docs URL structure, generated API docs, or GitBook redirects.

### weekly-agent-pipelines-test.yml / vscode-tutorial-pipelines-test.yml

Regression tests for example/tutorial/agent pipelines. If a code change affects pipeline authoring, dynamic pipelines, or example behavior, mention these workflows in the PR so maintainers know whether to rerun them.

## Important Gotchas

1. **GH_TOKEN for zizmor**: Use `GH_TOKEN=$(gh auth token)` not `GITHUB_TOKEN` for SHA lookups

2. **Template repos stay unpinned**: The 4 template repositories in `update-templates-to-examples.yml` intentionally use `@main` - don't SHA-pin them

3. **zizmor strips subdirectory paths**: Actions with subdirectory paths like `github/codeql-action/init@SHA` or `zenml-io/template-e2e-batch/.github/actions/e2e_template_test@main` get incorrectly "fixed" by zizmor to just `github/codeql-action@SHA` (stripping `/init`). This breaks workflows. After running `zizmor --fix`, manually verify and restore any stripped subdirectory paths. Common affected actions:
   - `github/codeql-action/init` (Initialize CodeQL)
   - `github/codeql-action/analyze` (Perform CodeQL Analysis)
   - `github/codeql-action/upload-sarif` (Upload SARIF results)

4. **secrets: inherit is intentional**: Zizmor warns about this but it's the correct pattern for first-party reusable workflows

5. **Run format.sh before commits**: YAML files must pass yamlfix (`bash scripts/format.sh .github/`)

6. **Slow CI entry points differ**: Advisory PR slow CI runs when maintainers add the `run-slow-ci` label; develop qualification runs through `ci-slow-develop.yml` on its own scheduled/manual/callable paths

7. **Release waits are intentional**: The 4-minute sleeps in release.yml allow PyPI CDN propagation

8. **Don't modify examples/ directly**: This folder is auto-updated by CI from template repos

## Formatting Workflows

Always run before committing workflow changes:

```bash
bash scripts/format.sh .github/
```

This runs yamlfix on YAML files to ensure consistent formatting.

## Adding New Workflows

1. Use SHA-pinned actions with a version comment: `actions/checkout@<full-sha>  # v6.0.2`
2. Add appropriate concurrency settings
3. Include standard environment variables
4. Consider if it should be reusable (`workflow_call`)
5. Run zizmor to check for security issues
6. Update this document if adding new patterns
