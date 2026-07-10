"""Run the Firecrawl monitoring pipeline from a JSON payload."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from constants import DEFAULT_GOAL
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
    pipeline_instance(
        payload=load_payload(args.payload),
        goal=args.goal,
        notify_slack=args.notify_slack,
        llm_secret_name=args.llm_secret,
    )


if __name__ == "__main__":
    main()
