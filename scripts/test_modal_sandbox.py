#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Manual smoke test for the Phase 3 Modal sandbox implementation."""

import json

from zenml import pipeline, step
from zenml.client import Client
from zenml.sandboxes import SandboxExecError
from zenml.steps import get_step_context


@step(sandbox=True)
def modal_sandbox_smoke_step() -> str:
    """Executes a basic sandbox smoke test inside a sandbox-enabled step."""
    context = get_step_context()
    if context.sandbox is None:
        raise RuntimeError(
            "No sandbox component is active in the current stack."
        )

    with context.sandbox.session(
        image="python:3.11-slim",
        timeout_seconds=120,
        env={"ZENML_SANDBOX_SMOKE": "1"},
    ) as sandbox:
        hello_result = sandbox.exec_run(
            ["python", "-c", "print('hello from modal sandbox')"]
        )

        check_raised = False
        try:
            sandbox.exec_run(
                ["python", "-c", "import sys; sys.exit(3)"],
                check=True,
            )
        except SandboxExecError:
            check_raised = True

        sandbox.write_file("/tmp/phase3.txt", "phase3-smoke")
        file_contents = sandbox.read_file("/tmp/phase3.txt").decode("utf-8")

        with sandbox.code_interpreter() as interpreter:
            first = interpreter.run(
                "counter = globals().get('counter', 0) + 1\noutput = counter"
            )
            second = interpreter.run("counter += 1\noutput = counter")

    summary = {
        "hello_stdout": hello_result.stdout.strip(),
        "check_raised": check_raised,
        "file_contents": file_contents,
        "interpreter_first_output": first.output,
        "interpreter_second_output": second.output,
    }
    return json.dumps(summary, sort_keys=True)


@pipeline
def modal_sandbox_smoke_pipeline() -> None:
    """Pipeline wrapping the Modal sandbox smoke step."""
    modal_sandbox_smoke_step()


def _validate_stack() -> None:
    """Validates preconditions before running the smoke pipeline."""
    stack = Client().active_stack
    if stack.sandbox is None:
        raise RuntimeError(
            "The active stack does not include a sandbox component."
        )


if __name__ == "__main__":
    _validate_stack()
    print("Running Modal sandbox smoke pipeline...")
    run = modal_sandbox_smoke_pipeline()
    run_id = getattr(run, "id", None)
    print(f"Pipeline finished. Run ID: {run_id}")
    print(
        "Inspect step metadata for `sandbox_info` in the dashboard or with the "
        "ZenML client to verify session metadata emission."
    )
