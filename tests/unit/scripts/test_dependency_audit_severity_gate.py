"""Tests for the dependency audit severity gate helper."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError

import pytest
from scripts import dependency_audit_severity_gate as gate


class FakeGitHubResponse:
    """Minimal context-manager response used to mock urllib."""

    def __init__(self, payload: Any) -> None:
        """Store the response payload."""
        self._payload = payload

    def __enter__(self) -> "FakeGitHubResponse":
        """Return this response for with-statement usage."""
        return self

    def __exit__(self, *args: object) -> None:
        """Leave the mocked context manager without cleanup."""
        return None

    def read(self) -> bytes:
        """Return the payload as JSON bytes."""
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")


def audit_data(
    *vulnerabilities: tuple[str, str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a small pip-audit JSON payload."""
    dependencies: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for package, version, vulnerability in vulnerabilities:
        dependencies.setdefault((package, version), []).append(vulnerability)
    return {
        "dependencies": [
            {"name": package, "version": version, "vulns": vulns}
            for (package, version), vulns in dependencies.items()
        ]
    }


def vulnerability(
    advisory_id: str,
    aliases: list[str] | None = None,
    fix_versions: list[str] | None = None,
) -> dict[str, Any]:
    """Build a small pip-audit vulnerability entry."""
    return {
        "id": advisory_id,
        "aliases": aliases or [],
        "fix_versions": fix_versions or [],
        "description": f"Description for {advisory_id}",
    }


def install_fake_github_api(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, Any],
    requested: list[Any] | None = None,
) -> None:
    """Mock GitHub Advisory API responses by URL."""

    def fake_urlopen(request: Any, timeout: int) -> FakeGitHubResponse:
        if requested is not None:
            requested.append(request)
        payload = responses[request.full_url]
        if isinstance(payload, BaseException):
            raise payload
        return FakeGitHubResponse(payload)

    monkeypatch.setattr(gate, "urlopen", fake_urlopen)


def classify(
    data: dict[str, Any],
    token: str | None = "token",
) -> dict[str, Any]:
    """Classify fixture audit data through the real helper path."""
    return gate.classify_audit(data, gate.GitHubAdvisoryClient(token=token))


def test_no_vulnerabilities_pass_without_findings() -> None:
    """An empty pip-audit result should produce an all-clear report."""
    report = classify({"dependencies": []})

    assert report["counts"] == {
        "total": 0,
        "blocking": 0,
        "nonblocking": 0,
        "unknown": 0,
        "skipped": 0,
    }
    assert "No dependency vulnerabilities" in gate.render_summary(report)


def test_strict_skip_with_no_vulnerabilities_is_audit_error(
    tmp_path: Any,
) -> None:
    """A skipped dependency makes strict audit output unusable."""
    audit_json = tmp_path / "pip-audit.json"
    classified_json = tmp_path / "classified.json"
    summary_md = tmp_path / "summary.md"
    issue_md = tmp_path / "issue.md"
    github_output = tmp_path / "github-output.txt"
    audit_json.write_text(
        json.dumps(
            {
                "dependencies": [
                    {
                        "name": "skipped-package",
                        "version": "1.0.0",
                        "vulns": [],
                        "skip_reason": "package was not found on PyPI",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = gate.main(
        [
            "--audit-json",
            str(audit_json),
            "--pip-audit-exit-code",
            "1",
            "--classified-json",
            str(classified_json),
            "--summary-md",
            str(summary_md),
            "--nonblocking-issue-md",
            str(issue_md),
            "--github-output",
            str(github_output),
        ]
    )

    classified = json.loads(classified_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert classified["audit_error"] is True
    assert classified["counts"]["skipped"] == 1
    assert classified["counts"]["blocking"] == 0
    assert "skipped-package" in classified["audit_error_message"]
    assert "audit_error=true" in github_output.read_text(encoding="utf-8")
    summary = summary_md.read_text(encoding="utf-8")
    assert "Skipped/unauditable dependencies" in summary
    assert "package was not found on PyPI" in summary


def test_strict_skip_preserves_vulnerability_classification(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skipped deps fail the audit while vulnerabilities still classify."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-LOWW-1111-2222": {
                "ghsa_id": "GHSA-loww-1111-2222",
                "severity": "low",
            }
        },
    )
    audit_json = tmp_path / "pip-audit.json"
    classified_json = tmp_path / "classified.json"
    summary_md = tmp_path / "summary.md"
    issue_md = tmp_path / "issue.md"
    github_output = tmp_path / "github-output.txt"
    audit_json.write_text(
        json.dumps(
            {
                "dependencies": [
                    {
                        "name": "vulnerable-package",
                        "version": "2.0.0",
                        "vulns": [vulnerability("GHSA-loww-1111-2222")],
                    },
                    {
                        "name": "skipped-package",
                        "version": "1.0.0",
                        "vulns": [],
                        "skip_reason": "package was not found on PyPI",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = gate.main(
        [
            "--audit-json",
            str(audit_json),
            "--pip-audit-exit-code",
            "1",
            "--classified-json",
            str(classified_json),
            "--summary-md",
            str(summary_md),
            "--nonblocking-issue-md",
            str(issue_md),
            "--github-output",
            str(github_output),
        ]
    )

    classified = json.loads(classified_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert classified["audit_error"] is True
    assert classified["counts"]["skipped"] == 1
    assert classified["counts"]["nonblocking"] == 1
    assert classified["nonblocking"][0]["package"] == "vulnerable-package"
    assert classified["nonblocking"][0]["severity"] == "low"
    assert (
        classified["skipped_dependencies"][0]["package"] == "skipped-package"
    )
    assert "audit_error=true" in github_output.read_text(encoding="utf-8")


def test_malformed_dependency_entries_are_audit_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed entries should fail the audit but preserve valid findings."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-LOWW-1111-2222": {
                "ghsa_id": "GHSA-loww-1111-2222",
                "severity": "low",
            }
        },
    )

    report = classify(
        {
            "dependencies": [
                "not-an-object",
                {"name": "bad-vulns", "version": "1.0.0", "vulns": "bad"},
                {
                    "name": "mixed-vulns",
                    "version": "2.0.0",
                    "vulns": [
                        "not-an-object",
                        vulnerability("GHSA-loww-1111-2222"),
                    ],
                },
            ]
        }
    )

    assert report["audit_error"] is True
    assert "Malformed pip-audit JSON" in report["audit_error_message"]
    assert (
        "dependency entry 0 was not an object" in report["audit_error_message"]
    )
    assert (
        "dependency 'bad-vulns' field 'vulns' was not a list"
        in report["audit_error_message"]
    )
    assert (
        "vulnerability entry 0 was not an object"
        in report["audit_error_message"]
    )
    assert report["counts"]["nonblocking"] == 1
    assert report["nonblocking"][0]["package"] == "mixed-vulns"


def test_malformed_dependencies_field_is_an_audit_error() -> None:
    """A non-list dependencies field should not crash classification."""
    report = classify({"dependencies": {"name": "not-a-list"}})

    assert report["audit_error"] is True
    assert (
        "field 'dependencies' was not a list" in report["audit_error_message"]
    )
    assert report["counts"]["total"] == 0


def test_empty_github_token_omits_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pull request runs pass an empty advisory token."""
    requested: list[Any] = []
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-LOWW-1111-2222": {
                "ghsa_id": "GHSA-loww-1111-2222",
                "severity": "low",
            }
        },
        requested,
    )

    report = classify(
        audit_data(
            ("package-a", "1.0.0", vulnerability("GHSA-loww-1111-2222"))
        ),
        token="",
    )

    assert report["counts"]["nonblocking"] == 1
    assert requested[0].get_header("Authorization") is None


def test_medium_and_low_findings_are_nonblocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Medium and low GitHub severities should pass the final gate."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-MMMM-1111-2222": {
                "ghsa_id": "GHSA-mmmm-1111-2222",
                "severity": "medium",
            },
            "https://api.github.com/advisories?cve_id=CVE-2026-0001&ecosystem=pip&affects=package-b&per_page=100": [
                {
                    "ghsa_id": "GHSA-llll-1111-2222",
                    "cve_id": "CVE-2026-0001",
                    "severity": "low",
                    "vulnerabilities": [
                        {"package": {"ecosystem": "pip", "name": "package-b"}}
                    ],
                }
            ],
        },
    )

    report = classify(
        audit_data(
            (
                "package-a",
                "1.0.0",
                vulnerability("GHSA-mmmm-1111-2222"),
            ),
            (
                "package-b",
                "2.0.0",
                vulnerability("PYSEC-1", aliases=["CVE-2026-0001"]),
            ),
        )
    )

    assert report["counts"]["blocking"] == 0
    assert report["counts"]["nonblocking"] == 2
    assert {item["severity"] for item in report["nonblocking"]} == {
        "medium",
        "low",
    }


def test_high_and_critical_findings_are_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """High and critical GitHub severities should fail the final gate."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-HIGH-1111-2222": {
                "ghsa_id": "GHSA-high-1111-2222",
                "severity": "high",
            },
            "https://api.github.com/advisories/GHSA-CRIT-1111-2222": {
                "ghsa_id": "GHSA-crit-1111-2222",
                "severity": "critical",
            },
        },
    )

    report = classify(
        audit_data(
            ("package-a", "1.0.0", vulnerability("GHSA-high-1111-2222")),
            ("package-b", "2.0.0", vulnerability("GHSA-crit-1111-2222")),
        )
    )

    assert report["counts"]["blocking"] == 2
    assert report["counts"]["nonblocking"] == 0
    assert {item["severity"] for item in report["blocking"]} == {
        "critical",
        "high",
    }


def test_unmapped_advisory_becomes_unknown_and_blocks() -> None:
    """PYSEC/OSV-only findings should block when no GHSA/CVE is present."""
    report = classify(
        audit_data(("package-a", "1.0.0", vulnerability("PYSEC-2026-1")))
    )

    finding = report["blocking"][0]
    assert finding["severity"] == "unknown"
    assert finding["unknown_reason"] == gate.UNKNOWN_UNMAPPED_ADVISORY
    assert report["counts"]["blocking"] == 1


def test_github_api_failure_becomes_unknown_and_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed severity lookup should be safe by default and block."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-FAIL-1111-2222": URLError(
                "temporary failure"
            )
        },
    )

    report = classify(
        audit_data(
            ("package-a", "1.0.0", vulnerability("GHSA-fail-1111-2222"))
        )
    )

    finding = report["blocking"][0]
    assert finding["severity"] == "unknown"
    assert finding["unknown_reason"] == gate.UNKNOWN_GITHUB_API_ERROR


def test_ghsa_and_cve_lookup_paths_use_github_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GHSA IDs should use the detail endpoint; CVEs should use list lookup."""
    requested: list[Any] = []
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-ABCD-1111-2222": {
                "ghsa_id": "GHSA-abcd-1111-2222",
                "severity": "medium",
            },
            "https://api.github.com/advisories?cve_id=CVE-2026-1234&ecosystem=pip&affects=package-b&per_page=100": [
                {
                    "ghsa_id": "GHSA-wxyz-1111-2222",
                    "cve_id": "CVE-2026-1234",
                    "severity": "high",
                    "vulnerabilities": [
                        {"package": {"ecosystem": "pip", "name": "package-b"}}
                    ],
                }
            ],
        },
        requested,
    )

    report = classify(
        audit_data(
            ("package-a", "1.0.0", vulnerability("GHSA-abcd-1111-2222")),
            (
                "package-b",
                "2.0.0",
                vulnerability("PYSEC-1", ["CVE-2026-1234"]),
            ),
        ),
        token="secret-token",
    )

    assert report["counts"]["total"] == 2
    assert [request.full_url for request in requested] == [
        "https://api.github.com/advisories/GHSA-ABCD-1111-2222",
        "https://api.github.com/advisories?cve_id=CVE-2026-1234&ecosystem=pip&affects=package-b&per_page=100",
    ]
    assert all(
        request.get_header("Authorization") == "Bearer secret-token"
        for request in requested
    )


def test_cve_lookup_filters_to_matching_python_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CVE lookup should not trust an unrelated first advisory."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories?cve_id=CVE-2026-9999&ecosystem=pip&affects=package-a&per_page=100": [
                {
                    "ghsa_id": "GHSA-npmx-1111-2222",
                    "cve_id": "CVE-2026-9999",
                    "severity": "low",
                    "vulnerabilities": [
                        {"package": {"ecosystem": "npm", "name": "package-a"}}
                    ],
                },
                {
                    "ghsa_id": "GHSA-pipm-1111-2222",
                    "cve_id": "CVE-2026-9999",
                    "severity": "medium",
                    "vulnerabilities": [
                        {"package": {"ecosystem": "pip", "name": "package-a"}}
                    ],
                },
                {
                    "ghsa_id": "GHSA-piph-1111-2222",
                    "cve_id": "CVE-2026-9999",
                    "severity": "high",
                    "vulnerabilities": [
                        {"package": {"ecosystem": "pip", "name": "package-a"}}
                    ],
                },
            ]
        },
    )

    report = classify(
        audit_data(
            ("package-a", "1.0.0", vulnerability("PYSEC-1", ["CVE-2026-9999"]))
        )
    )

    assert report["counts"]["blocking"] == 1
    assert report["blocking"][0]["severity"] == "high"
    assert report["blocking"][0]["ghsa_id"] == "GHSA-PIPH-1111-2222"


def test_malformed_github_json_becomes_invalid_response_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed GitHub JSON should produce a clear unknown reason."""
    install_fake_github_api(
        monkeypatch,
        {"https://api.github.com/advisories/GHSA-JSON-1111-2222": b"not-json"},
    )

    report = classify(
        audit_data(
            ("package-a", "1.0.0", vulnerability("GHSA-json-1111-2222"))
        )
    )

    assert report["counts"]["blocking"] == 1
    assert (
        report["blocking"][0]["unknown_reason"]
        == gate.UNKNOWN_INVALID_RESPONSE
    )


def test_duplicate_package_advisory_findings_are_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated package/advisory pairs should appear once in reports."""
    requested: list[Any] = []
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-DUPE-1111-2222": {
                "ghsa_id": "GHSA-dupe-1111-2222",
                "severity": "medium",
            }
        },
        requested,
    )

    report = classify(
        audit_data(
            ("Package_A", "1.0.0", vulnerability("GHSA-dupe-1111-2222")),
            (
                "package-a",
                "1.0.0",
                vulnerability("PYSEC-1", ["GHSA-dupe-1111-2222"]),
            ),
        )
    )

    assert report["counts"]["total"] == 1
    assert len(requested) == 1


def test_tracking_issue_body_includes_only_nonblocking_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tracking issue is a backlog for medium/low findings only."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-HIGH-1111-2222": {
                "ghsa_id": "GHSA-high-1111-2222",
                "severity": "high",
            },
            "https://api.github.com/advisories/GHSA-LOWW-1111-2222": {
                "ghsa_id": "GHSA-loww-1111-2222",
                "severity": "low",
            },
        },
    )
    report = classify(
        audit_data(
            (
                "blocking-package",
                "1.0.0",
                vulnerability("GHSA-high-1111-2222"),
            ),
            (
                "tracking-package",
                "2.0.0",
                vulnerability("GHSA-loww-1111-2222"),
            ),
        )
    )

    body = gate.render_tracking_issue_body(
        report,
        "https://github.com/zenml-io/zenml/actions/runs/1",
    )

    assert gate.TRACKING_ISSUE_MARKER in body
    assert "tracking-package" in body
    assert "GHSA-loww-1111-2222" in body
    assert "blocking-package" not in body
    assert "GHSA-high-1111-2222" not in body


def test_main_writes_compact_outputs(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI should write artifacts and small GitHub Actions outputs."""
    install_fake_github_api(
        monkeypatch,
        {
            "https://api.github.com/advisories/GHSA-LOWW-1111-2222": {
                "ghsa_id": "GHSA-loww-1111-2222",
                "severity": "low",
            }
        },
    )
    audit_json = tmp_path / "pip-audit.json"
    classified_json = tmp_path / "classified.json"
    summary_md = tmp_path / "summary.md"
    issue_md = tmp_path / "issue.md"
    github_output = tmp_path / "github-output.txt"
    audit_json.write_text(
        json.dumps(
            audit_data(
                ("package-a", "1.0.0", vulnerability("GHSA-loww-1111-2222"))
            )
        ),
        encoding="utf-8",
    )

    exit_code = gate.main(
        [
            "--audit-json",
            str(audit_json),
            "--pip-audit-exit-code",
            "1",
            "--classified-json",
            str(classified_json),
            "--summary-md",
            str(summary_md),
            "--nonblocking-issue-md",
            str(issue_md),
            "--github-output",
            str(github_output),
        ]
    )

    assert exit_code == 0
    assert (
        json.loads(classified_json.read_text(encoding="utf-8"))["counts"][
            "nonblocking"
        ]
        == 1
    )
    assert "Only medium/low" in summary_md.read_text(encoding="utf-8")
    assert "has_nonblocking=true" in github_output.read_text(encoding="utf-8")
    assert "blocking_count=0" in github_output.read_text(encoding="utf-8")
