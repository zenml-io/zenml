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

**Entry points** (triggered externally): ci-fast.yml, ci-medium.yml, ci-slow-develop.yml, slow-ci-on-pr.yml, release.yml, nightly_build.yml, check-links.yml, check-markdown-links.yml, gitbook-redirect-check.yml, validate-changelog.yml, zizmor.yml

**Reusable workflows** (called via `workflow_call`): unit-test.yml, linting.yml, integration-test-*.yml, base-package-functionality.yml, publish_*.yml

Some entrypoint/orchestration workflows are also callable. For example, `ci-slow-develop.yml` exposes `workflow_call` so `slow-ci-on-pr.yml` can reuse the develop qualification matrix.

All reusable workflows use `secrets: inherit` for centralized secret management.

## CI Architecture

### ci-fast.yml (Every PR)

Runs automatically on all PRs, merge queue entries, and pushes to develop:
- SQLite migration testing
- Static checks (ubuntu, Python 3.13) — spellcheck, Ruff, and pydoclint
- Fast unit and non-slow integration coverage through `linux-fast-offload.yml`
- Fork PR fallback unit, default integration, and local MySQL integration coverage when Modal offload cannot run
- Separate Modal MySQL serial shared-state lane
- API docs buildability test

### ci-medium.yml (Merge Queue)

Runs merge-queue validation beyond fast PR checks:
- Random database migration coverage
- Python 3.13 linting and unit tests
- Modal-hosted MySQL integration coverage

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
- **Secrets inherit**: First-party workflows calling other first-party workflows

## Common Patterns

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

### Caching

uv cache key pattern:
```yaml
key: uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
```

Cache invalidates when integrations change.

Offload CI uses separate cache families:
- `offload-uv-v1`: runner-side uv downloads/build artifacts for offload driver setup and pytest collection dependencies.
- `offload-image-v2`: Modal image metadata. This intentionally excludes runtime fields such as CPU, memory, `max_parallel`, commands used after sandbox creation, and test filters.
- `offload-junit-v2`: offload JUnit duration seeds keyed by lane and test-selection inputs.

Restored offload JUnit XML is only a duration seed. It must not be treated as current test output unless `.ci/offload/junit.xml` is newer than `.ci/offload/run-start.marker`. Stale restored XML should be moved aside as `junit.stale.xml`.

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
