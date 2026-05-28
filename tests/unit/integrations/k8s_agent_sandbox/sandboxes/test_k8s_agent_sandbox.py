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
"""Unit tests for the Agent Sandbox flavor.

These tests mock the ``k8s_agent_sandbox`` SDK entry points and the
service-connector hook. They cover the wiring (settings resolution,
template / namespace plumbing, connection-config construction) without
needing a live cluster. End-to-end coverage against a real GKE / kind
cluster lands in a follow-up integration test.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Iterator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# --- Stub the SDK before the integration module is imported -----------

_sdk = types.ModuleType("k8s_agent_sandbox")
_sdk.SandboxClient = MagicMock()


class _Models(types.ModuleType):
    SandboxDirectConnectionConfig = MagicMock()
    SandboxGatewayConnectionConfig = MagicMock()
    SandboxInClusterConnectionConfig = MagicMock()
    SandboxLocalTunnelConnectionConfig = MagicMock()


_models = _Models("k8s_agent_sandbox.models")
_sdk.models = _models  # type: ignore[attr-defined]

_sandbox_mod = types.ModuleType("k8s_agent_sandbox.sandbox")
_sandbox_mod.Sandbox = MagicMock()

sys.modules.setdefault("k8s_agent_sandbox", _sdk)
sys.modules.setdefault("k8s_agent_sandbox.models", _models)
sys.modules.setdefault("k8s_agent_sandbox.sandbox", _sandbox_mod)

# --- Imports that depend on the SDK shim ------------------------------

from zenml.integrations.k8s_agent_sandbox.flavors import (  # noqa: E402
    ConnectionMode,
    K8sAgentSandboxConfig,
    K8sAgentSandboxFlavor,
    K8sAgentSandboxSettings,
)
from zenml.integrations.k8s_agent_sandbox.sandboxes.k8s_agent_sandbox import (  # noqa: E402
    K8sAgentSandbox,
    K8sAgentSandboxProcess,
    K8sAgentSandboxSession,
)


def _make_sandbox(**config_overrides: Any) -> K8sAgentSandbox:
    cfg = K8sAgentSandboxConfig(
        template_name="python-sandbox",
        **config_overrides,
    )
    return K8sAgentSandbox(
        name="test-sandbox",
        id=uuid4(),
        config=cfg,
        flavor="k8s_agent_sandbox",
        type="sandbox",
        user=uuid4(),
        created="2026-01-01T00:00:00",
        updated="2026-01-01T00:00:00",
    )


class TestFlavorMetadata:
    def test_name_is_k8s_agent_sandbox(self) -> None:
        assert K8sAgentSandboxFlavor().name == "k8s_agent_sandbox"

    def test_config_class(self) -> None:
        assert K8sAgentSandboxFlavor().config_class is K8sAgentSandboxConfig

    def test_service_connector_requirements_match_k8s_cluster(self) -> None:
        from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE

        req = K8sAgentSandboxFlavor().service_connector_requirements
        assert req is not None
        assert req.resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE


class TestConfigDefaults:
    def test_inherits_base_sandbox_fields(self) -> None:
        fields = K8sAgentSandboxSettings.model_fields
        assert {"base_image", "environment", "timeout_seconds"} <= set(fields)

    def test_default_connection_mode_is_gateway(self) -> None:
        cfg = K8sAgentSandboxConfig()
        assert cfg.connection_mode == ConnectionMode.GATEWAY

    def test_is_remote_true(self) -> None:
        cfg = K8sAgentSandboxConfig()
        assert cfg.is_remote is True

    def test_template_name_optional(self) -> None:
        cfg = K8sAgentSandboxConfig()
        assert cfg.template_name is None


class TestConnectionConfigBuild:
    @pytest.mark.parametrize(
        "mode,expected_cls",
        [
            (ConnectionMode.GATEWAY, "SandboxGatewayConnectionConfig"),
            (ConnectionMode.IN_CLUSTER, "SandboxInClusterConnectionConfig"),
            (
                ConnectionMode.LOCAL_TUNNEL,
                "SandboxLocalTunnelConnectionConfig",
            ),
        ],
    )
    def test_mode_routes_to_expected_config(
        self, mode: ConnectionMode, expected_cls: str
    ) -> None:
        sb = _make_sandbox(connection_mode=mode)
        # Smoke: the method picks the right SDK class. The SDK models
        # module is shimmed at import time (see top of file); we just
        # confirm the matching constructor is invoked.
        with patch.dict(
            "sys.modules",
            {"k8s_agent_sandbox.models": _models},
        ):
            cfg = sb._build_connection_config(K8sAgentSandboxSettings())
        assert type(cfg).__name__ == "MagicMock"  # mock class instance
        assert getattr(_models, expected_cls).called

    def test_direct_mode_requires_api_url(self) -> None:
        sb = _make_sandbox(connection_mode=ConnectionMode.DIRECT)
        with pytest.raises(ValueError, match="api_url"):
            sb._build_connection_config(K8sAgentSandboxSettings())

    def test_direct_mode_with_api_url_succeeds(self) -> None:
        sb = _make_sandbox(
            connection_mode=ConnectionMode.DIRECT,
            api_url="http://sb.example.com",
        )
        sb._build_connection_config(K8sAgentSandboxSettings())
        _models.SandboxDirectConnectionConfig.assert_called_with(
            api_url="http://sb.example.com"
        )


class TestCreateSession:
    def test_requires_template_name(self) -> None:
        sb = _make_sandbox()
        # template_name defaults to "python-sandbox" via _make_sandbox;
        # explicitly null it on the per-call override to reach the
        # not-implemented branch.
        with pytest.raises(ValueError, match="Inline template synthesis"):
            sb.create_session(
                settings=K8sAgentSandboxSettings(template_name="")
            )

    def test_passes_template_and_namespace_to_sdk(self) -> None:
        sb = _make_sandbox(default_namespace="prod")
        fake_client = MagicMock()
        fake_sandbox = MagicMock(name="sb1")
        fake_sandbox.name = "sb1"
        fake_client.create_sandbox.return_value = fake_sandbox
        sb._client = fake_client

        session = sb.create_session()
        assert isinstance(session, K8sAgentSandboxSession)
        fake_client.create_sandbox.assert_called_once_with(
            template="python-sandbox",
            namespace="prod",
            sandbox_ready_timeout=180,
        )

    def test_per_call_namespace_overrides_default(self) -> None:
        sb = _make_sandbox(default_namespace="prod")
        fake_client = MagicMock()
        fake_client.create_sandbox.return_value = MagicMock(name="sb1")
        fake_client.create_sandbox.return_value.name = "sb1"
        sb._client = fake_client

        sb.create_session(
            settings=K8sAgentSandboxSettings(
                template_name="python-sandbox", namespace="experiments"
            )
        )
        kwargs = fake_client.create_sandbox.call_args.kwargs
        assert kwargs["namespace"] == "experiments"


class TestProcessSurface:
    def test_stdout_yields_single_chunk(self) -> None:
        result = MagicMock(stdout="hello\nworld\n", stderr="", exit_code=0)
        proc = K8sAgentSandboxProcess(result, session=None)
        lines = list(proc.stdout())
        assert lines == ["hello\nworld\n"]

    def test_stderr_empty_yields_no_chunks(self) -> None:
        result = MagicMock(stdout="ok", stderr="", exit_code=0)
        proc = K8sAgentSandboxProcess(result, session=None)
        assert list(proc.stderr()) == []

    def test_wait_returns_captured_exit_code(self) -> None:
        result = MagicMock(stdout="", stderr="oops", exit_code=3)
        proc = K8sAgentSandboxProcess(result, session=None)
        assert proc.wait() == 3
        assert proc.exit_code == 3

    def test_kill_is_noop(self) -> None:
        proc = K8sAgentSandboxProcess(MagicMock(exit_code=0), session=None)
        proc.kill()  # no exception

    def test_session_log_wrapping_routes_through_wrap_stream(self) -> None:
        sentinel: Iterator[str] = iter(["wrapped"])
        fake_session = MagicMock()
        fake_session._wrap_stream.return_value = sentinel
        result = MagicMock(stdout="raw\n", stderr="", exit_code=0)
        proc = K8sAgentSandboxProcess(result, session=fake_session)
        out = list(proc.stdout())
        assert out == ["wrapped"]
        assert fake_session._wrap_stream.call_args.kwargs["stream"] == (
            "stdout"
        )


class TestExec:
    def _live_session(self, run_result: Any) -> K8sAgentSandboxSession:
        sb = _make_sandbox()
        fake_underlying = MagicMock()
        fake_underlying.name = "live-session"
        fake_underlying.commands.run.return_value = run_result
        return K8sAgentSandboxSession(fake_underlying, parent=sb)

    def test_string_command_passed_through(self) -> None:
        result = MagicMock(stdout="", stderr="", exit_code=0)
        session = self._live_session(result)
        session.exec("echo hi")
        # The SDK accepts a single shell-string command.
        session._sandbox.commands.run.assert_called_once_with("echo hi")

    def test_list_command_joined_with_shlex(self) -> None:
        result = MagicMock(stdout="", stderr="", exit_code=0)
        session = self._live_session(result)
        session.exec(["python", "-c", "print('hi')"])
        called_with = session._sandbox.commands.run.call_args.args[0]
        # shlex.join quotes the snippet that contains parens.
        assert "python -c " in called_with
        assert "print" in called_with

    def test_cwd_prefixed_as_cd(self) -> None:
        result = MagicMock(stdout="", stderr="", exit_code=0)
        session = self._live_session(result)
        session.exec("ls", cwd="/tmp")
        called_with = session._sandbox.commands.run.call_args.args[0]
        assert called_with.startswith("cd /tmp && ")

    def test_env_prefixed_as_inline_exports(self) -> None:
        result = MagicMock(stdout="", stderr="", exit_code=0)
        session = self._live_session(result)
        session.exec("env", env={"FOO": "bar baz"})
        called_with = session._sandbox.commands.run.call_args.args[0]
        # shlex.quote wraps "bar baz" in single quotes.
        assert "FOO='bar baz'" in called_with

    def test_exec_failure_wraps_in_sandbox_exec_error(self) -> None:
        from zenml.sandboxes import SandboxExecError

        session = self._live_session(MagicMock())
        session._sandbox.commands.run.side_effect = RuntimeError("boom")
        with pytest.raises(SandboxExecError, match="RuntimeError"):
            session.exec("/missing")


class TestClose:
    def test_close_terminates_underlying_sandbox(self) -> None:
        sb = _make_sandbox()
        fake_underlying = MagicMock()
        fake_underlying.name = "sb1"
        session = K8sAgentSandboxSession(fake_underlying, parent=sb)
        session.close()
        fake_underlying.terminate.assert_called_once()

    def test_close_tolerates_terminate_failure(self) -> None:
        sb = _make_sandbox()
        fake_underlying = MagicMock()
        fake_underlying.name = "sb1"
        fake_underlying.terminate.side_effect = RuntimeError("network gone")
        session = K8sAgentSandboxSession(fake_underlying, parent=sb)
        # Should not raise — close is idempotent / best-effort.
        session.close()
