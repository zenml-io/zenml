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
"""Manual smoke test for the Phase 5 Modal sandbox implementation."""

import json
from typing import Iterator, List

__test__ = False

from zenml import pipeline, step
from zenml.client import Client
from zenml.sandboxes import SandboxExecError
from zenml.steps import get_step_context


def _registration_commands() -> str:
    """Returns sandbox and stack registration commands for this smoke test."""
    return "\n".join(
        [
            "zenml integration install modal",
            "zenml sandbox register modal-sb --flavor modal",
            (
                "zenml stack register modal-sandbox-stack "
                "-o default -a default --sandbox modal-sb"
            ),
            "zenml stack set modal-sandbox-stack",
            (
                "zenml sandbox update modal-sb "
                "--cpu_cost_per_core_second_usd 0.00001 "
                "--memory_cost_per_gib_second_usd 0.000001"
            ),
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


@step(sandbox=True)
def modal_sandbox_smoke_step() -> str:
    """Executes a sandbox smoke test inside a sandbox-enabled step."""
    context = get_step_context()
    if context.sandbox is None:
        raise RuntimeError(
            "No sandbox component is active in the current stack."
        )

    with context.sandbox.session(
        image="python:3.11-slim",
        timeout_seconds=600,
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

        sandbox.write_file("/tmp/phase5.txt", "phase5-smoke")
        file_contents = sandbox.read_file("/tmp/phase5.txt").decode("utf-8")

        interpreter_mode = "persistent"
        try:
            with sandbox.code_interpreter() as interpreter:
                first = interpreter.run(
                    "counter = globals().get('counter', 0) + 1\noutput = counter"
                )
                second = interpreter.run("counter += 1\noutput = counter")
            first_output = first.output
            second_output = second.output
        except RuntimeError as e:
            if "direct command router connection" not in str(e):
                raise
            interpreter_mode = "run_code_fallback"
            first_fallback = sandbox.run_code("print(1)")
            second_fallback = sandbox.run_code("print(2)")
            first_output = first_fallback.stdout.strip()
            second_output = second_fallback.stdout.strip()

    summary = {
        "hello_stdout": hello_result.stdout.strip(),
        "check_raised": check_raised,
        "streaming_exit_code": streaming_exit_code,
        "streamed_stdout": streamed_stdout,
        "streamed_stderr": streamed_stderr,
        "file_contents": file_contents,
        "interpreter_mode": interpreter_mode,
        "interpreter_first_output": first_output,
        "interpreter_second_output": second_output,
    }
    return json.dumps(summary, sort_keys=True)


@pipeline(enable_cache=False)
def modal_sandbox_smoke_pipeline() -> None:
    """Pipeline wrapping the Modal sandbox smoke step."""
    modal_sandbox_smoke_step()


def _validate_stack() -> None:
    """Validates preconditions before running the smoke pipeline."""
    stack = Client().active_stack
    if stack.sandbox is None:
        raise RuntimeError(
            "The active stack does not include a sandbox component.\n"
            "Register and activate a stack with these commands:\n"
            f"{_registration_commands()}"
        )


if __name__ == "__main__":
    _validate_stack()
    print("Running Modal sandbox smoke pipeline...")
    run = modal_sandbox_smoke_pipeline()
    run_id = getattr(run, "id", None)
    print(f"Pipeline finished. Run ID: {run_id}")
    print(
        "Inspect step metadata for `sandbox_info` in the dashboard or with the "
        "ZenML client to verify session metadata emission and cost estimates."
    )
