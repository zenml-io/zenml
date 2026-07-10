"""Create a Firecrawl page monitor that sends diffs to the local receiver."""

import argparse
import os
from typing import Any, Dict, Optional

import requests
from constants import DEFAULT_GOAL


def build_monitor_request(
    target_url: str,
    webhook_url: str,
    goal: str,
    schedule: str,
    webhook_token: Optional[str],
) -> Dict[str, Any]:
    """Build a Firecrawl v2 monitor request.

    Args:
        target_url: Page that Firecrawl should monitor and scrape.
        webhook_url: Public receiver URL.
        goal: Meaningful-change goal.
        schedule: Firecrawl natural-language schedule.
        webhook_token: Optional shared receiver token.

    Returns:
        Firecrawl monitor request body.
    """
    headers = (
        {"Authorization": f"Bearer {webhook_token}"} if webhook_token else {}
    )
    return {
        "name": f"ZenML monitor: {target_url}",
        "schedule": {"text": schedule, "timezone": "UTC"},
        "goal": goal,
        "targets": [
            {
                "type": "scrape",
                "urls": [target_url],
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
            }
        ],
        "webhook": {
            "url": webhook_url,
            "headers": headers,
            "metadata": {"source": "zenml-firecrawl-example"},
            "events": ["monitor.page", "monitor.check.completed"],
        },
    }


def main() -> None:
    """Create a monitor using credentials from the environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--webhook-url", required=True)
    parser.add_argument("--goal", default=DEFAULT_GOAL)
    parser.add_argument("--schedule", default="hourly")
    args = parser.parse_args()

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("Set FIRECRAWL_API_KEY before creating a monitor.")

    response = requests.post(
        "https://api.firecrawl.dev/v2/monitor",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=build_monitor_request(
            target_url=args.target_url,
            webhook_url=args.webhook_url,
            goal=args.goal,
            schedule=args.schedule,
            webhook_token=os.getenv("FIRECRAWL_WEBHOOK_TOKEN"),
        ),
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    monitor_id = body.get("id") or body.get("data", {}).get("id", "<unknown>")
    print(f"Created Firecrawl monitor: {monitor_id}")


if __name__ == "__main__":
    main()
