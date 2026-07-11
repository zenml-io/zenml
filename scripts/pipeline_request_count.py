#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Count the server requests made by a minimal pipeline run."""

import argparse
import json
import re
from collections import Counter
from typing import Any, Tuple
from urllib.parse import urlparse

import requests

from zenml import pipeline, step

UUID_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


@step
def noop_step() -> None:
    pass


@pipeline(enable_cache=False)
def request_count_pipeline() -> None:
    noop_step()
    noop_step()
    noop_step()


def normalize_path(path: str) -> str:
    """Replace UUIDs in a request path with a placeholder.

    Args:
        path: Request path.

    Returns:
        Normalized path.
    """
    return UUID_REGEX.sub("{id}", path)


def run_and_count(output_file: str) -> None:
    """Run the pipeline and write per-endpoint request counts to a file.

    Args:
        output_file: Output JSON file.
    """
    counts: Counter[Tuple[str, str, str]] = Counter()
    original_send = requests.Session.send

    def counting_send(
        session: requests.Session,
        request: requests.PreparedRequest,
        **kwargs: Any,
    ) -> requests.Response:
        parsed = urlparse(request.url or "")
        key = (
            parsed.netloc,
            request.method or "",
            normalize_path(parsed.path),
        )
        counts[key] += 1

        return original_send(session, request, **kwargs)

    requests.Session.send = counting_send  # type: ignore[method-assign]
    try:
        request_count_pipeline()
    finally:
        requests.Session.send = original_send  # type: ignore[method-assign]

    from zenml.config.global_config import GlobalConfiguration

    server_netloc = urlparse(
        GlobalConfiguration().store_configuration.url
    ).netloc
    requests_by_endpoint = {
        f"{method} {path}": count
        for (netloc, method, path), count in sorted(counts.items())
        if netloc == server_netloc
    }
    result = {
        "total": sum(requests_by_endpoint.values()),
        "requests": requests_by_endpoint,
    }

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


def main() -> None:
    """Parse arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()

    run_and_count(output_file=args.output)


if __name__ == "__main__":
    main()
