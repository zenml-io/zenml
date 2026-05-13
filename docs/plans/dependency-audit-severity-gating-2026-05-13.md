# Dependency Audit Severity Gating: Plan

## Goal

Extend PR #4805 (`feature/dependency-audit-ci`) so the Python dependency audit keeps auditing the installed `zenml[server,dev,local]` environment, but no longer lets `pip-audit` directly decide the CI result.

Desired behavior:

- `critical`, `high`, and `unknown` vulnerabilities fail CI.
- `medium` and `low` vulnerabilities are reported but do not fail CI.
- Weekly scheduled/manual runs open or update one tracking issue for current non-blocking `medium`/`low` findings.

## Decisions

- Keep this in `.github/workflows/dependency-audit.yml`, but split it into separate jobs for audit/classification, final gating, and scheduled issue maintenance.
- Preserve the current main-repo guard on all jobs unless maintainers explicitly decide later that forks should run this audit.
- Keep PR/push jobs read-only. Only the scheduled/manual issue-maintenance job gets `issues: write`.
- Use a checked-in Python helper script rather than inline YAML/Python.
- Use workflow artifacts for larger classified reports and Markdown bodies. Use job outputs only for small values such as counts, booleans, and artifact names.
- Use the workflow `GITHUB_TOKEN` for GitHub Advisory API calls to avoid unauthenticated rate limits.
- Treat unresolved severity as `unknown` and block CI, but report whether it was caused by missing mapping metadata or a lookup/API failure.
- Do not add PR comments in this change; use `$GITHUB_STEP_SUMMARY` for PR-visible reporting.

## Background

The current workflow installs `zenml[server,dev,local]` into `.venv-audit-target`, runs `uv pip check`, then runs `uvx pip-audit --path "$SITE_PACKAGES" --strict --progress-spinner off` (`.github/workflows/dependency-audit.yml:51-60`). Because `pip-audit` currently owns the exit status, any vulnerability fails the job.

`pip-audit` can emit JSON with package names, versions, advisory IDs, aliases, descriptions, and fix versions, but it does not include normalized severity and does not provide a built-in severity-threshold flag. Severity therefore needs to be resolved from advisory identifiers, preferably through the GitHub Global Security Advisories API.

The existing workflow is intentionally locked down: workflow-level `permissions: {}` and job-level `contents: read` (`.github/workflows/dependency-audit.yml:19-27`). That is right for PR/push audit checks. Issue creation needs a separate write-capable path that only runs on scheduled/manual events in the main repository.

Useful existing patterns:

- `$GITHUB_STEP_SUMMARY` and delayed-failure reporting: `.github/workflows/check-links.yml:77-158`, `.github/workflows/validate-changelog.yml`.
- Search-before-create issue handling with `actions/github-script`: `.github/workflows/snack-it.yml:116-151`.
- Security-workflow posture with empty workflow permissions, pinned actions, main-repo guards, and read-only jobs: `.github/workflows/zizmor.yml`.

## Approach

Use three jobs inside the existing workflow.

### 1. `audit-classify`

Read-only job. It keeps the existing install path, runs `pip-audit` in JSON mode, captures the exit code without immediately failing, then runs a helper script to classify findings by severity.

This job writes:

- a workflow summary Markdown file
- a classified JSON artifact
- a non-blocking tracking issue Markdown artifact
- small job outputs such as `blocking_count`, `nonblocking_count`, `unknown_count`, and `audit_error`

It should append the summary Markdown to `$GITHUB_STEP_SUMMARY` even when vulnerabilities are found.

### 2. `gate`

Read-only job. It depends on `audit-classify` and decides the final red/green status.

It fails only when:

- the audit/classification job failed technically
- the helper marked the audit result unusable
- `blocking_count > 0`

It passes when vulnerabilities exist but all classified findings are `medium` or `low`.

### 3. `update-nonblocking-tracking-issue`

Write-capable job. It depends directly on `audit-classify`, not on `gate`, so scheduled/manual runs can still update the medium/low tracking issue even if a high/critical/unknown finding makes `gate` fail.

It runs only when:

- `github.repository == 'zenml-io/zenml'`
- the event is `schedule` or `workflow_dispatch`
- `audit-classify` produced usable classified output

It downloads the non-blocking issue Markdown artifact, then uses `actions/github-script` to search for one existing tracking issue by marker:

```text
<!-- zenml-dependency-audit-nonblocking -->
```

Behavior:

- If `medium`/`low` findings exist, create, update, or reopen the tracking issue.
- If no `medium`/`low` findings exist, close the open tracking issue after updating it with a “no current non-blocking findings” note.
- If no tracking issue exists and there are no non-blocking findings, do nothing.

Suggested title:

```text
Python dependency audit: medium/low vulnerability tracking
```

## Work Items

### 1. Add the severity-classification helper

**File:** `scripts/dependency_audit_severity_gate.py`

The helper should use only the Python standard library. It should:

- parse `pip-audit` JSON
- extract package, installed version, advisory ID, aliases, fix versions, and description
- normalize package names
- prefer GHSA identifiers and call `GET /advisories/{ghsa_id}`
- fall back to CVE lookup through the GitHub Global Security Advisories list endpoint
- classify PYSEC/OSV-only findings as `unknown` unless a GHSA/CVE alias is available
- cache advisory lookups during the run
- deduplicate repeated advisory/package findings
- split findings into blocking and non-blocking buckets
- render summary Markdown, tracking issue Markdown, and classified JSON

Use explicit reason codes for `unknown`, for example:

- `unmapped-advisory`
- `github-api-error`
- `invalid-advisory-response`

That way a red check tells the reader whether they should rerun CI or investigate missing advisory metadata.

### 2. Add focused unit tests for the helper

**File:** `tests/unit/scripts/test_dependency_audit_severity_gate.py`

Mock all GitHub API responses. Cover the important trust-boundary cases:

- no vulnerabilities
- medium/low findings pass
- high/critical findings block
- unmapped findings become `unknown` and block
- API failures become `unknown` and block
- GHSA and CVE lookup paths
- deduplication
- tracking issue body includes only medium/low findings

### 3. Update the audit workflow

**File:** `.github/workflows/dependency-audit.yml`

Keep the current install/audit target:

- Python 3.11
- pinned `uv` setup
- `.venv-audit-target`
- `uv pip install --python .venv-audit-target/bin/python '.[server,dev,local]'`
- `uv pip check`

Change the audit/reporting path:

- Add `scripts/dependency_audit_severity_gate.py` to the path filters.
- Run `pip-audit` with JSON output.
- Capture stdout/stderr and exit code without failing immediately for vulnerabilities.
- Pass `GITHUB_TOKEN` to the helper for advisory lookups.
- Upload classified JSON and Markdown reports as artifacts.
- Emit only small job outputs for downstream conditions.
- Append the summary Markdown to `$GITHUB_STEP_SUMMARY`.

### 4. Add the final gate job

**File:** `.github/workflows/dependency-audit.yml`

Add `gate` after `audit-classify`. Its job is deliberately small: inspect the classification outputs and fail only for technical audit errors or blocking findings.

### 5. Add scheduled/manual tracking issue maintenance

**File:** `.github/workflows/dependency-audit.yml`

Add `update-nonblocking-tracking-issue` after `audit-classify`, guarded to scheduled/manual events in `zenml-io/zenml`.

Grant this job:

```yaml
permissions:
  contents: read
  issues: write
```

Use pinned `actions/github-script`. Search for the stable marker before creating anything. Keep labels best-effort; missing labels should warn but not fail the audit.

## Reporting Shape

The workflow summary should separate blocking and non-blocking findings, with one section per severity and a short notes block explaining:

- where severity came from
- that `unknown` blocks by design
- whether each `unknown` was caused by missing mapping metadata or lookup/API failure

The tracking issue should contain only current `medium`/`low` findings, plus a link to the latest workflow run. Blocking findings should be handled through failed CI, not backlog tracking.

## Validation Plan

Before updating the PR, run targeted checks:

1. Unit tests for `scripts/dependency_audit_severity_gate.py`.
2. Workflow/YAML formatting or linting through the repo’s normal tooling where practical.
3. `zizmor` against `.github/workflows/dependency-audit.yml`.
4. Local fixture checks for no-vulnerability, medium/low-only, high/critical, unknown, mixed-severity, and API-failure scenarios.
5. CI validation on PR #4805 after pushing the branch update.
6. Manual or scheduled workflow validation for the issue-maintenance path, because issue creation cannot be fully verified by ordinary local tests.

## Risks and Defaults

### Unknown severity can create noisy red checks

Some `pip-audit` findings may have IDs that GitHub cannot map cleanly, or advisory lookup may temporarily fail. Those findings will block as `unknown`. This is intentional: the safer failure mode is “someone investigates this” rather than “a real high-severity issue passed because metadata was missing.”

### GitHub Actions data transfer can bite

Markdown issue bodies and classified JSON can outgrow safe step-output usage. Use artifacts for report bodies and classified data; reserve job outputs for small counts and flags.

### Tracking issue spam

Opening one issue per vulnerability would create noise. Maintain one stable issue with a marker and replace the body each scheduled/manual run.

### Permissions boundary

The most important safety rule is that PR/push audit jobs remain read-only. Only the scheduled/manual tracking job should receive `issues: write`.

## Out of Scope

- Auditing every ZenML integration extra.
- Replacing `pip-audit` with `uv audit`.
- Adding OSV or NVD severity fallback in the first pass.
- Uploading SARIF/code-scanning results.
- Adding PR comments for dependency audit results.
- Automatically opening remediation PRs.

## References

- PR #4805: https://github.com/zenml-io/zenml/pull/4805
- `pip-audit`: https://github.com/pypa/pip-audit
- GitHub Global Security Advisories REST API: https://docs.github.com/en/rest/security-advisories/global-advisories
- OSV severity field: https://ossf.github.io/osv-schema/#severity-field
- Current workflow: `.github/workflows/dependency-audit.yml:1-60`
- Summary/comment pattern: `.github/workflows/check-links.yml:77-158`
- Issue creation pattern: `.github/workflows/snack-it.yml:116-151`
