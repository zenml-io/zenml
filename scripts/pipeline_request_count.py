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
"""Count the server requests made by minimal pipeline runs."""

import argparse
import json
import re
from collections import Counter
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

import requests

from zenml import pipeline, step

UUID_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


@step(enable_cache=False)
def produce() -> int:
    return 1


@step(enable_cache=False)
def transform(value: int) -> int:
    return value + 1


@step(enable_cache=False)
def noop() -> None:
    pass


@pipeline(dynamic=True, enable_cache=False)
def chain() -> None:
    first = produce()
    second = transform(first, id="transform_1")
    transform(second, id="transform_2")


@pipeline(dynamic=True, enable_cache=False)
def fanout() -> None:
    value = produce()
    transform(value, id="transform_1")
    transform(value, id="transform_2")


@pipeline(dynamic=True, enable_cache=False)
def disconnected() -> None:
    noop(id="noop_1")
    noop(id="noop_2")
    noop(id="noop_3")


# Three-step pipelines that differ only in how the steps are connected through
# artifacts: a linear chain (2 connections), a single producer feeding two
# consumers (2 connections), and three independent steps (0 connections).
PIPELINES = {
    "chain": chain,
    "fanout": fanout,
    "disconnected": disconnected,
}


def normalize_path(path: str) -> str:
    """Replace UUIDs in a request path with a placeholder.

    Args:
        path: Request path.

    Returns:
        Normalized path.
    """
    return UUID_REGEX.sub("{id}", path)


def measure(pipeline_instance: Any, server_netloc: str) -> Dict[str, Any]:
    """Run one pipeline and count the server requests it makes.

    Args:
        pipeline_instance: The pipeline to run.
        server_netloc: Network location of the ZenML server.

    Returns:
        The total and per-endpoint request counts.
    """
    counts: Counter[Tuple[str, str]] = Counter()
    original_send = requests.Session.send

    def counting_send(
        session: requests.Session,
        request: requests.PreparedRequest,
        **kwargs: Any,
    ) -> requests.Response:
        parsed = urlparse(request.url or "")
        if parsed.netloc == server_netloc:
            key = (request.method or "", normalize_path(parsed.path))
            counts[key] += 1

        return original_send(session, request, **kwargs)

    requests.Session.send = counting_send  # type: ignore[method-assign]
    try:
        pipeline_instance()
    finally:
        requests.Session.send = original_send  # type: ignore[method-assign]

    requests_by_endpoint = {
        f"{method} {path}": count
        for (method, path), count in sorted(counts.items())
    }

    return {
        "total": sum(requests_by_endpoint.values()),
        "requests": requests_by_endpoint,
    }


def run_and_count(output_file: str) -> None:
    """Run the pipelines and write per-pipeline request counts to a file.

    Args:
        output_file: Output JSON file.
    """
    from zenml.config.global_config import GlobalConfiguration

    server_netloc = urlparse(
        GlobalConfiguration().store_configuration.url
    ).netloc

    # Warm up so one-time client initialization (authentication, server info,
    # stack and project lookups) is not attributed to the measured pipelines.
    disconnected()

    result = {
        name: measure(pipeline_instance, server_netloc)
        for name, pipeline_instance in PIPELINES.items()
    }

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


def main() -> None:
    """Parse arguments and run the pipelines."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()

    run_and_count(output_file=args.output)


if __name__ == "__main__":
    main()
