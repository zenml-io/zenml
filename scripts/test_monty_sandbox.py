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
"""Manual smoke test for the Phase 7 Monty sandbox implementation."""

import json

__test__ = False

from zenml import pipeline, step
from zenml.client import Client
from zenml.sandboxes import SandboxCapability, SandboxExecError
from zenml.steps import get_step_context


def _registration_commands() -> str:
    """Returns sandbox and stack registration commands for this smoke test."""
    return "\n".join(
        [
            "zenml integration install monty",
            "zenml sandbox register monty-sb --flavor monty",
            (
                "zenml stack register monty-sandbox-stack "
                "-o default -a default --sandbox monty-sb"
            ),
            "zenml stack set monty-sandbox-stack",
        ]
    )


@step(sandbox=True)
def monty_sandbox_smoke_step() -> str:
    """Executes a Monty sandbox smoke test inside a sandbox-enabled step."""
    context = get_step_context()
    if context.sandbox is None:
        raise RuntimeError(
            "No sandbox component is active in the current stack."
        )

    with context.sandbox.session(
        timeout_seconds=60,
        env={"ZENML_SANDBOX_SMOKE": "1"},
    ) as sandbox:
        computation = sandbox.run_code(
            "x * y + 1",
            inputs={"x": 5, "y": 3},
        )

        check_raised = False
        try:
            sandbox.run_code("1 / 0", check=True)
        except SandboxExecError:
            check_raised = True

        with sandbox.code_interpreter() as interpreter:
            interpreter.run("counter = 0")
            interpreter.run("counter = counter + 1")
            interpreter_result = interpreter.run("counter")

        snapshot_payload = sandbox.snapshot()

        filesystem_unsupported = False
        try:
            sandbox.write_file("/tmp/monty_phase7.txt", "phase7")
        except NotImplementedError:
            filesystem_unsupported = True

    summary = {
        "computation_output": computation.output,
        "check_raised": check_raised,
        "has_filesystem_capability": context.sandbox.has_capability(
            SandboxCapability.FILESYSTEM
        ),
        "interpreter_output": interpreter_result.output,
        "snapshot_available": bool(snapshot_payload),
        "filesystem_unsupported": filesystem_unsupported,
    }
    return json.dumps(summary, sort_keys=True)


@pipeline
def monty_sandbox_smoke_pipeline() -> None:
    """Pipeline wrapping the Monty sandbox smoke step."""
    monty_sandbox_smoke_step()


def _validate_stack() -> None:
    """Validates preconditions before running the smoke pipeline."""
    stack = Client().active_stack
    if stack.sandbox is None:
        raise RuntimeError(
            "The active stack does not include a sandbox component.\n"
            "Register and activate a stack with these commands:\n"
            f"{_registration_commands()}"
        )

    if stack.sandbox.flavor != "monty":
        raise RuntimeError(
            "The active stack sandbox flavor is not `monty`.\n"
            "Switch to a Monty-backed stack with these commands:\n"
            f"{_registration_commands()}"
        )


if __name__ == "__main__":
    _validate_stack()
    print("Running Monty sandbox smoke pipeline...")
    run = monty_sandbox_smoke_pipeline()
    run_id = getattr(run, "id", None)
    print(f"Pipeline finished. Run ID: {run_id}")
    print(
        "Inspect step metadata for `sandbox_info` in the dashboard or with the "
        "ZenML client to verify session metadata emission for provider 'monty'."
    )
