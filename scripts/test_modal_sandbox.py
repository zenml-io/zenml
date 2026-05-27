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
"""End-to-end smoke test for the Modal Sandbox flavor.

Runs a small battery of operations against a *real* Modal account to verify
the flavor end-to-end. Not part of the unit-test suite (excluded from pytest
via the ``__test__`` flag).

Prerequisites:
    1. ``modal token new`` has been run (or ``MODAL_TOKEN_ID`` / ``MODAL_TOKEN_SECRET``
       are set in the environment).
    2. The active ZenML stack has a Modal sandbox component:
       ::

           zenml integration install modal
           zenml sandbox register modal-sb --flavor=modal
           zenml stack register modal-sandbox-stack -o default -a default --sandbox modal-sb
           zenml stack set modal-sandbox-stack

Run with::

    python scripts/test_modal_sandbox.py
"""

import os
import tempfile
from typing import Iterator, List

__test__ = False

from zenml.client import Client
from zenml.integrations.modal.flavors import ModalSandboxSettings


def _drain(stream: Iterator[str], limit: int = 50) -> List[str]:
    """Reads up to ``limit`` lines from a process stream.

    Args:
        stream: The line iterator.
        limit: Hard cap so a runaway process doesn't hang the smoke test.

    Returns:
        The collected lines (rstripped).
    """
    lines: List[str] = []
    for _ in range(limit):
        try:
            lines.append(next(stream).rstrip())
        except StopIteration:
            break
    return lines


def _exec_and_collect(session, argv: List[str]) -> tuple[List[str], int]:
    """Runs argv in the session and returns (stdout lines, exit code)."""
    process = session.exec(argv)
    stdout_lines = _drain(process.stdout())
    exit_code = process.wait()
    return stdout_lines, exit_code


def _check_basic_exec(sandbox) -> None:
    """Boots a Session, runs a hello-world command, asserts the output."""
    print("\n[1/5] Basic exec + stream")
    with sandbox.create_session(
        settings=ModalSandboxSettings(
            environment={"ZENML_SANDBOX_SMOKE": "1"},
            timeout_seconds=600,
        )
    ) as session:
        print(f"   Session id: {session.id}")
        out, code = _exec_and_collect(
            session,
            [
                "python",
                "-c",
                "print('hello from modal'); import os; print(os.environ['ZENML_SANDBOX_SMOKE'])",
            ],
        )
        print(f"   stdout: {out!r}")
        print(f"   exit:   {code}")
        assert code == 0, f"expected exit 0, got {code}"
        assert out == ["hello from modal", "1"], f"unexpected stdout: {out!r}"


def _check_exit_nonzero(sandbox) -> None:
    """Verifies a failing command surfaces a non-zero exit code (no exception)."""
    print("\n[2/5] Non-zero exit (no exception)")
    with sandbox.create_session() as session:
        process = session.exec(["python", "-c", "import sys; sys.exit(3)"])
        process.wait()
        print(f"   exit_code: {process.exit_code}")
        assert process.exit_code == 3


def _check_file_io(sandbox) -> None:
    """Round-trips a file upload + download."""
    print("\n[3/5] upload_file + download_file")
    with sandbox.create_session() as session:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False
        ) as src:
            src.write("hello\nfrom\nlocal\n")
            src_path = src.name
        try:
            session.upload_file(src_path, "/tmp/in.txt")
            out, code = _exec_and_collect(session, ["cat", "/tmp/in.txt"])
            assert code == 0
            assert out == ["hello", "from", "local"], out

            with tempfile.NamedTemporaryFile(
                "rb", suffix=".txt", delete=False
            ) as dst:
                dst_path = dst.name
            session.download_file("/tmp/in.txt", dst_path)
            with open(dst_path) as f:
                assert f.read() == "hello\nfrom\nlocal\n"
            print("   round-trip ok")
        finally:
            for p in (src_path, dst_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass


def _check_snapshot_restore(sandbox) -> None:
    """Writes a file, snapshots, restores into a fresh Session, reads it back."""
    print("\n[4/5] snapshot + restore (FS state preserved)")
    with sandbox.create_session() as original:
        out, code = _exec_and_collect(
            original,
            [
                "bash",
                "-c",
                "echo 'snapshot-payload' > /tmp/snap.txt && cat /tmp/snap.txt",
            ],
        )
        assert code == 0 and out == ["snapshot-payload"]
        snap = original.snapshot()
        print(f"   snapshot ref: {snap.ref}")

    with sandbox.restore(snap) as restored:
        out, code = _exec_and_collect(restored, ["cat", "/tmp/snap.txt"])
        assert code == 0 and out == ["snapshot-payload"], out
        print(f"   restored session id: {restored.id} (new id; FS preserved)")


def _check_attach(sandbox) -> None:
    """Verifies attach() reconnects to a still-live Session by id."""
    print("\n[5/5] attach (subagent reuse pattern)")
    original = sandbox.create_session()
    sess_id = original.id
    original.close()  # release handle; Modal sandbox still running

    reattached = sandbox.attach(sess_id)
    try:
        out, code = _exec_and_collect(
            reattached, ["python", "-c", "print('reattached')"]
        )
        assert code == 0 and out == ["reattached"], out
        print(f"   reattached to id={sess_id} successfully")
    finally:
        reattached.destroy()


def main() -> None:
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise SystemExit(
            "No sandbox component in the active stack. See the docstring "
            "in this file for setup instructions."
        )
    print(f"Smoke-testing Modal sandbox: {sandbox.name}")

    _check_basic_exec(sandbox)
    _check_exit_nonzero(sandbox)
    _check_file_io(sandbox)
    _check_snapshot_restore(sandbox)
    _check_attach(sandbox)
    print("\nAll Modal sandbox smoke checks passed.")


if __name__ == "__main__":
    main()
