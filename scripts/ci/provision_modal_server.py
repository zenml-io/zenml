"""Provision or tear down a Modal-backed ZenML test server for CI."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from tests.harness.deployment.server_modal_mysql import (  # noqa: E402
    ServerModalMySQLTestDeployment,
)
from tests.harness.harness import TestHarness  # noqa: E402

DEFAULT_DEPLOYMENT = "modal-server-mysql"


def _write_output(name: str, value: str) -> None:
    """Writes a GitHub Actions output without leaking values in CI logs."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output_file:
            output_file.write(f"{name}={value}\n")
        print(f"{name}=<written to GITHUB_OUTPUT>")
        return

    print(f"{name}={value}")


def _get_modal_deployment(
    deployment_name: str,
) -> ServerModalMySQLTestDeployment:
    """Returns the configured Modal MySQL deployment instance."""
    deployment = TestHarness().get_deployment(deployment_name)
    if not isinstance(deployment, ServerModalMySQLTestDeployment):
        raise TypeError(
            f"Deployment '{deployment_name}' is not a Modal MySQL deployment."
        )
    return deployment


def provision(deployment_name: str) -> int:
    """Provisions a Modal MySQL deployment and emits its connection info."""
    import modal

    with modal.enable_output():
        deployment = _get_modal_deployment(deployment_name)
        deployment.up()

        store_config = deployment.get_store_config()
        if store_config is None:
            raise RuntimeError(
                f"Deployment '{deployment_name}' did not produce a store config."
            )

        sandbox_id = deployment.sandbox_id
        if sandbox_id is None:
            raise RuntimeError(
                f"Deployment '{deployment_name}' did not expose a sandbox ID."
            )

    _write_output("server_url", store_config.url)
    _write_output("sandbox_id", sandbox_id)
    return 0


def teardown(sandbox_id: str) -> int:
    """Terminates a previously provisioned Modal sandbox."""
    import modal

    with modal.enable_output():
        sandbox = modal.Sandbox.from_id(sandbox_id)
        sandbox.terminate()

    logging.info("Terminated Modal sandbox %s.", sandbox_id)
    return 0


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Provision or tear down the Modal-backed ZenML test server used "
            "by CI offload runs."
        )
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=["provision", "teardown"],
        default="provision",
        help="Action to perform.",
    )
    parser.add_argument(
        "--deployment",
        default=DEFAULT_DEPLOYMENT,
        help="Harness deployment name to provision.",
    )
    parser.add_argument(
        "--sandbox-id",
        help="Sandbox ID to terminate when using the teardown action.",
    )
    return parser.parse_args()


def main() -> int:
    """Runs the requested action."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()

    try:
        if args.action == "provision":
            return provision(args.deployment)
        if not args.sandbox_id:
            raise ValueError("--sandbox-id is required for teardown.")
        return teardown(args.sandbox_id)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
