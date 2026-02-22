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
"""Manual smoke test for the Phase 6 Daytona sandbox implementation."""

import json
from typing import Iterator, List

__test__ = False

from zenml import pipeline, step
from zenml.client import Client
from zenml.integrations.daytona.flavors import DaytonaSandboxSettings
from zenml.sandboxes import SandboxExecError
from zenml.steps import get_step_context


def _registration_commands() -> str:
    """Returns sandbox and stack registration commands for this smoke test."""
    return "\n".join(
        [
            "zenml integration install daytona",
            "zenml sandbox register daytona-sb --flavor daytona",
            (
                "zenml stack register daytona-sandbox-stack "
                "-o default -a default --sandbox daytona-sb"
            ),
            "zenml stack set daytona-sandbox-stack",
        ]
    )


def _collect_stream_lines(
    iterator: Iterator[str], expected_lines: int
) -> List[str]:
    """Collects a bounded number of streamed lines without waiting for EOF."""
    lines: List[str] = []
    for _ in range(expected_lines):
        try:
            lines.append(next(iterator).rstrip())
        except StopIteration:
            break
    return lines


@step(
    sandbox=True,
    settings={
        "sandbox.daytona": DaytonaSandboxSettings(
            ephemeral=True,
            auto_stop_interval_minutes=20,
        )
    },
)
def daytona_sandbox_smoke_step() -> str:
    """Executes a sandbox smoke test inside a sandbox-enabled step."""
    context = get_step_context()
    if context.sandbox is None:
        raise RuntimeError(
            "No sandbox component is active in the current stack."
        )

    with context.sandbox.session(
        image="python:3.12",
        timeout_seconds=600,
        env={"ZENML_SANDBOX_SMOKE": "1"},
    ) as sandbox:
        hello_result = sandbox.exec_run(
            ["python", "-c", "print('hello from daytona sandbox')"]
        )

        check_raised = False
        try:
            sandbox.exec_run(
                ["python", "-c", "import sys; sys.exit(3)"],
                check=True,
            )
        except SandboxExecError:
            check_raised = True

        process = sandbox.exec_streaming(
            [
                "python",
                "-u",
                "-c",
                (
                    "import sys; "
                    "print('stream stdout line 1'); "
                    "print('stream stderr line 1', file=sys.stderr); "
                    "print('stream stdout line 2'); "
                    "print('stream stderr line 2', file=sys.stderr)"
                ),
            ]
        )
        streamed_stdout = _collect_stream_lines(
            iter(process.stdout_iter()), expected_lines=2
        )
        streamed_stderr = _collect_stream_lines(
            iter(process.stderr_iter()), expected_lines=2
        )
        streaming_exit_code = process.wait(timeout_seconds=30)

        sandbox.write_file("/tmp/phase6.txt", "phase6-smoke")
        file_contents = sandbox.read_file("/tmp/phase6.txt").decode("utf-8")

        with sandbox.code_interpreter() as interpreter:
            first = interpreter.run(
                "counter = globals().get('counter', 0) + 1\nprint(counter)"
            )
            second = interpreter.run("counter += 1\nprint(counter)")
        first_output = (
            first.output if first.output is not None else first.stdout.strip()
        )
        second_output = (
            second.output
            if second.output is not None
            else second.stdout.strip()
        )

    summary = {
        "hello_stdout": hello_result.stdout.strip(),
        "check_raised": check_raised,
        "streaming_exit_code": streaming_exit_code,
        "streamed_stdout": streamed_stdout,
        "streamed_stderr": streamed_stderr,
        "file_contents": file_contents,
        "interpreter_first_output": first_output,
        "interpreter_second_output": second_output,
    }
    return json.dumps(summary, sort_keys=True)


@pipeline
def daytona_sandbox_smoke_pipeline() -> None:
    """Pipeline wrapping the Daytona sandbox smoke step."""
    daytona_sandbox_smoke_step()


def _validate_stack() -> None:
    """Validates preconditions before running the smoke pipeline."""
    stack = Client().active_stack
    if stack.sandbox is None:
        raise RuntimeError(
            "The active stack does not include a sandbox component.\n"
            "Register and activate a stack with these commands:\n"
            f"{_registration_commands()}"
        )

    if getattr(stack.sandbox, "flavor", None) != "daytona":
        raise RuntimeError(
            "The active stack sandbox flavor is not 'daytona'.\n"
            "Set a Daytona sandbox stack with:\n"
            f"{_registration_commands()}"
        )


if __name__ == "__main__":
    _validate_stack()
    print("Running Daytona sandbox smoke pipeline...")
    run = daytona_sandbox_smoke_pipeline()
    run_id = getattr(run, "id", None)
    print(f"Pipeline finished. Run ID: {run_id}")
    print(
        "Inspect step metadata for `sandbox_info` in the dashboard or with the "
        "ZenML client to verify provider metadata emission."
    )
