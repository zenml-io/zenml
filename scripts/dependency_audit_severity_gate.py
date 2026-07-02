"""Classify pip-audit findings by GitHub advisory severity.

The GitHub Actions workflow uses this script as a safer middle step between
``pip-audit`` and the final CI result. ``pip-audit`` tells us which installed
packages have known vulnerabilities. This script asks GitHub's Global Security
Advisory API how severe those vulnerabilities are, then marks only critical,
high, and unknown-severity findings as blocking.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEVERITY_ORDER = ("critical", "high", "unknown", "medium", "low")
SEVERITY_RANK = {
    severity: index for index, severity in enumerate(SEVERITY_ORDER)
}
BLOCKING_SEVERITIES = set(SEVERITY_ORDER[:3])
KNOWN_SEVERITIES = set(SEVERITY_ORDER)
UNKNOWN_GITHUB_API_ERROR = "github-api-error"
UNKNOWN_INVALID_RESPONSE = "invalid-advisory-response"
UNKNOWN_GITHUB_UNKNOWN_SEVERITY = "github-unknown-severity"
UNKNOWN_UNMAPPED_ADVISORY = "unmapped-advisory"
TRACKING_ISSUE_MARKER = "<!-- zenml-dependency-audit-nonblocking -->"


@dataclass(frozen=True)
class ResolvedSeverity:
    """Severity metadata resolved for one advisory identifier."""

    severity: str
    source: str
    unknown_reason: str | None = None
    ghsa_id: str | None = None
    cve_id: str | None = None


@dataclass(frozen=True)
class SkippedDependency:
    """Dependency entry that pip-audit could not audit."""

    package: str
    normalized_package: str
    installed_version: str
    skip_reason: str


@dataclass(frozen=True)
class Finding:
    """Classified vulnerability finding for one package/advisory pair."""

    package: str
    normalized_package: str
    installed_version: str
    advisory_id: str
    aliases: list[str]
    fix_versions: list[str]
    description: str
    severity: str
    blocking: bool
    severity_source: str
    unknown_reason: str | None = None
    ghsa_id: str | None = None
    cve_id: str | None = None


@dataclass(frozen=True)
class AdvisoryWaiver:
    """A temporary waiver for specific advisories in specific CI contexts."""

    package: str
    normalized_package: str
    advisories: list[str]
    normalized_advisories: list[str]
    allowed_contexts: list[str]
    expires_on: date
    owner: str
    reason: str


class GitHubAdvisoryClient:
    """Small stdlib client for GitHub Global Security Advisories."""

    def __init__(
        self,
        token: str | None = None,
        api_url: str = "https://api.github.com",
    ) -> None:
        """Initialize the advisory client."""
        self._token = token
        self._api_url = api_url.rstrip("/")
        self._cache: dict[tuple[str, ...], ResolvedSeverity] = {}

    def resolve(
        self,
        identifiers: list[str],
        package_name: str,
    ) -> ResolvedSeverity:
        """Resolve severity from the best available advisory identifier."""
        ghsa_id = _first_ghsa_identifier(identifiers)
        if ghsa_id:
            return self._cached_resolve(
                ("ghsa", ghsa_id),
                lambda: self._resolve_ghsa(ghsa_id),
            )

        cve_id = _first_cve_identifier(identifiers)
        if cve_id:
            normalized_package = _normalize_package_name(package_name)
            return self._cached_resolve(
                ("cve", cve_id, normalized_package),
                lambda: self._resolve_cve(cve_id, normalized_package),
            )

        return ResolvedSeverity(
            severity="unknown",
            source="pip-audit",
            unknown_reason=UNKNOWN_UNMAPPED_ADVISORY,
        )

    def _cached_resolve(
        self,
        cache_key: tuple[str, ...],
        resolver: Callable[[], ResolvedSeverity],
    ) -> ResolvedSeverity:
        if cache_key not in self._cache:
            self._cache[cache_key] = resolver()
        return self._cache[cache_key]

    def _resolve_ghsa(self, ghsa_id: str) -> ResolvedSeverity:
        try:
            advisory = self._fetch_json(f"/advisories/{ghsa_id}")
        except json.JSONDecodeError:
            return ResolvedSeverity(
                severity="unknown",
                source="github-advisory-api",
                unknown_reason=UNKNOWN_INVALID_RESPONSE,
                ghsa_id=ghsa_id,
            )
        except (HTTPError, URLError, TimeoutError, OSError):
            return ResolvedSeverity(
                severity="unknown",
                source="github-advisory-api",
                unknown_reason=UNKNOWN_GITHUB_API_ERROR,
                ghsa_id=ghsa_id,
            )
        return _severity_from_advisory(advisory, fallback_ghsa_id=ghsa_id)

    def _resolve_cve(
        self,
        cve_id: str,
        normalized_package_name: str,
    ) -> ResolvedSeverity:
        query = urlencode(
            {
                "cve_id": cve_id,
                "ecosystem": "pip",
                "affects": normalized_package_name,
                "per_page": 100,
            }
        )
        try:
            advisories = self._fetch_json(f"/advisories?{query}")
        except json.JSONDecodeError:
            return ResolvedSeverity(
                severity="unknown",
                source="github-advisory-api",
                unknown_reason=UNKNOWN_INVALID_RESPONSE,
                cve_id=cve_id,
            )
        except (HTTPError, URLError, TimeoutError, OSError):
            return ResolvedSeverity(
                severity="unknown",
                source="github-advisory-api",
                unknown_reason=UNKNOWN_GITHUB_API_ERROR,
                cve_id=cve_id,
            )

        if not isinstance(advisories, list):
            return ResolvedSeverity(
                severity="unknown",
                source="github-advisory-api",
                unknown_reason=UNKNOWN_INVALID_RESPONSE,
                cve_id=cve_id,
            )
        matching_advisories = _filter_advisories_by_package(
            advisories,
            normalized_package_name,
        )
        if not matching_advisories:
            return ResolvedSeverity(
                severity="unknown",
                source="github-advisory-api",
                unknown_reason=UNKNOWN_UNMAPPED_ADVISORY,
                cve_id=cve_id,
            )
        severities = [
            _severity_from_advisory(advisory, fallback_cve_id=cve_id)
            for advisory in matching_advisories
        ]
        return min(
            severities,
            key=lambda severity: _severity_sort_key(severity.severity),
        )

    def _fetch_json(self, path: str) -> Any:
        request = Request(
            f"{self._api_url}{path}",
            headers=self._headers(),
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "zenml-dependency-audit-severity-gate",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers


def classify_audit(
    audit_data: dict[str, Any],
    client: GitHubAdvisoryClient,
    waivers: list[AdvisoryWaiver] | None = None,
    waiver_context: str = "",
    today: date | None = None,
    audit_error: bool = False,
    audit_error_message: str = "",
) -> dict[str, Any]:
    """Classify a parsed pip-audit JSON document."""
    waivers = waivers or []
    today = today or date.today()
    malformed_messages = _collect_malformed_audit_messages(audit_data)
    if malformed_messages:
        audit_error = True
        audit_error_message = _append_audit_error_message(
            audit_error_message,
            "Malformed pip-audit JSON: " + " ".join(malformed_messages),
        )

    findings = _deduplicate_findings(
        _classify_raw_finding(raw_finding, client)
        for raw_finding in _iter_raw_findings(audit_data)
    )
    skipped_dependencies = _iter_skipped_dependencies(audit_data)
    if skipped_dependencies:
        audit_error = True
        audit_error_message = _append_audit_error_message(
            audit_error_message,
            _skipped_dependency_error_message(skipped_dependencies),
        )
    blocking, waived_blocking = _split_blocking_findings(
        findings,
        waivers,
        waiver_context,
        today,
    )
    nonblocking = [finding for finding in findings if not finding.blocking]
    unknown_count = sum(
        1 for finding in findings if finding.severity == "unknown"
    )

    return {
        "audit_error": audit_error,
        "audit_error_message": audit_error_message,
        "counts": {
            "total": len(findings),
            "blocking": len(blocking),
            "waived_blocking": len(waived_blocking),
            "nonblocking": len(nonblocking),
            "unknown": unknown_count,
            "skipped": len(skipped_dependencies),
        },
        "skipped_dependencies": [
            asdict(dependency) for dependency in skipped_dependencies
        ],
        "findings": [asdict(finding) for finding in findings],
        "blocking": [asdict(finding) for finding in blocking],
        "waived_blocking": waived_blocking,
        "nonblocking": [asdict(finding) for finding in nonblocking],
    }


def render_summary(report: dict[str, Any]) -> str:
    """Render GitHub workflow summary Markdown."""
    counts = report["counts"]
    lines = [
        "# Python dependency audit",
        "",
        _summary_status_line(report),
        "",
        "## Counts",
        "",
        "| Bucket | Count |",
        "| --- | ---: |",
        f"| Blocking (`critical`, `high`, `unknown`) | {counts['blocking']} |",
        f"| Waived blocking | {counts.get('waived_blocking', 0)} |",
        f"| Non-blocking (`medium`, `low`) | {counts['nonblocking']} |",
        f"| Unknown severity | {counts['unknown']} |",
        f"| Skipped/unauditable dependencies | {counts.get('skipped', 0)} |",
        f"| Total findings | {counts['total']} |",
        "",
        "## Notes",
        "",
        "- Severity is resolved through GitHub Global Security Advisories ",
        "  when a GHSA or CVE identifier is available.",
        "- `unknown` severity blocks CI by design because the workflow cannot ",
        "  prove that the finding is only medium or low.",
        "- Unknown reason codes distinguish missing mapping metadata from ",
        "  GitHub API lookup failures.",
        "",
    ]
    if report["audit_error"]:
        lines.extend(
            [
                "## Audit error",
                "",
                report["audit_error_message"]
                or "The pip-audit result was unusable.",
                "",
            ]
        )

    lines.extend(
        _render_skipped_dependencies(report.get("skipped_dependencies", []))
    )
    lines.extend(
        _render_finding_sections(report["blocking"], "Blocking findings")
    )
    lines.extend(
        _render_waived_finding_sections(
            report.get("waived_blocking", []),
            "Waived blocking findings",
        )
    )
    lines.extend(
        _render_finding_sections(
            report["nonblocking"], "Non-blocking findings"
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def render_tracking_issue_body(
    report: dict[str, Any], run_url: str | None
) -> str:
    """Render the scheduled tracking issue body for medium/low findings."""
    nonblocking = report["nonblocking"]
    lines = [
        TRACKING_ISSUE_MARKER,
        "# Python dependency audit: medium/low vulnerability tracking",
        "",
        "This issue is maintained by the scheduled/manual dependency audit.",
        "It only tracks current `medium` and `low` findings. Blocking ",
        "`critical`, `high`, and `unknown` findings are handled by failed CI.",
        "",
    ]
    if run_url:
        lines.extend([f"Latest workflow run: {run_url}", ""])

    if not nonblocking:
        lines.extend(
            [
                "## Current status",
                "",
                "No current non-blocking dependency audit findings were found.",
                "",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(
        [
            "## Current non-blocking findings",
            "",
            "| Severity | Package | Installed | Advisory | Fix versions |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for finding in nonblocking:
        lines.append(_finding_table_row(finding))
    lines.extend(
        [
            "",
            "## Suggested maintenance flow",
            "",
            "1. Review whether the affected package is reachable in ZenML's ",
            "   installed `server`, `dev`, and `local` environment.",
            "2. Prefer an upgrade when a compatible fixed version exists.",
            "3. If an upgrade is blocked, leave a short note explaining the ",
            "   blocker and revisit it on the next scheduled audit.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_waived_discord_message(
    report: dict[str, Any],
    run_url: str | None,
) -> str:
    """Render a concise Discord message for release-only waived findings."""
    waived_findings = report.get("waived_blocking", [])
    if not waived_findings:
        return "No waived blocking dependency audit findings were found.\n"

    lines = [
        "**Dependency Audit Waiver Used**",
        "",
        "A release PR used temporary waivers for blocking dependency findings.",
        "",
        "**Waived findings:**",
    ]
    for finding in waived_findings:
        waiver = finding.get("waiver", {})
        lines.append(
            "- "
            f"{finding['package']} {finding['installed_version']} — "
            f"{finding['advisory_id']} — {finding['severity']} "
            f"(expires {waiver.get('expires_on', 'unknown')})"
        )
    reasons = sorted(
        {
            str(finding.get("waiver", {}).get("reason", "")).strip()
            for finding in waived_findings
            if str(finding.get("waiver", {}).get("reason", "")).strip()
        }
    )
    if reasons:
        lines.extend(["", "**Reason:**"])
        lines.extend(f"- {reason}" for reason in reasons)
    if run_url:
        lines.extend(["", f"**Details:** {run_url}"])
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-json", required=True, type=Path)
    parser.add_argument("--pip-audit-exit-code", required=True, type=int)
    parser.add_argument("--pip-audit-stderr", type=Path)
    parser.add_argument("--classified-json", required=True, type=Path)
    parser.add_argument("--summary-md", required=True, type=Path)
    parser.add_argument("--nonblocking-issue-md", required=True, type=Path)
    parser.add_argument("--waivers-json", type=Path)
    parser.add_argument("--waiver-context", default="")
    parser.add_argument("--waived-discord-md", type=Path)
    parser.add_argument("--today", type=_parse_iso_date)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument(
        "--github-token", default=os.environ.get("GITHUB_TOKEN")
    )
    parser.add_argument(
        "--github-api-url",
        default=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
    )
    parser.add_argument("--run-url", default=_default_run_url())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the severity gate helper."""
    args = parse_args(argv or sys.argv[1:])
    audit_data, audit_error, audit_error_message = _load_audit_data(args)
    waivers, waiver_error_message = _load_waivers(args.waivers_json)
    if waiver_error_message:
        audit_error = True
        audit_error_message = _append_audit_error_message(
            audit_error_message,
            waiver_error_message,
        )
    client = GitHubAdvisoryClient(
        token=args.github_token,
        api_url=args.github_api_url,
    )
    report = classify_audit(
        audit_data,
        client,
        waivers=waivers,
        waiver_context=args.waiver_context,
        today=args.today,
        audit_error=audit_error,
        audit_error_message=audit_error_message,
    )

    _write_text(args.summary_md, render_summary(report))
    _write_text(
        args.nonblocking_issue_md,
        render_tracking_issue_body(report, args.run_url),
    )
    if args.waived_discord_md:
        _write_text(
            args.waived_discord_md,
            render_waived_discord_message(report, args.run_url),
        )
    _write_json(args.classified_json, report)
    if args.github_output:
        _write_github_outputs(args.github_output, report)
    return 0


def _load_audit_data(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], bool, str]:
    audit_error = args.pip_audit_exit_code not in {0, 1}
    error_parts = []
    if audit_error:
        error_parts.append(
            f"pip-audit exited with code {args.pip_audit_exit_code}."
        )
    if args.pip_audit_stderr:
        try:
            stderr = args.pip_audit_stderr.read_text(encoding="utf-8").strip()
        except OSError:
            stderr = ""
        if stderr and audit_error:
            error_parts.append(f"stderr: {stderr}")

    try:
        data = json.loads(args.audit_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, True, " ".join(error_parts + [f"Invalid JSON: {exc}"])

    if not isinstance(data, dict):
        return (
            {},
            True,
            " ".join(error_parts + ["pip-audit JSON was not an object."]),
        )
    return data, audit_error, " ".join(error_parts)


def _load_waivers(
    waivers_json: Path | None,
) -> tuple[list[AdvisoryWaiver], str]:
    """Load explicit advisory waivers from JSON."""
    if waivers_json is None or not waivers_json.exists():
        return [], ""
    try:
        data = json.loads(waivers_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], f"Invalid dependency audit waiver JSON: {exc}"
    if not isinstance(data, dict):
        return (
            [],
            "Invalid dependency audit waiver JSON: root was not an object.",
        )
    raw_waivers = data.get("waivers", [])
    if not isinstance(raw_waivers, list):
        return (
            [],
            "Invalid dependency audit waiver JSON: waivers was not a list.",
        )

    waivers: list[AdvisoryWaiver] = []
    errors: list[str] = []
    for index, raw_waiver in enumerate(raw_waivers):
        waiver, error = _parse_waiver(raw_waiver, index)
        if error:
            errors.append(error)
            continue
        waivers.append(waiver)
    return waivers, " ".join(errors)


def _parse_waiver(
    raw_waiver: Any,
    index: int,
) -> tuple[AdvisoryWaiver | None, str]:
    """Parse one waiver entry and return a validation error if malformed."""
    if not isinstance(raw_waiver, dict):
        return None, f"waiver entry {index} was not an object."

    package = str(raw_waiver.get("package") or "").strip()
    advisories = _string_list(raw_waiver.get("advisories", []))
    allowed_contexts = _string_list(raw_waiver.get("allowed_contexts", []))
    expires_on_raw = str(raw_waiver.get("expires_on") or "").strip()
    owner = str(raw_waiver.get("owner") or "").strip()
    reason = str(raw_waiver.get("reason") or "").strip()

    missing = []
    if not package:
        missing.append("package")
    if not advisories:
        missing.append("advisories")
    if not allowed_contexts:
        missing.append("allowed_contexts")
    if not expires_on_raw:
        missing.append("expires_on")
    if not owner:
        missing.append("owner")
    if not reason:
        missing.append("reason")
    if missing:
        return (
            None,
            f"waiver entry {index} is missing required fields: "
            + ", ".join(missing)
            + ".",
        )

    try:
        expires_on = _parse_iso_date(expires_on_raw)
    except argparse.ArgumentTypeError as exc:
        return None, f"waiver entry {index} has invalid expires_on: {exc}"

    return (
        AdvisoryWaiver(
            package=package,
            normalized_package=_normalize_package_name(package),
            advisories=advisories,
            normalized_advisories=[
                _normalize_advisory_identifier(advisory)
                for advisory in advisories
            ],
            allowed_contexts=allowed_contexts,
            expires_on=expires_on,
            owner=owner,
            reason=reason,
        ),
        "",
    )


def _iter_skipped_dependencies(
    audit_data: dict[str, Any],
) -> list[SkippedDependency]:
    """Extract dependency entries that pip-audit skipped under strict mode."""
    skipped_dependencies: list[SkippedDependency] = []
    dependencies = audit_data.get("dependencies", [])
    if not isinstance(dependencies, list):
        return skipped_dependencies
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        skip_reason = str(dependency.get("skip_reason") or "").strip()
        if not skip_reason:
            continue
        package = str(dependency.get("name", ""))
        installed_version = str(dependency.get("version", ""))
        skipped_dependencies.append(
            SkippedDependency(
                package=package,
                normalized_package=_normalize_package_name(package),
                installed_version=installed_version,
                skip_reason=skip_reason,
            )
        )
    return sorted(
        skipped_dependencies,
        key=lambda dependency: (
            dependency.normalized_package,
            dependency.installed_version,
        ),
    )


def _split_blocking_findings(
    findings: list[Finding],
    waivers: list[AdvisoryWaiver],
    waiver_context: str,
    today: date,
) -> tuple[list[Finding], list[dict[str, Any]]]:
    """Split blocking findings into unwaived and explicitly waived groups."""
    blocking: list[Finding] = []
    waived_blocking: list[dict[str, Any]] = []
    for finding in findings:
        if not finding.blocking:
            continue
        waiver = _matching_waiver(finding, waivers, waiver_context, today)
        if waiver is None:
            blocking.append(finding)
            continue
        waived_finding = asdict(finding)
        waived_finding["waiver"] = _waiver_report_dict(waiver)
        waived_blocking.append(waived_finding)
    return blocking, waived_blocking


def _matching_waiver(
    finding: Finding,
    waivers: list[AdvisoryWaiver],
    waiver_context: str,
    today: date,
) -> AdvisoryWaiver | None:
    """Return the active waiver that covers a finding, if one exists."""
    if not waiver_context:
        return None
    finding_identifiers = set(_finding_advisory_identifiers(finding))
    for waiver in waivers:
        if waiver_context not in waiver.allowed_contexts:
            continue
        if waiver.expires_on < today:
            continue
        if waiver.normalized_package != finding.normalized_package:
            continue
        if finding_identifiers.intersection(waiver.normalized_advisories):
            return waiver
    return None


def _finding_advisory_identifiers(finding: Finding) -> list[str]:
    """Return all advisory identifiers that can match a waiver."""
    identifiers = [finding.advisory_id, *finding.aliases]
    if finding.ghsa_id:
        identifiers.append(finding.ghsa_id)
    if finding.cve_id:
        identifiers.append(finding.cve_id)
    return [
        _normalize_advisory_identifier(identifier)
        for identifier in identifiers
    ]


def _waiver_report_dict(waiver: AdvisoryWaiver) -> dict[str, Any]:
    """Serialize waiver details included in audit artifacts."""
    return {
        "package": waiver.package,
        "advisories": waiver.advisories,
        "allowed_contexts": waiver.allowed_contexts,
        "expires_on": waiver.expires_on.isoformat(),
        "owner": waiver.owner,
        "reason": waiver.reason,
    }


def _iter_raw_findings(audit_data: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    dependencies = audit_data.get("dependencies", [])
    if not isinstance(dependencies, list):
        return findings
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        package = str(dependency.get("name", ""))
        installed_version = str(dependency.get("version", ""))
        vulns = dependency.get("vulns", [])
        if not isinstance(vulns, list):
            continue
        for vulnerability in vulns:
            if not isinstance(vulnerability, dict):
                continue
            findings.append(
                {
                    "package": package,
                    "installed_version": installed_version,
                    "vulnerability": vulnerability,
                }
            )
    return findings


def _collect_malformed_audit_messages(
    audit_data: dict[str, Any],
) -> list[str]:
    """Return validation messages for malformed-but-parseable audit JSON."""
    dependencies = audit_data.get("dependencies", [])
    if not isinstance(dependencies, list):
        return ["field 'dependencies' was not a list."]

    messages: list[str] = []
    for dependency_index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            messages.append(
                f"dependency entry {dependency_index} was not an object."
            )
            continue

        package = str(dependency.get("name") or f"index {dependency_index}")
        vulns = dependency.get("vulns", [])
        if not isinstance(vulns, list):
            messages.append(
                f"dependency '{package}' field 'vulns' was not a list."
            )
            continue

        for vuln_index, vulnerability in enumerate(vulns):
            if not isinstance(vulnerability, dict):
                messages.append(
                    f"dependency '{package}' vulnerability entry {vuln_index} "
                    "was not an object."
                )
    return messages


def _append_audit_error_message(
    existing_message: str, new_message: str
) -> str:
    """Append audit error context without losing earlier tooling errors."""
    if existing_message:
        return f"{existing_message} {new_message}"
    return new_message


def _skipped_dependency_error_message(
    skipped_dependencies: list[SkippedDependency],
) -> str:
    """Render a compact error message for skipped dependencies."""
    packages = ", ".join(
        f"{dependency.package or '<unknown>'}"
        f"=={dependency.installed_version or '<unknown>'}"
        for dependency in skipped_dependencies
    )
    return (
        "pip-audit skipped dependencies under strict mode; the audit result "
        f"is incomplete. Skipped: {packages}."
    )


def _classify_raw_finding(
    raw_finding: dict[str, Any],
    client: GitHubAdvisoryClient,
) -> Finding:
    vulnerability = raw_finding["vulnerability"]
    advisory_id = str(vulnerability.get("id", ""))
    aliases = _string_list(vulnerability.get("aliases", []))
    identifiers = [advisory_id, *aliases]
    resolved = client.resolve(identifiers, raw_finding["package"])
    severity = resolved.severity
    return Finding(
        package=raw_finding["package"],
        normalized_package=_normalize_package_name(raw_finding["package"]),
        installed_version=raw_finding["installed_version"],
        advisory_id=advisory_id,
        aliases=aliases,
        fix_versions=_extract_fix_versions(vulnerability),
        description=str(vulnerability.get("description", "")),
        severity=severity,
        blocking=severity in BLOCKING_SEVERITIES,
        severity_source=resolved.source,
        unknown_reason=resolved.unknown_reason,
        ghsa_id=resolved.ghsa_id,
        cve_id=resolved.cve_id,
    )


def _deduplicate_findings(findings: Any) -> list[Finding]:
    deduplicated: dict[tuple[str, str, str], Finding] = {}
    for finding in findings:
        key = (
            finding.normalized_package,
            finding.installed_version,
            _canonical_identifier(finding),
        )
        deduplicated.setdefault(key, finding)
    return sorted(
        deduplicated.values(),
        key=lambda finding: (
            _severity_sort_key(finding.severity),
            finding.normalized_package,
            finding.advisory_id,
        ),
    )


def _filter_advisories_by_package(
    advisories: list[Any],
    normalized_package_name: str,
) -> list[dict[str, Any]]:
    """Return advisories that affect the audited Python package."""
    matching_advisories: list[dict[str, Any]] = []
    for advisory in advisories:
        if not isinstance(advisory, dict):
            continue
        vulnerabilities = advisory.get("vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            continue
        for vulnerability in vulnerabilities:
            if _vulnerability_matches_package(
                vulnerability,
                normalized_package_name,
            ):
                matching_advisories.append(advisory)
                break
    return matching_advisories


def _vulnerability_matches_package(
    vulnerability: Any,
    normalized_package_name: str,
) -> bool:
    """Check whether GitHub advisory metadata matches the audited package."""
    if not isinstance(vulnerability, dict):
        return False
    package = vulnerability.get("package")
    if not isinstance(package, dict):
        return False
    ecosystem = str(package.get("ecosystem", "")).lower()
    name = str(package.get("name", ""))
    return ecosystem in {"pip", "pypi"} and (
        _normalize_package_name(name) == normalized_package_name
    )


def _severity_from_advisory(
    advisory: Any,
    fallback_ghsa_id: str | None = None,
    fallback_cve_id: str | None = None,
) -> ResolvedSeverity:
    if not isinstance(advisory, dict):
        return ResolvedSeverity(
            severity="unknown",
            source="github-advisory-api",
            unknown_reason=UNKNOWN_INVALID_RESPONSE,
            ghsa_id=fallback_ghsa_id,
            cve_id=fallback_cve_id,
        )
    severity = str(advisory.get("severity", "")).lower()
    if severity == "unknown":
        return ResolvedSeverity(
            severity="unknown",
            source="github-advisory-api",
            unknown_reason=UNKNOWN_GITHUB_UNKNOWN_SEVERITY,
            ghsa_id=_normalize_ghsa_id(
                advisory.get("ghsa_id") or fallback_ghsa_id
            ),
            cve_id=_normalize_cve_id(
                advisory.get("cve_id") or fallback_cve_id
            ),
        )
    if severity not in KNOWN_SEVERITIES:
        return ResolvedSeverity(
            severity="unknown",
            source="github-advisory-api",
            unknown_reason=UNKNOWN_INVALID_RESPONSE,
            ghsa_id=_normalize_ghsa_id(
                advisory.get("ghsa_id") or fallback_ghsa_id
            ),
            cve_id=_normalize_cve_id(
                advisory.get("cve_id") or fallback_cve_id
            ),
        )
    return ResolvedSeverity(
        severity=severity,
        source="github-advisory-api",
        ghsa_id=_normalize_ghsa_id(
            advisory.get("ghsa_id") or fallback_ghsa_id
        ),
        cve_id=_normalize_cve_id(advisory.get("cve_id") or fallback_cve_id),
    )


def _extract_fix_versions(vulnerability: dict[str, Any]) -> list[str]:
    fix_versions = _string_list(
        vulnerability.get("fix_versions")
        or vulnerability.get("fixed_versions")
        or [],
    )
    if fix_versions:
        return fix_versions

    fixes = vulnerability.get("fixes", [])
    if not isinstance(fixes, list):
        return []
    versions = []
    for fix in fixes:
        if isinstance(fix, dict) and fix.get("version"):
            versions.append(str(fix["version"]))
        elif isinstance(fix, str):
            versions.append(fix)
    return versions


def _first_ghsa_identifier(identifiers: list[str]) -> str | None:
    for identifier in identifiers:
        if re.match(r"^GHSA-", identifier, re.IGNORECASE):
            return identifier.upper()
    return None


def _first_cve_identifier(identifiers: list[str]) -> str | None:
    for identifier in identifiers:
        if re.match(r"^CVE-", identifier, re.IGNORECASE):
            return identifier.upper()
    return None


def _parse_iso_date(value: str) -> date:
    """Parse an ISO date used by waiver expiry checks."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected YYYY-MM-DD, got {value!r}"
        ) from exc


def _normalize_ghsa_id(identifier: Any) -> str | None:
    if not identifier:
        return None
    return str(identifier).upper()


def _normalize_cve_id(identifier: Any) -> str | None:
    if not identifier:
        return None
    return str(identifier).upper()


def _normalize_advisory_identifier(identifier: str) -> str:
    """Normalize advisory IDs so waivers can match IDs or aliases."""
    return identifier.strip().upper()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    strings = [str(item).strip() for item in value if item]
    return [item for item in strings if item]


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _canonical_identifier(finding: Finding) -> str:
    if finding.ghsa_id:
        return finding.ghsa_id.upper()
    ghsa_id = _first_ghsa_identifier([finding.advisory_id, *finding.aliases])
    if ghsa_id:
        return ghsa_id
    if finding.cve_id:
        return finding.cve_id.upper()
    cve_id = _first_cve_identifier([finding.advisory_id, *finding.aliases])
    return cve_id or finding.advisory_id.upper()


def _severity_sort_key(severity: str) -> int:
    return SEVERITY_RANK.get(severity, len(SEVERITY_ORDER))


def _summary_status_line(report: dict[str, Any]) -> str:
    counts = report["counts"]
    if report["audit_error"]:
        return "❌ The audit result was unusable and the final gate will fail."
    if counts["blocking"]:
        return "❌ Blocking dependency vulnerabilities were found."
    if counts.get("waived_blocking", 0):
        return (
            "⚠️ Blocking dependency vulnerabilities were waived for this "
            "workflow context."
        )
    if counts["nonblocking"]:
        return "⚠️ Only medium/low dependency vulnerabilities were found."
    return "✅ No dependency vulnerabilities were found."


def _render_skipped_dependencies(
    skipped_dependencies: list[dict[str, Any]],
) -> list[str]:
    """Render skipped dependency details for the workflow summary."""
    lines = ["## Skipped/unauditable dependencies", ""]
    if not skipped_dependencies:
        lines.extend(["None.", ""])
        return lines

    lines.extend(
        [
            "These dependencies could not be audited by `pip-audit --strict`, ",
            "so the audit result is treated as a tooling error and the final ",
            "gate fails until the skip is resolved or explicitly investigated.",
            "",
            "| Package | Installed | Reason |",
            "| --- | --- | --- |",
        ]
    )
    for dependency in skipped_dependencies:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_escape(dependency["package"]),
                    _markdown_escape(dependency["installed_version"]),
                    _markdown_escape(dependency["skip_reason"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def _render_finding_sections(
    findings: list[dict[str, Any]],
    title: str,
) -> list[str]:
    lines = [f"## {title}", ""]
    if not findings:
        lines.extend(["None.", ""])
        return lines

    for severity in SEVERITY_ORDER:
        severity_findings = [
            finding for finding in findings if finding["severity"] == severity
        ]
        if not severity_findings:
            continue
        lines.extend(
            [
                f"### {severity.title()}",
                "",
                "| Package | Installed | Advisory | Fix versions | Reason |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for finding in severity_findings:
            lines.append(_finding_table_row(finding, include_reason=True))
        lines.append("")
    return lines


def _render_waived_finding_sections(
    findings: list[dict[str, Any]],
    title: str,
) -> list[str]:
    """Render waived blocking findings and the waiver metadata."""
    lines = [f"## {title}", ""]
    if not findings:
        lines.extend(["None.", ""])
        return lines

    lines.extend(
        [
            "These findings are still blocking-severity vulnerabilities, but "
            "the final gate allows them in this workflow context because an "
            "explicit, unexpired waiver matched the package and advisory.",
            "",
            "| Package | Installed | Advisory | Severity | Expires | Owner | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for finding in findings:
        waiver = finding.get("waiver", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_escape(finding["package"]),
                    _markdown_escape(finding["installed_version"]),
                    _advisory_cell(finding),
                    _markdown_escape(finding["severity"]),
                    _markdown_escape(str(waiver.get("expires_on", ""))),
                    _markdown_escape(str(waiver.get("owner", ""))),
                    _markdown_escape(str(waiver.get("reason", ""))),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def _finding_table_row(
    finding: dict[str, Any],
    include_reason: bool = False,
) -> str:
    fix_versions = ", ".join(finding.get("fix_versions", [])) or "None listed"
    cells = [
        _markdown_escape(finding["severity"]),
        _markdown_escape(finding["package"]),
        _markdown_escape(finding["installed_version"]),
        _advisory_cell(finding),
        _markdown_escape(fix_versions),
    ]
    if include_reason:
        cells = cells[1:]
        reason = (
            finding.get("unknown_reason")
            or finding.get("severity_source")
            or ""
        )
        cells.append(_markdown_escape(reason))
    return "| " + " | ".join(cells) + " |"


def _advisory_cell(finding: dict[str, Any]) -> str:
    """Render the advisory ID and aliases for summary tables."""
    aliases = ", ".join(finding.get("aliases", []))
    advisory = _markdown_escape(finding["advisory_id"])
    if aliases:
        return f"{advisory}<br>{_markdown_escape(aliases)}"
    return advisory


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _default_run_url() -> str | None:
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if repository and run_id:
        return f"{server_url}/{repository}/actions/runs/{run_id}"
    return None


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_github_outputs(path: Path, report: dict[str, Any]) -> None:
    counts = report["counts"]
    outputs = {
        "audit_error": str(report["audit_error"]).lower(),
        "blocking_count": str(counts["blocking"]),
        "waived_blocking_count": str(counts.get("waived_blocking", 0)),
        "nonblocking_count": str(counts["nonblocking"]),
        "unknown_count": str(counts["unknown"]),
        "skipped_count": str(counts.get("skipped", 0)),
        "has_waived_blocking": str(
            counts.get("waived_blocking", 0) > 0
        ).lower(),
        "has_nonblocking": str(counts["nonblocking"] > 0).lower(),
    }
    with path.open("a", encoding="utf-8") as output_file:
        for key, value in outputs.items():
            output_file.write(f"{key}={value}\n")


if __name__ == "__main__":
    raise SystemExit(main())
