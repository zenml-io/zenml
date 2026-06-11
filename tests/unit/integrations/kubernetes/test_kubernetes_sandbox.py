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
"""Tests for the Kubernetes sandbox."""

import queue
from typing import List, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from kubernetes import client as k8s_client

from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.sandboxes import kubernetes_sandbox
from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
    KubernetesSandbox,
    KubernetesSandboxProcess,
    KubernetesSandboxSession,
)


def _build_script(
    command,
    cwd: Optional[str] = None,
    env=None,
) -> str:
    shell_command = KubernetesSandboxSession._build_shell_command(
        command, cwd, env
    )
    assert shell_command[:2] == ["/bin/sh", "-c"]
    return shell_command[2]


def test_build_shell_command_quotes_list_commands() -> None:
    """Test that list commands are quoted argv-style."""
    assert _build_script(["echo", "hello world"]) == "echo 'hello world'"


def test_build_shell_command_passes_string_commands_through() -> None:
    """Test that string commands are passed through unmodified."""
    assert _build_script("echo $HOME && ls") == "echo $HOME && ls"


def test_build_shell_command_cwd_uses_brace_group() -> None:
    """Test that the cwd guard wraps the whole command in a brace group."""
    assert _build_script("ls", cwd="/tmp") == "cd /tmp && { ls\n}"


def test_build_shell_command_cwd_guard_covers_raw_separators() -> None:
    """Test that raw `;` commands stay inside the cwd guard."""
    assert _build_script("a; b", cwd="/work") == "cd /work && { a; b\n}"


def test_build_shell_command_cwd_guard_survives_trailing_comment() -> None:
    """Test that a trailing comment does not swallow the group close."""
    assert (
        _build_script("ls # comment", cwd="/tmp")
        == "cd /tmp && { ls # comment\n}"
    )


def test_build_shell_command_prefixes_env_exports() -> None:
    """Test that env vars are prepended as export statements."""
    assert (
        _build_script("env", env={"FOO": "bar baz"})
        == "export FOO='bar baz'; env"
    )


def test_build_shell_command_env_inside_cwd_guard() -> None:
    """Test that env exports are placed inside the cwd guard."""
    assert (
        _build_script("env", cwd="/tmp", env={"FOO": "bar baz"})
        == "cd /tmp && { export FOO='bar baz'; env\n}"
    )


def test_build_shell_command_rejects_invalid_env_keys() -> None:
    """Test that non-identifier env keys raise instead of being injected."""
    with pytest.raises(ValueError, match="Invalid environment variable"):
        _build_script("x", env={"A; whoami #": "v"})


def test_split_lines_with_buffer_keeps_trailing_partial_line() -> None:
    """Test that incomplete trailing lines are kept in the buffer."""
    lines, buffer = kubernetes_sandbox._split_lines_with_buffer(
        chunk="a\nb\nc", buffer=""
    )
    assert lines == ["a\n", "b\n"]
    assert buffer == "c"

    lines, buffer = kubernetes_sandbox._split_lines_with_buffer(
        chunk="d\n", buffer=buffer
    )
    assert lines == ["cd\n"]
    assert buffer == ""


class _ClosedWSClient:
    """Websocket client stub that is already closed."""

    returncode = 0

    def is_open(self) -> bool:
        return False


def test_enqueue_line_drops_oldest_past_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the stream queues drop the oldest lines past the cap."""
    monkeypatch.setattr(kubernetes_sandbox, "_STREAM_BUFFER_MAX_LINES", 3)
    process = KubernetesSandboxProcess(
        session=MagicMock(),
        websocket_client=_ClosedWSClient(),  # type: ignore[arg-type]
        started_at=0.0,
    )

    q: "queue.Queue[object]" = queue.Queue()
    for i in range(5):
        process._enqueue_line(q, f"line-{i}\n")

    assert [q.get_nowait() for _ in range(q.qsize())] == [
        "line-2\n",
        "line-3\n",
        "line-4\n",
    ]


def _session_pod(
    session_id: str,
    component_id: str,
    phase: str = "Running",
) -> k8s_client.V1Pod:
    return k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(
            name=f"zenml-sandbox-{session_id}",
            labels={
                "zenml-sandbox-id": kube_utils.sanitize_label_value(
                    session_id
                ),
                "zenml-sandbox-component-id": (
                    kube_utils.sanitize_label_value(component_id)
                ),
            },
        ),
        status=k8s_client.V1PodStatus(phase=phase),
    )


def _make_sandbox(pods: List[k8s_client.V1Pod]) -> MagicMock:
    sandbox = MagicMock()
    sandbox.id = uuid4()
    sandbox.config.kubernetes_namespace = "zenml"
    sandbox.config.api_request_timeout = None
    sandbox.core_api.list_namespaced_pod.return_value = k8s_client.V1PodList(
        items=pods
    )
    return sandbox


def test_attach_returns_session_for_running_pod() -> None:
    """Test that attach returns a session handle for a running pod."""
    sandbox = _make_sandbox([])
    sandbox.core_api.list_namespaced_pod.return_value = k8s_client.V1PodList(
        items=[_session_pod("k8s-abc", str(sandbox.id))]
    )

    session = KubernetesSandbox.attach(sandbox, "k8s-abc")

    assert isinstance(session, KubernetesSandboxSession)
    assert session.id == "k8s-abc"
    assert session._pod_name == "zenml-sandbox-k8s-abc"
    assert session._namespace == "zenml"


def test_attach_fails_without_pod() -> None:
    """Test that attach fails when no pod exists for the session."""
    sandbox = _make_sandbox([])

    with pytest.raises(RuntimeError, match="No sandbox pod found"):
        KubernetesSandbox.attach(sandbox, "k8s-abc")


def test_attach_fails_for_other_component() -> None:
    """Test that attach rejects pods of a different sandbox component."""
    sandbox = _make_sandbox([_session_pod("k8s-abc", str(uuid4()))])

    with pytest.raises(RuntimeError, match="different sandbox component"):
        KubernetesSandbox.attach(sandbox, "k8s-abc")


def test_attach_fails_for_non_running_pod() -> None:
    """Test that attach rejects pods that are not running."""
    sandbox = _make_sandbox([])
    sandbox.core_api.list_namespaced_pod.return_value = k8s_client.V1PodList(
        items=[_session_pod("k8s-abc", str(sandbox.id), phase="Pending")]
    )

    with pytest.raises(RuntimeError, match="is not running"):
        KubernetesSandbox.attach(sandbox, "k8s-abc")
