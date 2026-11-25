"""Tests for docs link checker policy exemptions."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load_link_checker_module() -> ModuleType:
    """Load the standalone docs link checker script as a module."""
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "docs" / "link_checker.py"
    spec = importlib.util.spec_from_file_location(
        "docs_link_checker", module_path
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


link_checker = load_link_checker_module()


@pytest.mark.parametrize(
    ("host", "domain", "expected"),
    [
        ("modal.com", "modal.com", True),
        ("docs.modal.com", "modal.com", True),
        ("a.b.modal.com", "modal.com", True),
        ("evilmodal.com", "modal.com", False),
        ("notsegment.com", "segment.com", False),
        ("modal.com.evil.example", "modal.com", False),
    ],
)
def test_host_matches_domain_only_matches_exact_hosts_or_subdomains(
    host: str, domain: str, expected: bool
) -> None:
    """Check that domain matching excludes unsafe suffix matches."""
    assert link_checker.host_matches_domain(host, domain) is expected


@pytest.mark.parametrize(
    ("url", "status_code"),
    [
        ("https://modal.com", 403),
        ("https://modal.com", 406),
        ("https://modal.com/", 403),
        ("https://modal.com/signup", 403),
        ("https://modal.com/signup", 406),
        ("https://modal.com/docs/guide/gpu", 403),
        ("https://modal.com/docs/guide/gpu", 406),
        ("https://modal.com/docs/guide/region-selection", 403),
        ("https://modal.com/docs/guide/region-selection", 406),
        ("https://segment.com", 403),
        ("https://segment.com/", 403),
    ],
)
def test_modal_and_segment_approved_urls_are_exempt(
    url: str, status_code: int
) -> None:
    """Check exact approved Modal and Segment URL exemptions."""
    assert link_checker.is_exception_status(url, status_code) is True


@pytest.mark.parametrize(
    ("url", "status_code"),
    [
        ("https://modal.com/unknown", 403),
        ("https://modal.com/unknown", 406),
        ("https://docs.modal.com", 403),
        ("https://segment.com/docs", 403),
        ("https://api.segment.com", 403),
        ("https://modal.com", 404),
        ("https://modal.com", 410),
        ("https://segment.com", 404),
        ("https://segment.com", 410),
        ("https://segment.com", 406),
    ],
)
def test_modal_and_segment_unapproved_urls_or_statuses_are_not_exempt(
    url: str, status_code: int
) -> None:
    """Check broad Modal and Segment domain exemptions are gone."""
    assert link_checker.is_exception_status(url, status_code) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.aws.amazon.com/general/latest/gr/apprunner.html",
        "https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html",
        "https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html",
    ],
)
def test_aws_documentation_and_reference_hosts_allow_403(url: str) -> None:
    """Check focused AWS documentation and reference host exemptions."""
    assert link_checker.is_exception_status(url, 403) is True


@pytest.mark.parametrize(
    ("url", "status_code"),
    [
        ("https://aws.amazon.com/apprunner/", 403),
        ("https://aws.amazon.com/cli/", 403),
        ("https://aws.amazon.com/s3/", 403),
        ("https://docs.aws.amazon.com/general/latest/gr/apprunner.html", 404),
        ("https://docs.aws.amazon.com/general/latest/gr/apprunner.html", 410),
        (
            "https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html",
            404,
        ),
        (
            "https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html",
            410,
        ),
    ],
)
def test_aws_product_urls_and_hard_failures_are_not_exempt(
    url: str, status_code: int
) -> None:
    """Check broad AWS product URLs and hard failures still fail."""
    assert link_checker.is_exception_status(url, status_code) is False


def test_ghcr_502_exemption_remains_intentional() -> None:
    """Check the policy still includes the intentional ghcr.io 502 case."""
    assert link_checker.is_exception_status("https://ghcr.io", 502) is True
