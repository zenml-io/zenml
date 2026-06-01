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
from typing import Any, Iterator, Optional
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


def _make_sandbox(
    template_name: Optional[str] = "python-sandbox",
    **config_overrides: Any,
) -> K8sAgentSandbox:
    cfg = K8sAgentSandboxConfig(
        template_name=template_name,
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
        # ``base_image`` is declared locally on the flavor (base no
        # longer ships it); ``environment`` comes from
        # ``BaseSandboxSettings``.
        assert {"base_image", "environment"} <= set(fields)

    def test_default_connection_mode_is_gateway(self) -> None:
        cfg = K8sAgentSandboxConfig()
        assert cfg.connection_mode == ConnectionMode.GATEWAY

    def test_is_remote_true(self) -> None:
        cfg = K8sAgentSandboxConfig()
        assert cfg.is_remote is True

    def test_template_name_optional(self) -> None:
        cfg = K8sAgentSandboxConfig()
        assert cfg.template_name is None


class TestRequirementsAreInherited:
    def test_kubernetes_pin_inherited_from_kubernetes_integration(
        self,
    ) -> None:
        from zenml.integrations.k8s_agent_sandbox import (
            K8sAgentSandboxIntegration,
        )
        from zenml.integrations.kubernetes import KubernetesIntegration

        # Confirm we pick up the same kubernetes-client pin as the
        # sibling integration — drift would mean the pod-spec helpers
        # we reuse target a different SDK version.
        k_pins = [
            r for r in KubernetesIntegration.REQUIREMENTS if "kubernetes" in r
        ]
        for pin in k_pins:
            assert pin in K8sAgentSandboxIntegration.REQUIREMENTS


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
            cfg = sb._build_connection_config()
        assert type(cfg).__name__ == "MagicMock"  # mock class instance
        assert getattr(_models, expected_cls).called

    def test_direct_mode_requires_api_url(self) -> None:
        sb = _make_sandbox(connection_mode=ConnectionMode.DIRECT)
        with pytest.raises(ValueError, match="api_url"):
            sb._build_connection_config()

    def test_direct_mode_with_api_url_succeeds(self) -> None:
        sb = _make_sandbox(
            connection_mode=ConnectionMode.DIRECT,
            api_url="http://sb.example.com",
        )
        sb._build_connection_config()
        _models.SandboxDirectConnectionConfig.assert_called_with(
            api_url="http://sb.example.com"
        )


def _wire_client(sb: K8sAgentSandbox) -> MagicMock:
    """Wires a mock ``SandboxClient`` via the ``_build_client`` hook.

    Returns the underlying fake client so tests can assert on its calls.
    """
    fake_client = MagicMock()
    fake_sandbox = MagicMock(name="sb1")
    fake_sandbox.name = "sb1"
    fake_client.create_sandbox.return_value = fake_sandbox
    sb._build_client = MagicMock(return_value=fake_client)  # type: ignore[method-assign]
    return fake_client


class TestCreateSession:
    def test_passes_template_and_namespace_to_sdk(self) -> None:
        sb = _make_sandbox(namespace="prod")
        fake_client = _wire_client(sb)

        session = sb.create_session()
        assert isinstance(session, K8sAgentSandboxSession)
        fake_client.create_sandbox.assert_called_once_with(
            template="python-sandbox",
            namespace="prod",
            sandbox_ready_timeout=180,
        )

    def test_per_call_namespace_overrides_default(self) -> None:
        sb = _make_sandbox(namespace="prod")
        fake_client = _wire_client(sb)

        sb.create_session(
            settings=K8sAgentSandboxSettings(
                template_name="python-sandbox",
                namespace="experiments",
            )
        )
        kwargs = fake_client.create_sandbox.call_args.kwargs
        assert kwargs["namespace"] == "experiments"

    def test_synthesizes_inline_template_when_template_name_unset(
        self,
    ) -> None:
        sb = _make_sandbox(
            template_name=None,
            namespace="lab",
            default_image="runtime:1.0",
        )
        fake_client = _wire_client(sb)

        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api_cls.return_value = fake_api
            session = sb.create_session()

        fake_api.create_namespaced_custom_object.assert_called_once()
        call_kwargs = fake_api.create_namespaced_custom_object.call_args.kwargs
        assert call_kwargs["group"] == "extensions.agents.x-k8s.io"
        assert call_kwargs["version"] == "v1beta1"
        assert call_kwargs["plural"] == "sandboxtemplates"
        assert call_kwargs["namespace"] == "lab"
        body = call_kwargs["body"]
        assert body["kind"] == "SandboxTemplate"
        # Full 32-char UUID hex (no collision risk at fanout scale).
        assert body["metadata"]["name"].startswith("zenml-sb-tpl-")
        assert len(body["metadata"]["name"]) == len("zenml-sb-tpl-") + 32
        # Upstream-matching container shape.
        container = body["spec"]["podTemplate"]["spec"]["containers"][0]
        assert container["name"] == "python-runtime"
        assert container["image"] == "runtime:1.0"
        assert container["ports"][0]["containerPort"] == 8888
        assert container["readinessProbe"]["httpGet"]["port"] == 8888
        assert container["livenessProbe"]["httpGet"]["port"] == 8888
        # SDK got the synthesized name.
        sdk_kwargs = fake_client.create_sandbox.call_args.kwargs
        assert sdk_kwargs["template"] == body["metadata"]["name"]
        # Session tracks the inline template for cleanup.
        assert session._inline_template_name == body["metadata"]["name"]
        assert session._inline_template_namespace == "lab"

    def test_inline_template_cleanup_disabled_skips_tracking(self) -> None:
        sb = _make_sandbox(
            template_name=None,
            namespace="lab",
            default_image="runtime:1.0",
            inline_template_cleanup=False,
        )
        _wire_client(sb)

        with patch("kubernetes.client.CustomObjectsApi"):
            session = sb.create_session()
        assert session._inline_template_name is None
        assert session._inline_template_namespace is None

    def test_inline_template_requires_image(self) -> None:
        # Reproducibility-first: no default_image, no base_image → refuse.
        sb = _make_sandbox(template_name=None, namespace="lab")
        _wire_client(sb)
        with (
            patch("kubernetes.client.CustomObjectsApi"),
            pytest.raises(ValueError, match="requires an image"),
        ):
            sb.create_session()

    def test_orphan_template_cleaned_up_on_create_sandbox_failure(
        self,
    ) -> None:
        sb = _make_sandbox(
            template_name=None,
            namespace="lab",
            default_image="runtime:1.0",
        )
        fake_client = _wire_client(sb)
        fake_client.create_sandbox.side_effect = RuntimeError("denied")

        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api_cls.return_value = fake_api
            with pytest.raises(RuntimeError, match="denied"):
                sb.create_session()
        # CR created AND deleted in the failure cleanup path.
        fake_api.create_namespaced_custom_object.assert_called_once()
        fake_api.delete_namespaced_custom_object.assert_called_once()

    def test_orphan_cleanup_runs_even_when_cleanup_disabled(self) -> None:
        # `inline_template_cleanup=False` governs successful teardown;
        # orphan cleanup on create-sandbox failure must still happen.
        sb = _make_sandbox(
            template_name=None,
            namespace="lab",
            default_image="runtime:1.0",
            inline_template_cleanup=False,
        )
        fake_client = _wire_client(sb)
        fake_client.create_sandbox.side_effect = RuntimeError("denied")

        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api_cls.return_value = fake_api
            with pytest.raises(RuntimeError, match="denied"):
                sb.create_session()
        fake_api.delete_namespaced_custom_object.assert_called_once()

    def test_404_crd_missing_hint(self) -> None:
        from kubernetes.client.rest import ApiException

        sb = _make_sandbox(
            template_name=None,
            namespace="lab",
            default_image="runtime:1.0",
        )
        _wire_client(sb)

        api_exc = ApiException(status=404, reason="Not Found")
        api_exc.body = (
            '{"kind":"Status","status":"Failure",'
            '"reason":"NotFound","message":"the server could not find '
            'the requested resource"}'
        )
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api.create_namespaced_custom_object.side_effect = api_exc
            fake_api_cls.return_value = fake_api
            with pytest.raises(RuntimeError, match="CRDs aren't installed"):
                sb.create_session()

    def test_404_namespace_missing_hint(self) -> None:
        # If the 404 body mentions the namespace, surface the
        # namespace-missing remediation instead of the CRD hint.
        from kubernetes.client.rest import ApiException

        sb = _make_sandbox(
            template_name=None,
            namespace="missing-ns",
            default_image="runtime:1.0",
        )
        _wire_client(sb)

        api_exc = ApiException(status=404, reason="Not Found")
        api_exc.body = '{"message":"namespaces \\"missing-ns\\" not found"}'
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api.create_namespaced_custom_object.side_effect = api_exc
            fake_api_cls.return_value = fake_api
            with pytest.raises(RuntimeError, match="does not exist"):
                sb.create_session()


class TestInlineTemplateBody:
    def test_default_resources_include_ephemeral_storage(self) -> None:
        # Even without StepContext, the upstream-matching default
        # ephemeral-storage request is set so the pod can be scheduled.
        sb = _make_sandbox(template_name=None, default_image="r:1")
        body = sb._build_inline_template_body(
            K8sAgentSandboxSettings(), "ns", "zenml-sb-tpl-test"
        )
        container = body["spec"]["podTemplate"]["spec"]["containers"][0]
        assert container["resources"]["requests"]["ephemeral-storage"] == (
            "512Mi"
        )

    def test_container_name_matches_upstream(self) -> None:
        sb = _make_sandbox(template_name=None, default_image="r:1")
        body = sb._build_inline_template_body(
            K8sAgentSandboxSettings(), "ns", "zenml-sb-tpl-test"
        )
        container = body["spec"]["podTemplate"]["spec"]["containers"][0]
        # Operator examples use `python-runtime` — keep parity.
        assert container["name"] == "python-runtime"

    def test_includes_liveness_probe(self) -> None:
        sb = _make_sandbox(template_name=None, default_image="r:1")
        body = sb._build_inline_template_body(
            K8sAgentSandboxSettings(), "ns", "zenml-sb-tpl-test"
        )
        container = body["spec"]["podTemplate"]["spec"]["containers"][0]
        assert container["livenessProbe"]["httpGet"]["port"] == 8888

    def test_refuses_without_any_image(self) -> None:
        # default_image=None on config, no base_image in settings.
        sb = _make_sandbox(template_name=None)
        with pytest.raises(ValueError, match="requires an image"):
            sb._build_inline_template_body(
                K8sAgentSandboxSettings(), "ns", "zenml-sb-tpl-test"
            )

    def test_image_override_via_settings(self) -> None:
        sb = _make_sandbox(default_image="default:1")
        body = sb._build_inline_template_body(
            K8sAgentSandboxSettings(base_image="my-org/custom:1"),
            "ns",
            "zenml-sb-tpl-test",
        )
        container = body["spec"]["podTemplate"]["spec"]["containers"][0]
        assert container["image"] == "my-org/custom:1"

    def test_resource_requests_via_k8s_helper(self) -> None:
        # Confirms we reuse `convert_resource_settings_to_k8s_format`:
        # cpu_count=0.5 must become "500m", not "0.5" — the helper's
        # millicore handling is the integration value-add.
        from zenml.config.resource_settings import ResourceSettings

        sb = _make_sandbox(default_image="r:1")
        fake_ctx = MagicMock()
        fake_ctx.step_run.config.resource_settings = ResourceSettings(
            cpu_count=0.5, memory="512MiB"
        )
        with patch(
            "zenml.steps.step_context.StepContext.get",
            return_value=fake_ctx,
        ):
            body = sb._build_inline_template_body(
                K8sAgentSandboxSettings(), "ns", "zenml-sb-tpl-test"
            )
        requests = body["spec"]["podTemplate"]["spec"]["containers"][0][
            "resources"
        ]["requests"]
        assert requests["cpu"] == "500m"
        assert requests["memory"].endswith("Mi")

    def test_gpu_count_routed_to_nvidia_resource(self) -> None:
        # The k8s helper mirrors GPUs to both requests and limits.
        from zenml.config.resource_settings import ResourceSettings

        sb = _make_sandbox(default_image="r:1")
        fake_ctx = MagicMock()
        fake_ctx.step_run.config.resource_settings = ResourceSettings(
            gpu_count=1
        )
        with patch(
            "zenml.steps.step_context.StepContext.get",
            return_value=fake_ctx,
        ):
            body = sb._build_inline_template_body(
                K8sAgentSandboxSettings(), "ns", "zenml-sb-tpl-test"
            )
        res = body["spec"]["podTemplate"]["spec"]["containers"][0]["resources"]
        assert res["requests"]["nvidia.com/gpu"] == "1"
        assert res["limits"]["nvidia.com/gpu"] == "1"

    def test_pod_settings_applied_via_manifest_utils(self) -> None:
        # `add_pod_settings` should plumb node_selectors / tolerations
        # / affinity through. We verify by setting node_selectors and
        # checking it lands in the serialized dict.
        from zenml.integrations.kubernetes.pod_settings import (
            KubernetesPodSettings,
        )

        sb = _make_sandbox(default_image="r:1")
        body = sb._build_inline_template_body(
            K8sAgentSandboxSettings(
                pod_settings=KubernetesPodSettings(
                    node_selectors={"node-pool": "sandbox"}
                )
            ),
            "ns",
            "zenml-sb-tpl-test",
        )
        pod_spec = body["spec"]["podTemplate"]["spec"]
        assert pod_spec["nodeSelector"] == {"node-pool": "sandbox"}


class TestSessionLifecycle:
    def _session_with_inline(
        self,
    ) -> Any:
        sb = _make_sandbox()
        fake_underlying = MagicMock()
        fake_underlying.name = "sb1"
        return (
            K8sAgentSandboxSession(
                fake_underlying,
                parent=sb,
                inline_template_name="zenml-sb-tpl-deadbeef",
                inline_template_namespace="lab",
            ),
            fake_underlying,
        )

    def test_close_does_not_terminate_sandbox(self) -> None:
        # Per the base contract, close() releases the local handle but
        # leaves the sandbox running. destroy() is the termination path.
        session, fake_underlying = self._session_with_inline()
        with patch("kubernetes.client.CustomObjectsApi"):
            session.close()
        fake_underlying.terminate.assert_not_called()

    def test_close_deletes_inline_template(self) -> None:
        session, _ = self._session_with_inline()
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api_cls.return_value = fake_api
            session.close()
        fake_api.delete_namespaced_custom_object.assert_called_once_with(
            group="extensions.agents.x-k8s.io",
            version="v1beta1",
            namespace="lab",
            plural="sandboxtemplates",
            name="zenml-sb-tpl-deadbeef",
        )

    def test_close_flushes_log_ctx(self) -> None:
        # The base contract requires _close_log_ctx() so the per-session
        # log source is flushed to the log store.
        session, _ = self._session_with_inline()
        with (
            patch("kubernetes.client.CustomObjectsApi"),
            patch.object(session, "_close_log_ctx") as fake_close_log,
        ):
            session.close()
        fake_close_log.assert_called_once()

    def test_destroy_terminates_and_deletes_template(self) -> None:
        session, fake_underlying = self._session_with_inline()
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api_cls.return_value = fake_api
            session.destroy()
        fake_underlying.terminate.assert_called_once()
        fake_api.delete_namespaced_custom_object.assert_called_once()

    def test_destroy_tolerates_terminate_failure(self) -> None:
        session, fake_underlying = self._session_with_inline()
        fake_underlying.terminate.side_effect = RuntimeError("network gone")
        with patch("kubernetes.client.CustomObjectsApi"):
            session.destroy()  # should not raise

    def test_double_cleanup_is_idempotent(self) -> None:
        # close() then destroy() (or vice versa) should not double-delete
        # the inline template CR.
        session, _ = self._session_with_inline()
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api_cls.return_value = fake_api
            session.close()
            session.destroy()
        assert fake_api.delete_namespaced_custom_object.call_count == 1

    def test_close_tolerates_delete_failure(self) -> None:
        session, _ = self._session_with_inline()
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            fake_api = MagicMock()
            fake_api.delete_namespaced_custom_object.side_effect = (
                RuntimeError("403 forbidden")
            )
            fake_api_cls.return_value = fake_api
            session.close()  # should not raise

    def test_close_skips_delete_when_no_inline_template(self) -> None:
        sb = _make_sandbox()
        fake_underlying = MagicMock()
        fake_underlying.name = "sb1"
        session = K8sAgentSandboxSession(fake_underlying, parent=sb)
        with patch("kubernetes.client.CustomObjectsApi") as fake_api_cls:
            session.close()
        fake_api_cls.assert_not_called()


class TestProcessSurface:
    def test_stdout_yields_line_by_line(self) -> None:
        # Honor the SandboxProcess line-iterator contract: each line is
        # one yield, trailing newline preserved.
        result = MagicMock(stdout="hello\nworld\n", stderr="", exit_code=0)
        proc = K8sAgentSandboxProcess(result, session=None)
        assert list(proc.stdout()) == ["hello\n", "world\n"]

    def test_stdout_handles_trailing_partial_line(self) -> None:
        result = MagicMock(
            stdout="line1\nline2-no-newline", stderr="", exit_code=0
        )
        proc = K8sAgentSandboxProcess(result, session=None)
        assert list(proc.stdout()) == ["line1\n", "line2-no-newline"]

    def test_stderr_empty_yields_no_chunks(self) -> None:
        result = MagicMock(stdout="ok\n", stderr="", exit_code=0)
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
