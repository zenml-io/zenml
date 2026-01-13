---
name: gha-debugger
description: Debug GitHub Actions CI failures for ZenML. Use when the user mentions CI failure, GitHub Actions failure, workflow failed, build failed, tests failing in CI, ci-fast failed, ci-slow failed, or needs help understanding why a PR check failed.
allowed-tools:
  - AskUserQuestion
  - Bash
  - Read
  - Grep
  - Glob
  - WebFetch
  - WebSearch
---

# GitHub Actions CI Debugger for ZenML

This skill helps diagnose and debug CI failures in ZenML's GitHub Actions workflows.

## Gather Context First

**Use the `AskUserQuestion` tool to clarify before diving in.** A few quick questions can save significant debugging time. Good questions to ask:

1. **Which PR or branch?** - "Which PR number or branch is failing?"
2. **Which job failed?** - "Do you know which specific job failed (e.g., linting, unit-test, integration-test)?"
3. **Is it just your PR?** - "Is this failure specific to your PR, or have you seen it failing on other PRs too?"
4. **What changed?** - "Did you recently change any dependencies or integration code?"
5. **When did it start?** - "Was this working before? When did it start failing?"

Example using AskUserQuestion:
```
Questions:
1. "Is this failure specific to your PR, or affecting multiple PRs?"
   - Options: ["Just my PR", "Multiple PRs / develop branch too", "Not sure"]
2. "Which job is failing?"
   - Options: ["Linting/type errors", "Unit tests", "Integration tests", "Not sure - need to check"]
```

Don't be afraid to ask - it's much faster than guessing and running the wrong diagnostics!

---

## First: Determine the Failure Type

**Ask the user or determine from context which type of failure this is:**

### Type A: PR-Specific Failure (Local Debugging)
> "My PR is failing CI" / "I have linting errors" / "My tests are failing"

**Characteristics:**
- Failure is specific to your PR/branch
- Your code changes likely caused it
- Other PRs or `develop` branch are passing
- Usually: linting, type errors, docstrings, test failures from your changes

**→ Jump to: [Local Debugging Workflow](#local-debugging-workflow-type-a)**

### Type B: Systemic/Flaky Failure (Cross-PR Investigation)
> "This test has been failing all week" / "Multiple PRs are hitting this" / "We've been ignoring this failure"

**Characteristics:**
- Failure appears across multiple PRs
- Your code changes didn't cause it
- Often started failing after a dependency release or infrastructure change
- Usually: dependency upgrades, flaky tests, external service issues

**→ Jump to: [Systemic Failure Investigation](#systemic-failure-investigation-type-b)**

---

# Local Debugging Workflow (Type A)

For failures caused by your PR's code changes. These are usually quick to fix locally.

## Quick Fixes by Job Type

### Linting Failures (`linting` job)

```bash
# Run the full linting suite locally
bash scripts/lint.sh

# Or run mypy on just your changed files (much faster)
mypy src/zenml/path/to/your/changed/file.py

# Find files you changed
git diff --name-only origin/develop | grep "\.py$"

# Run mypy on all your changed Python files
git diff --name-only origin/develop | grep "\.py$" | xargs mypy
```

### Docstring Failures (`docstring-check` job)

```bash
# Run darglint locally
bash scripts/docstring.sh

# Or check specific files
darglint src/zenml/path/to/your/file.py
```

Common docstring issues:
- Missing parameter documentation (`DAR101`)
- Missing return documentation (`DAR201`)
- Parameter name mismatch (`DAR102`)

### Spellcheck Failures (`spellcheck` job)

```bash
# Run typos locally
typos .

# Fix the typo, OR add to .typos.toml if it's a valid word:
```

```toml
# .typos.toml
[default.extend-words]
myword = "myword"
```

### Unit Test Failures (`unit-test` job)

```bash
# Run the specific failing test locally
pytest tests/unit/path/to/test_file.py::test_function_name -v

# Run with more verbosity
pytest tests/unit/path/to/test_file.py -vvs

# Run all unit tests (slower)
pytest tests/unit/ -v
```

### Type Errors in Your Code

```bash
# Quick mypy check on your changes
git diff --name-only origin/develop | grep "\.py$" | xargs mypy --ignore-missing-imports

# Check a specific module
mypy src/zenml/your_module/ --ignore-missing-imports
```

## Getting the Actual Error from CI

```bash
# Get your PR's check status
gh pr checks <PR_NUMBER> --repo zenml-io/zenml

# Get the failed logs
gh run view <RUN_ID> --repo zenml-io/zenml --log-failed | head -100
```

---

# Systemic Failure Investigation (Type B)

For failures that affect multiple PRs and aren't caused by specific code changes.

## Step 1: Confirm It's Systemic

```bash
# Check if develop branch is also failing
gh run list --branch develop --repo zenml-io/zenml --limit 10

# Check recent runs across all branches for the same job
gh run list --repo zenml-io/zenml --workflow "ci-fast.yml" --limit 20

# See if multiple PRs have the same failing job
gh pr list --repo zenml-io/zenml --state open --json number,title,statusCheckRollup --jq '.[] | select(.statusCheckRollup != null) | {number, title, checks: [.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name]}'
```

## Step 2: Find When It Started Failing

```bash
# Look at recent workflow runs to find when failures started
gh run list --repo zenml-io/zenml --workflow "ci-fast.yml" --limit 50 --json conclusion,createdAt,headBranch --jq '.[] | "\(.createdAt) \(.headBranch): \(.conclusion)"'

# Find the last successful run of develop
gh run list --branch develop --repo zenml-io/zenml --status success --limit 5
```

## Step 3: Identify the Root Cause

### If it's a dependency issue (most common):

Jump to **[Dependency Upgrade Breakage](#1-dependency-upgrade-breakage-most-common)** in the failure patterns section.

### If it's a flaky test:

```bash
# Check if the test has "rerun" in the logs (indicates flakiness)
gh run view <RUN_ID> --log-failed | grep -i "rerun"

# Look for timing-related or resource-related errors
gh run view <RUN_ID> --log-failed | grep -iE "timeout|connection|refused|unavailable"
```

### If it's infrastructure-related:

```bash
# Check for Docker/container issues
gh run view <RUN_ID> --log-failed | grep -iE "docker|container|image|pull"

# Check for disk space issues
gh run view <RUN_ID> --log-failed | grep -iE "no space|disk full|ENOSPC"

# Check for rate limiting
gh run view <RUN_ID> --log-failed | grep -iE "rate limit|429|too many requests"
```

---

# Reference: Fetching Logs and Run Details

### If user provides a PR number or URL:

```bash
# Get workflow runs for a specific PR
gh pr checks <PR_NUMBER> --repo zenml-io/zenml

# Or get runs for a branch
gh run list --branch <branch-name> --repo zenml-io/zenml --limit 10
```

### If user provides a run URL:

Extract the run ID from the URL: `https://github.com/zenml-io/zenml/actions/runs/<RUN_ID>`

### If investigating the current branch:

```bash
# Get the current branch name
git branch --show-current

# List recent runs for this branch
gh run list --branch $(git branch --show-current) --repo zenml-io/zenml --limit 10
```

## Analyzing Failures

### Get run summary:

```bash
# View run summary (shows which jobs failed)
gh run view <RUN_ID> --repo zenml-io/zenml
```

### Get failed job logs only:

```bash
# This is the most useful command - gets only failed job logs
gh run view <RUN_ID> --repo zenml-io/zenml --log-failed
```

### Get specific job logs:

```bash
# List jobs in a run
gh run view <RUN_ID> --repo zenml-io/zenml --json jobs --jq '.jobs[] | {name: .name, status: .status, conclusion: .conclusion}'

# Get logs for a specific job
gh run view <RUN_ID> --repo zenml-io/zenml --log --job=<JOB_ID>
```

### For large logs, save to file and use `hl`:

```bash
# Save logs to file for analysis with hl
gh run view <RUN_ID> --repo zenml-io/zenml --log-failed > /tmp/ci-failure.log

# If hl is installed, use it to parse the logs:
# hl /tmp/ci-failure.log --filter 'level in (error, warning)'
# hl /tmp/ci-failure.log --filter 'message contains "FAILED"'
# hl /tmp/ci-failure.log --filter 'message contains "Error"'
```

**Tip for users**: Install `hl` (https://github.com/pamburus/hl) for better log parsing:
```bash
# macOS
brew install pamburus/tap/hl

# Or via cargo
cargo install hl
```

Useful `hl` flags for CI logs:
- `hl <file> --level error` - Show only error-level messages
- `hl <file> -f 'message contains "FAILED"'` - Filter by keyword
- `hl <file> --tail 100` - Show last 100 lines
- `hl <file> --follow` - Follow log file (for live debugging)

---

# Reference: ZenML CI Structure

### ci-fast (runs on every PR)

| Job | Description | Common Failures |
|-----|-------------|-----------------|
| `docstring-check` | Validates docstrings with darglint | Missing/malformed docstrings |
| `spellcheck` | Typo checking with typos | Misspellings (add to `.typos.toml` if valid) |
| `api-docs-test` | Tests API docs can be built | Import errors, missing dependencies |
| `linting` | Runs `scripts/lint.sh` (ruff + mypy) | Type errors, style violations |
| `ubuntu-setup-and-unit-test` | Unit tests on Python 3.11 | Test failures, import errors |
| `ubuntu-latest-integration-test` | Integration tests (6 shards) | Flaky tests, Docker issues, DB issues |
| `update-templates-to-examples` | Syncs templates to examples | Template/example mismatch |

### ci-slow (requires `run-slow-ci` label)

| Job | Description | Common Failures |
|-----|-------------|-----------------|
| `run-slow-ci-label-is-set` | Gate check for label | Missing label (add it!) |
| `sqlite-db-migration-testing-full` | SQLite migration tests | Migration script errors |
| `mysql-db-migration-testing-*` | MySQL migration tests | Migration script errors |
| `mariadb-db-migration-testing` | MariaDB migration tests | Migration script errors |
| `windows-*` | Windows-specific tests | Path handling, OS-specific issues |
| `macos-*` | macOS-specific tests | Homebrew issues, Docker via Colima |
| `vscode-tutorial-pipelines-test` | VSCode tutorial tests | Example code breaking changes |

### Integration Test Sharding

Integration tests are split into 6 shards for parallelism. To identify which tests are in which shard:

```bash
# The sharding uses pytest-split with least_duration algorithm
# Check .test_durations file for test timing data
cat .test_durations
```

---

# Reference: Common Failure Patterns

### 1. Dependency Upgrade Breakage (MOST COMMON)

**This is the most frequent cause of CI failures**, especially on Mondays or after weekends when packages release new versions.

**Symptoms**:
- CI was passing, suddenly starts failing without code changes
- Errors mention a specific package version or API change
- Often affects integration tests (ZenML has 50+ integrations)
- Error messages like `AttributeError`, `ImportError`, or deprecation warnings

**Diagnosis workflow**:

1. **Identify the failing package** from the error message:
```bash
# Look for package names in the error
gh run view <RUN_ID> --log-failed | grep -iE "error|exception|failed" | head -30
```

2. **Check when the package was last updated** - search for recent releases:
```bash
# Use WebSearch to find recent issues/releases
# Search: "<package-name> python release <current-month> <current-year>"
# Search: "<package-name> breaking change <current-year>"
```

3. **Check the package's GitHub issues** for known problems:
```bash
# Fetch the package's issues page
# Example: https://github.com/org/package/issues
```

4. **Check PyPI for recent releases**:
```bash
# View recent versions
pip index versions <package-name>

# Or check PyPI directly
# https://pypi.org/project/<package-name>/#history
```

**Solutions** (in order of preference):

1. **Upgrade the integration** to support the new version:
   - Check if the new version has breaking API changes
   - Update the integration code in `src/zenml/integrations/<name>/`
   - Update version bounds in the integration's `__init__.py`

2. **Pin to a working version** temporarily:
   - Update the version constraint in `src/zenml/integrations/<integration>/__init__.py`
   - Example: Change `"package>=1.0"` to `"package>=1.0,<2.0"`

3. **Skip the failing release** if it's known buggy:
   - Pin to exclude just that version: `"package>=1.0,!=1.2.0"`

**Where to update version constraints**:
```bash
# Find the integration's requirements
grep -r "<package-name>" src/zenml/integrations/*/

# The __init__.py file contains REQUIREMENTS list
cat src/zenml/integrations/<integration>/__init__.py
```

**Example investigation flow**:
```bash
# 1. Get the error
gh run view <RUN_ID> --log-failed | grep -A5 "Error\|Exception" | head -30

# 2. If it mentions e.g. "mlflow" - search for recent issues
# WebSearch: "mlflow python error January 2026"
# WebSearch: "mlflow 2.x breaking changes"

# 3. Check ZenML's current constraint
grep -A5 "REQUIREMENTS" src/zenml/integrations/mlflow/__init__.py

# 4. Check what version CI installed
gh run view <RUN_ID> --log-failed | grep -i "mlflow"
```

**Pro tips**:
- Monday failures are often weekend releases
- Check if the same test passed in recent CI runs (regression vs new issue)
- Look at the package's changelog for breaking changes
- Sometimes the fix is already in the package's `main` branch but not released

### 2. Flaky Test Failures (also common)

**Symptoms**: Test passes on retry, intermittent failures
**Solution**: Tests are retried 3 times automatically. If still failing:
- Check if test has race conditions
- Look for resource cleanup issues
- Check external service dependencies

```bash
# Find the specific test that failed
gh run view <RUN_ID> --log-failed | grep -E "FAILED|ERROR" | head -20
```

### 3. Linting/Type Errors

**Symptoms**: `linting` job fails
**Solution**: Run locally:

```bash
# Run the full linting suite
bash scripts/lint.sh

# Or run mypy on specific files
mypy src/zenml/path/to/changed/file.py
```

### 4. Docstring Errors

**Symptoms**: `docstring-check` job fails
**Solution**: Run darglint locally:

```bash
bash scripts/docstring.sh
```

Common issues:
- Missing parameter documentation
- Missing return type documentation
- Mismatched parameter names

### 5. Spellcheck Failures

**Symptoms**: `spellcheck` job fails with typos
**Solution**:
- Fix the typo, OR
- Add to `.typos.toml` if it's a valid word:

```toml
[default.extend-words]
# Add your word here
myword = "myword"
```

### 6. Database Migration Failures

**Symptoms**: `*-db-migration-testing-*` jobs fail
**Solution**: Check migration script:

```bash
# Check for migration branch divergence
bash scripts/check-alembic-branches.sh

# Look at recent migrations
ls -la src/zenml/zen_stores/migrations/versions/
```

### 7. Docker/Container Issues

**Symptoms**: Integration tests fail with Docker errors
**Common causes**:
- Disk space exhaustion (CI maximizes space but still limited)
- Docker image pull rate limits
- Container startup timeouts

```bash
# Check for Docker-related errors
gh run view <RUN_ID> --log-failed | grep -i docker
```

### 8. Import/Dependency Errors

**Symptoms**: Tests fail with `ImportError` or `ModuleNotFoundError`
**Solution**: Check if integration is installed:

```bash
# Integration tests install integrations dynamically
# Check which integrations are needed
zenml integration list
```

### 9. Windows/macOS Specific Failures

**Symptoms**: Tests pass on Linux but fail on Windows/macOS
**Common causes**:
- Path separator issues (`/` vs `\`)
- Case sensitivity
- macOS fork() issues (should be handled by `OBJC_DISABLE_INITIALIZE_FORK_SAFETY`)

### 10. GitHub Actions Runner Issues (Hard to Debug!)

**Symptoms**:
- Failures that can't be reproduced locally at all
- Sudden failures across all PRs without any code changes
- Errors mentioning system packages, paths, or pre-installed tools
- Cache-related errors or stale package versions
- Failures that "fix themselves" after a few days

**Common causes**:
- GitHub pushed a bad runner image update
- Pre-installed package versions changed on the runner
- Runner cache has stale/corrupted packages
- System-level dependencies changed (e.g., OpenSSL, Python system packages)
- GitHub infrastructure issues

**How to investigate**:

```bash
# Check GitHub's status page for known issues
# https://www.githubstatus.com/

# Look for runner-specific errors in logs
gh run view <RUN_ID> --log-failed | grep -iE "runner|image|pre-installed|cache"

# Check if the error mentions system paths
gh run view <RUN_ID> --log-failed | grep -iE "/usr/|/opt/|/home/runner"

# Compare runner image versions between passing and failing runs
# (Look for "Runner Image" in the job output)
gh run view <RUN_ID> --log | grep -i "runner image"
```

**How to identify it's a runner issue**:
1. **Search GitHub issues** for the error message + "actions runner"
2. **Check GitHub's changelog**: https://github.blog/changelog/label/actions/
3. **Search Twitter/X** for other OSS projects hitting the same issue
4. **Check ubuntu-latest changes**: https://github.com/actions/runner-images/releases

```bash
# WebSearch for recent runner issues
# Search: "github actions ubuntu-latest broken <current-month> <current-year>"
# Search: "github actions runner image <error-keyword>"
```

**Solutions** (limited options):
1. **Wait it out** - GitHub often fixes runner issues within days
2. **Pin the runner image** (if possible):
   ```yaml
   runs-on: ubuntu-22.04  # Instead of ubuntu-latest
   ```
3. **Clear caches** - Delete GitHub Actions caches for the repo
4. **Add workarounds** - Install specific package versions in the workflow
5. **Report to GitHub** - File an issue at https://github.com/actions/runner-images/issues

**Pro tip**: If you suspect a runner issue, check if other major OSS projects are seeing the same thing. Search their issue trackers or Twitter - you're probably not alone!

---

# Reference: Re-running Failed Jobs

```bash
# Re-run only failed jobs
gh run rerun <RUN_ID> --repo zenml-io/zenml --failed

# Re-run entire workflow
gh run rerun <RUN_ID> --repo zenml-io/zenml
```

---

# Reference: Debugging with tmate

Some workflows support tmate for interactive debugging:

```bash
# Trigger workflow with tmate enabled
gh workflow run <workflow>.yml -f enable_tmate=on-failure -f tmate_timeout=30
```

## Environment Variables

Key environment variables in CI:
- `ZENML_DEBUG=1` - Enables verbose debug logging (causes large logs)
- `ZENML_ANALYTICS_OPT_IN=false` - Disables analytics
- `PYTEST_RERUNS=3` - Number of test retries
- `PYTEST_RERUNS_DELAY=5` - Delay between retries

## Quick Debug Commands

```bash
# Get summary of what failed
gh run view <RUN_ID> --repo zenml-io/zenml

# Get failed logs
gh run view <RUN_ID> --repo zenml-io/zenml --log-failed

# Search for specific error in logs
gh run view <RUN_ID> --repo zenml-io/zenml --log-failed | grep -i "error\|failed\|exception" | head -50

# Get job timing info
gh run view <RUN_ID> --repo zenml-io/zenml --json jobs --jq '.jobs[] | "\(.name): \(.conclusion) (\(.steps | length) steps)"'

# Check if it's a known flaky test
gh run view <RUN_ID> --repo zenml-io/zenml --log-failed | grep -E "PASSED|FAILED|ERROR" | grep -i "rerun"
```

## Workflow Files Reference

Key workflow files to examine for understanding CI behavior:
- `.github/workflows/ci-fast.yml` - Fast CI jobs
- `.github/workflows/ci-slow.yml` - Slow CI jobs (need label)
- `.github/workflows/unit-test.yml` - Unit test configuration
- `.github/workflows/integration-test-fast.yml` - Integration test configuration
- `.github/workflows/linting.yml` - Linting configuration
- `scripts/test-coverage-xml.sh` - Main test runner script
