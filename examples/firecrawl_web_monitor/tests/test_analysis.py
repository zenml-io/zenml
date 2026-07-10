"""Tests for the Firecrawl monitoring analysis helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from analysis import analyze_change  # noqa: E402
from create_firecrawl_monitor import build_monitor_request  # noqa: E402
from models import (  # noqa: E402
    FirecrawlJudgment,
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


def test_monitor_request_configures_scraping_and_webhooks() -> None:
    """Provisioning should request page scrapes and both monitor events."""
    request = build_monitor_request(
        target_url="https://example.com/pricing",
        webhook_url="https://hooks.example.com/webhooks/firecrawl",
        goal="Track prices",
        schedule="hourly",
        webhook_token="shared-secret",
    )

    assert request["targets"][0]["type"] == "scrape"
    assert request["targets"][0]["scrapeOptions"]["formats"] == ["markdown"]
    assert request["webhook"]["events"] == [
        "monitor.page",
        "monitor.check.completed",
    ]
    assert request["webhook"]["headers"]["Authorization"] == (
        "Bearer shared-secret"
    )
