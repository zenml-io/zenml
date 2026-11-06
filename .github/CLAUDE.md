# ZenML GitHub Actions Guidelines

This document provides guidance for AI assistants working with ZenML's GitHub Actions workflows.

## Workflow Organization

### Categories

| Category | Workflows | Purpose |
|----------|-----------|---------|
| **CI/Testing** | ci-fast.yml, ci-slow.yml, unit-test.yml, integration-test-*.yml, base-package-functionality.yml | Primary PR testing and reusable test jobs |
| **Linting/Quality** | linting.yml, spellcheck.yml, zizmor.yml, check-links.yml, check-markdown-links.yml, gitbook-redirect-check.yml, validate-changelog.yml | Code quality, docs links, changelog, and workflow security checks |
| **Release/Nightly** | release.yml, release_prepare.yml, release_finalize.yml, publish_*.yml, nightly_build.yml | PyPI, Docker, Helm, stack template, and nightly publishing |
| **Security** | codeql.yml, trivy-*.yml, zizmor.yml | Static analysis and vulnerability/supply-chain scanning |
| **Maintenance** | stale-prs.yml, pr_labeler.yml, require-release-label.yml, snack-it.yml, notify-*.yml, dependabot.yml | Repo automation and project notifications |
| **Special/Examples** | templates-test.yml, update-templates-to-examples.yml, vscode-tutorial-pipelines-test.yml, weekly-agent-pipelines-test.yml, performance-profiling.yml | Template syncing, tutorial/example regression tests, and profiling |

### Entry Points vs Reusable Workflows

**Entry points** (triggered externally): ci-fast.yml, ci-slow.yml, release.yml, nightly_build.yml, check-links.yml, check-markdown-links.yml, gitbook-redirect-check.yml, validate-changelog.yml, zizmor.yml

**Reusable workflows** (called via `workflow_call`): unit-test.yml, linting.yml, integration-test-*.yml, base-package-functionality.yml, publish_*.yml

All reusable workflows use `secrets: inherit` for centralized secret management.

## Two-Tier CI Architecture

### ci-fast.yml (Every PR)

Runs automatically on all PRs and pushes to main:
- Spellcheck
- SQLite migration testing
- Linting (ubuntu, Python 3.11) — includes Ruff, pydoclint, yamlfix, zizmor, and mypy
- Unit tests (ubuntu, Python 3.11)
- Integration tests (default and docker/MySQL environments, sharded, with test lanes).
  The docker/MySQL environment is the only place the example projects run against a
  real MySQL-backed server, so every PR runs all of it.
- API docs buildability test
- Template example updates (PRs only, same-repo only)

### ci-slow.yml (Full Matrix, Requires Label)

Gated by `run-slow-ci` label (checked dynamically):
- Multi-OS: Ubuntu, Windows, macOS
- Multi-Python: Ubuntu runs the most versions, macOS and Windows only the oldest and
  newest they support (see the matrices)
- Tests run in shards and test lanes (see below). Tests start independently of lint in
  both CI workflows; slow CI still requires the label. Lint failures still fail the
  workflow, but tests can use runner time even when lint fails. There is no Windows or
  macOS lint job: ruff and
  pydoclint do not depend on the OS, and `mypy-platforms` type-checks the Windows and macOS
  `sys.platform` branches from Ubuntu with `mypy --platform`.
- Full database migration tests (MySQL, MariaDB, SQLite)
- VSCode tutorial pipeline tests
- Base package functionality tests

**Label mechanism**: Maintainers add `run-slow-ci` label and rerun workflow to trigger full CI without code changes.

## Release Process

Triggered by tag push. Sequence:

1. Unit tests (ubuntu, Python 3.11)
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
- **Secrets inherit**: First-party workflows calling other first-party workflows

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
  ZENML_LOGGING_VERBOSITY: debug
  ZENML_ANALYTICS_OPT_IN: false
  ZENML_DEBUG: true
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

All CI workflows use:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This cancels previous runs when new commits are pushed to the same branch.

### Path Filtering

ci-fast and ci-slow ignore:
- `docs/**` - Documentation changes
- `*.md` - Markdown files
- `.claude/**` - Claude configuration
- `.github/workflows/claude.yml` - Claude workflow

But explicitly include `pyproject.toml` changes.

### Test sharding

Sharded jobs pass `--splits`/`--group` to pytest-split, which balances the shards by
per-test time from `.test_durations` at the repo root. Without that file the shards are
split by test count and finish minutes apart. Every shard and lane is its own pytest
process, so the script gives them all one `--randomly-seed` per workflow run: with
pytest-randomly's per-process seeds, pytest-split breaks ties between equally long tests
differently in each process and some tests run twice while others never run. `generate-test-duration.yml` refreshes it
weekly by opening a pull request (a direct push to `develop` is rejected). The generator
uses the workflow token to publish a pending `check-label` on the exact generated commit
after verifying that the PR changes only `.test_durations`. It then verifies that the PR
is still open at that commit with exactly one release label before completing the check.
If verification or completion fails, the check cannot pass.
Concurrent refreshes wait for the previous run. The repository must enable
"Allow GitHub Actions to create and approve pull requests". Scheduled Monday runs use
the workflow on the default branch, `main`, so this automation must reach `main` before
the schedule uses it. The reusable
`unit-test.yml`, `integration-test-fast.yml` and `integration-test-slow.yml` take a
`shards` input, a JSON list such as `'[1, 2, 3]'`; the shard count is the length of that
list.

### Test lanes

The org can run only a limited number of jobs at once (20 Linux/Windows, 5 macOS), and a
hosted runner has more CPU cores than one pytest process keeps busy. So a shard runs
several pytest processes ("lanes") side by side: `scripts/test-coverage-xml.sh` reads
`TEST_LANES`, which the reusable workflows pass from their `lanes` input, and splits the
shard's tests between the lanes with pytest-split. Each lane has a private deployment
root, and lanes without a server provision their own database, so they never share state.

Against a docker server only tests that work in their own project are safe side by side.
The script puts the paths in `SHARED_STATE_PATHS` (the example and integration tests,
which use the default project and prune docker resources daemon-wide, and the `zen_stores`
tests, which work on the server's own store) in one lane of their own whenever a run
includes them; nothing has to be passed for that. New functional tests must isolate
themselves (see `tests/integration/functional/conftest.py`).
`--cleanup-docker` is not passed when lanes are used, and other server types run one
lane. Raise the lane count only after checking that a contended runner still finishes each
shard sooner.

### Caching

There is deliberately no uv cache. It was branch-scoped, so almost every run missed, and
restoring a multi-GB cache was no faster than installing from PyPI while saving it added a
minute to every job. Measure before adding one back.

### Disk space

`actions/free_disk_space` only deletes preinstalled toolchains when a Linux runner is short
of space, so it costs nothing on the current large images.

## Key Supporting Files

| File | Purpose |
|------|---------|
| `actions/setup_environment/action.yml` | Composite action for Python + ZenML dev setup |
| `actions/free_disk_space/action.yml` | Composite action that frees Ubuntu disk space only when it is short |
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

### publish_staging_workspace_runtime.yml

Dispatches a `zenml-develop-updated` repository event to `zenml-cloud-plugins` on every push to `develop`, carrying the exact merge SHA. That repository builds and publishes the internal staging workspace image; this repo only needs the `CLOUD_PLUGINS_REPO_PAT` secret. Gated to the upstream repository so forks never fail on the missing secret.

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

6. **Two-tier CI requires label**: Full CI only runs with `run-slow-ci` label - maintainers add this for thorough testing

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
