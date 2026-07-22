"""Create a Firecrawl page monitor whose checks the pipeline can pull."""

import argparse
import os
from typing import Any, Dict, Optional

import requests
from constants import DEFAULT_GOAL


def build_monitor_request(
    target_url: str,
    goal: str,
    schedule: str,
    webhook_url: Optional[str] = None,
    webhook_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a Firecrawl v2 monitor request.

    Args:
        target_url: Page that Firecrawl should monitor and scrape.
        goal: Meaningful-change goal.
        schedule: Firecrawl natural-language schedule.
        webhook_url: Optional delivery endpoint. Without it, checks are
            pulled via the API (``run.py --monitor-id``).
        webhook_token: Optional bearer token for the webhook endpoint.

    Returns:
        Firecrawl monitor request body.
    """
    request: Dict[str, Any] = {
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
    }
    if webhook_url:
        headers = (
            {"Authorization": f"Bearer {webhook_token}"}
            if webhook_token
            else {}
        )
        request["webhook"] = {
            "url": webhook_url,
            "headers": headers,
            "metadata": {"source": "zenml-firecrawl-example"},
            "events": ["monitor.page"],
        }
    return request


def main() -> None:
    """Create a monitor using credentials from the environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--goal", default=DEFAULT_GOAL)
    parser.add_argument("--schedule", default="hourly")
    parser.add_argument(
        "--webhook-url",
        default=None,
        help="Optional endpoint Firecrawl should POST monitor.page events "
        "to, e.g. a relay that triggers a ZenML pipeline snapshot. Omit it "
        "to pull checks with `run.py --monitor-id` instead.",
    )
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
            goal=args.goal,
            schedule=args.schedule,
            webhook_url=args.webhook_url,
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
