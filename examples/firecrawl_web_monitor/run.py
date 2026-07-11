"""Run the Firecrawl monitoring pipeline from a JSON payload or the API."""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from constants import DEFAULT_GOAL
from fetch_firecrawl_check import build_page_payloads, fetch_check
from pipelines.monitoring import firecrawl_web_monitor_pipeline


def load_payload(path: Path) -> Dict[str, Any]:
    """Load a Firecrawl webhook payload.

    Args:
        path: JSON payload path.

    Returns:
        Parsed JSON object.
    """
    with path.open(encoding="utf-8") as payload_file:
        payload: Dict[str, Any] = json.load(payload_file)
    return payload


def collect_payloads(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """Gather one payload per page, from the Firecrawl API or a local file.

    Args:
        args: Parsed CLI arguments.

    Raises:
        RuntimeError: If ``--monitor-id`` is used without FIRECRAWL_API_KEY.

    Returns:
        Payloads to run the pipeline on, one per page result.
    """
    if args.monitor_id:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set FIRECRAWL_API_KEY to pull checks with --monitor-id."
            )
        check = fetch_check(
            api_key=api_key,
            monitor_id=args.monitor_id,
            check_id=args.check_id,
        )
        return build_page_payloads(check)
    return [load_payload(args.payload)]


def main() -> None:
    """Parse CLI arguments and start the pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "configs/dev.yaml",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=Path(__file__).with_name("sample_payload.json"),
    )
    parser.add_argument(
        "--monitor-id",
        default=None,
        help="Pull the latest completed check of this Firecrawl monitor "
        "instead of reading --payload. Requires FIRECRAWL_API_KEY.",
    )
    parser.add_argument(
        "--check-id",
        default=None,
        help="Specific check to pull with --monitor-id. Defaults to the "
        "latest completed check.",
    )
    parser.add_argument("--goal", default=DEFAULT_GOAL)
    parser.add_argument("--notify-slack", action="store_true")
    parser.add_argument(
        "--llm-secret",
        default=None,
        help="ZenML secret containing OPENAI_API_KEY and optional OPENAI_MODEL.",
    )
    args = parser.parse_args()

    pipeline_instance = firecrawl_web_monitor_pipeline.with_options(
        config_path=str(args.config), enable_cache=False
    )
    for payload in collect_payloads(args):
        pipeline_instance(
            payload=payload,
            goal=args.goal,
            notify_slack=args.notify_slack,
            llm_secret_name=args.llm_secret,
        )


if __name__ == "__main__":
    main()
