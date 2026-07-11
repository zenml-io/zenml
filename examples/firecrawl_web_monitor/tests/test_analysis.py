"""Tests for the Firecrawl monitoring analysis helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from analysis import analyze_change  # noqa: E402
from create_firecrawl_monitor import build_monitor_request  # noqa: E402
from fetch_firecrawl_check import build_page_payloads  # noqa: E402
from models import (  # noqa: E402
    FirecrawlJudgment,
    FirecrawlPageData,
    FirecrawlWebhook,
    MeaningfulChange,
    PageChange,
)


def test_analysis_uses_firecrawl_judgment() -> None:
    """Firecrawl evidence should provide a useful no-credential fallback."""
    change = PageChange(
        event_id="event",
        monitor_id="monitor",
        check_id="check",
        url="https://example.com/pricing",
        status="changed",
        firecrawl_judgment=FirecrawlJudgment(
            meaningful=True,
            confidence="high",
            reason="The price changed.",
            meaningful_changes=[
                MeaningfulChange(
                    type="changed",
                    before="$19",
                    after="$24",
                    reason="Review pricing position.",
                )
            ],
        ),
    )

    result = analyze_change(change=change, goal="Track price changes")

    assert result.meaningful is True
    assert result.analyzer == "firecrawl-judgment-fallback"
    assert result.recommended_actions == ["Review pricing position."]


def test_analysis_counts_changed_lines_without_judgment() -> None:
    """Raw diffs should still generate a transparent offline report."""
    change = PageChange(
        event_id="event",
        monitor_id="monitor",
        check_id="check",
        url="https://example.com",
        status="changed",
        unified_diff="--- old\n+++ new\n-before\n+after\n",
    )

    result = analyze_change(change=change, goal="Track changes")

    assert result.meaningful is True
    assert "2 changed lines" in result.summary
    assert result.analyzer == "deterministic-fallback"


def test_monitor_request_defaults_to_pull_without_webhook() -> None:
    """Provisioning should request page scrapes and omit webhook config."""
    request = build_monitor_request(
        target_url="https://example.com/pricing",
        goal="Track prices",
        schedule="hourly",
    )

    assert request["targets"][0]["type"] == "scrape"
    assert request["targets"][0]["scrapeOptions"]["formats"] == ["markdown"]
    assert "webhook" not in request


def test_monitor_request_supports_optional_webhook() -> None:
    """An explicit webhook endpoint should be configured with its token."""
    request = build_monitor_request(
        target_url="https://example.com/pricing",
        goal="Track prices",
        schedule="hourly",
        webhook_url="https://hooks.example.com/webhooks/firecrawl",
        webhook_token="shared-secret",
    )

    assert request["webhook"]["events"] == ["monitor.page"]
    assert request["webhook"]["headers"]["Authorization"] == (
        "Bearer shared-secret"
    )


def test_baseline_page_with_null_diff_validates() -> None:
    """Baseline 'new' checks deliver an explicit null diff over the API."""
    page = FirecrawlPageData.model_validate(
        {
            "monitorId": "monitor-1",
            "checkId": "check-1",
            "url": "https://news.ycombinator.com/newest",
            "status": "new",
            "diff": None,
            "judgment": None,
        }
    )

    assert page.diff.text == ""
    assert page.diff.structured == {}


def test_check_pages_become_webhook_style_payloads() -> None:
    """Pulled check pages should validate as monitor.page payloads."""
    check = {
        "id": "check-1",
        "monitorId": "monitor-1",
        "status": "completed",
        "pages": [
            {
                "url": "https://example.com/pricing",
                "status": "changed",
                "diff": {"text": "-old\n+new"},
            },
            {
                "url": "https://example.com/blog",
                "status": "same",
            },
        ],
    }

    payloads = build_page_payloads(check)

    assert len(payloads) == 2
    events = [FirecrawlWebhook.model_validate(p) for p in payloads]
    assert all(e.type == "monitor.page" for e in events)
    assert events[0].data[0]["monitorId"] == "monitor-1"
    assert events[0].data[0]["checkId"] == "check-1"
