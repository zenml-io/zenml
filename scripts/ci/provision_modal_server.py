"""Provision or tear down a Modal-backed ZenML test server for CI."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
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
        app_name = deployment.app_name
        if app_name is None:
            raise RuntimeError(
                f"Deployment '{deployment_name}' did not expose a Modal app name."
            )

    _write_output("server_url", store_config.url)
    _write_output("sandbox_id", sandbox_id)
    _write_output("app_name", app_name)
    return 0


def _modal_environment_cli_args() -> list[str]:
    """Returns Modal CLI args for the selected environment, if any."""
    modal_environment = os.getenv("MODAL_ENVIRONMENT")
    if modal_environment:
        return ["--env", modal_environment]
    return []


def _stop_modal_app(app_name: str) -> None:
    """Stops the Modal app created only to host the server sandbox."""
    modal_command = shutil.which("modal")
    if modal_command is None:
        logging.warning(
            "Unable to stop Modal app '%s': modal CLI not found.", app_name
        )
        return

    command = [
        modal_command,
        "app",
        "stop",
        app_name,
        *_modal_environment_cli_args(),
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logging.warning(
            "Unable to stop Modal app '%s' (exit %s): %s%s",
            app_name,
            result.returncode,
            result.stdout,
            result.stderr,
        )
        return

    logging.info("Stopped Modal app %s.", app_name)


def teardown(sandbox_id: str, app_name: str | None = None) -> int:
    """Terminates a previously provisioned Modal sandbox and app."""
    import modal

    sandbox_terminated = False
    with modal.enable_output():
        try:
            sandbox = modal.Sandbox.from_id(sandbox_id)
            sandbox.terminate()
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if sandbox.poll() is not None:
                    sandbox_terminated = True
                    break
                time.sleep(2)
            else:
                # Visible in GitHub Actions log; sandbox may leak otherwise.
                print(
                    f"::warning::Modal sandbox {sandbox_id} did not report "
                    "termination within 60s and may still be running.",
                    file=sys.stderr,
                )
        except Exception as exc:
            # Surface as an annotation so CI viewers can spot leaked sandboxes.
            print(
                f"::warning::Unable to terminate Modal sandbox {sandbox_id}: "
                f"{exc}",
                file=sys.stderr,
            )

    if sandbox_terminated:
        logging.info("Terminated Modal sandbox %s.", sandbox_id)
    if app_name:
        _stop_modal_app(app_name)
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
    parser.add_argument(
        "--app-name",
        help="Modal app name to stop when using the teardown action.",
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
        return teardown(args.sandbox_id, app_name=args.app_name)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
