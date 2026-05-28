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
"""Agent Sandbox flavor implementation.

Wraps the ``k8s-agent-sandbox`` Python SDK's ``SandboxClient`` /
``Sandbox`` primitives in the ``BaseSandbox`` interface. The SDK exposes
``sandbox.commands.run(cmd)`` as a single blocking call returning a full
``ExecutionResult`` — there is no server-side streaming endpoint in the
current operator. This implementation honours the SDK contract: each
``exec()`` issues one HTTP POST and surfaces the captured streams as
one-shot ``stdout()`` / ``stderr()`` iterators on
``K8sAgentSandboxProcess``. Real per-line streaming will land alongside the
snapshot/restore work once the operator exposes it.
"""

import shlex
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from zenml.config.base_settings import BaseSettings
from zenml.integrations.k8s_agent_sandbox.flavors import (
    ConnectionMode,
    K8sAgentSandboxConfig,
    K8sAgentSandboxSettings,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxSettings,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
)

if TYPE_CHECKING:
    from k8s_agent_sandbox import SandboxClient
    from k8s_agent_sandbox.sandbox import Sandbox

logger = get_logger(__name__)


class K8sAgentSandboxProcess(SandboxProcess):
    """Single-shot process wrapping an ``ExecutionResult``.

    The agent-sandbox SDK's ``commands.run`` is a blocking HTTP POST
    that returns once the command has exited. We capture the full
    ``ExecutionResult`` at ``exec()`` time, then expose it through the
    ``SandboxProcess`` API: ``stdout()`` / ``stderr()`` yield the
    captured output as a single chunk, ``wait()`` returns the exit code
    immediately, ``kill()`` is a no-op (the process is already gone).
    """

    def __init__(
        self,
        result: Any,
        *,
        session: Optional["K8sAgentSandboxSession"] = None,
    ) -> None:
        """Initializes the process wrapper.

        Args:
            result: The ``k8s_agent_sandbox.models.ExecutionResult``
                returned by ``sandbox.commands.run``.
            session: Owning session. When provided, captured output
                is also re-emitted through ``session._wrap_stream`` so
                it lands in the per-session sandbox log source.
        """
        self._result = result
        self._session = session

    def stdout(self) -> Iterator[str]:
        """Yields captured stdout as a single chunk.

        Returns:
            One-element iterator over the full stdout string when
            present, log-wrapped via ``session._wrap_stream`` if a
            session is attached.
        """
        text = self._result.stdout or ""
        lines = iter([text]) if text else iter([])
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stdout")

    def stderr(self) -> Iterator[str]:
        """Yields captured stderr as a single chunk.

        Returns:
            One-element iterator over the full stderr string when
            present, log-wrapped via ``session._wrap_stream`` if a
            session is attached.
        """
        text = self._result.stderr or ""
        lines = iter([text]) if text else iter([])
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stderr")

    def wait(self, timeout: Optional[float] = None) -> int:
        """Returns the exit code immediately.

        The blocking HTTP POST already completed at ``exec()`` time;
        ``wait()`` is therefore a no-op that just surfaces the exit
        code. ``timeout`` is accepted for interface compatibility but
        has no effect.

        Args:
            timeout: Ignored — the underlying call already returned.

        Returns:
            The captured exit code.
        """
        del timeout
        return int(self._result.exit_code)

    def kill(self) -> None:
        """No-op — the process has already terminated."""

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code captured at ``exec()`` time.

        Returns:
            The captured exit code (never ``None`` for this flavor).
        """
        return int(self._result.exit_code)


class K8sAgentSandboxSession(SandboxSession):
    """Wraps a ``k8s_agent_sandbox.Sandbox`` handle in the session interface."""

    def __init__(
        self,
        sandbox: "Sandbox",
        *,
        parent: "BaseSandbox",
    ) -> None:
        """Initializes the session wrapper.

        Args:
            sandbox: The live ``Sandbox`` returned by
                ``SandboxClient.create_sandbox``.
            parent: The owning ``BaseSandbox`` component.
        """
        super().__init__(
            id=str(sandbox.name),
            parent=parent,
        )
        self._sandbox = sandbox

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Runs a command in the Sandbox via the SDK's blocking POST.

        Args:
            command: Command to run. ``List[str]`` is joined argv-style
                via ``shlex.join`` before being passed to ``commands.run``
                (which takes a single shell-string). A string is passed
                through unmodified.
            cwd: Working directory. Prepended as a ``cd <cwd> && ...``
                prefix because the SDK's ``commands.run`` does not
                expose a per-call workdir.
            env: Per-exec env vars. Prepended as inline ``KEY=value``
                exports for the same reason — Session-level env should
                be set at sandbox-creation time on the operator side.

        Returns:
            An ``K8sAgentSandboxProcess`` carrying the captured
            ``ExecutionResult``.

        Raises:
            SandboxExecError: If the SDK raises while issuing the HTTP
                POST (network error, sandbox unhealthy, etc.).
        """
        cmd_str = shlex.join(command) if isinstance(command, list) else command
        if env:
            prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
            cmd_str = f"{prefix} {cmd_str}"
        if cwd is not None:
            cmd_str = f"cd {shlex.quote(cwd)} && {cmd_str}"

        argv_for_log = (
            list(command) if isinstance(command, list) else [command]
        )
        self._log_command(argv_for_log)

        started_at = time.time()
        try:
            result = self._sandbox.commands.run(cmd_str)
        except Exception as e:
            raise SandboxExecError(
                f"agent-sandbox exec failed to launch "
                f"({type(e).__name__}): {e}"
            ) from e
        wrapped = K8sAgentSandboxProcess(result, session=self)
        wrapped._started_at = started_at
        return wrapped

    def close(self) -> None:
        """Closes the session by terminating the underlying Sandbox.

        Idempotent — repeated calls log at debug but do not raise.
        """
        try:
            self._sandbox.terminate()
        except Exception as e:  # noqa: BLE001
            logger.debug("agent-sandbox terminate raised during close: %s", e)
        super().close()


class K8sAgentSandbox(BaseSandbox):
    """Sandbox flavor backed by ``k8s-agent-sandbox``."""

    _client: Optional["SandboxClient"] = None

    @property
    def config(self) -> K8sAgentSandboxConfig:
        """Typed config accessor.

        Returns:
            The component config.
        """
        return cast(K8sAgentSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type[BaseSettings]]:
        """Per-step settings class.

        Returns:
            ``K8sAgentSandboxSettings``.
        """
        return K8sAgentSandboxSettings

    def _get_kube_api_client(self) -> Any:
        """Resolves a ``kubernetes.client.ApiClient`` from the connector.

        When the component has a linked service connector that exposes
        a ``kubernetes-cluster`` resource, use its short-lived
        credentials. Otherwise fall back to the ambient kubeconfig
        (``~/.kube/config`` or ``KUBECONFIG``) that the SDK loads by
        default.

        Returns:
            A configured ``kubernetes.client.ApiClient``, or ``None``
            when no connector is linked (caller defers to SDK defaults).

        Raises:
            RuntimeError: If the linked connector returns something
                other than ``kubernetes.client.ApiClient`` — indicates a
                misconfigured connector or SDK version mismatch.
        """
        connector = self.get_connector()
        if connector is None:
            return None
        from kubernetes import (
            client as k8s_client,  # type: ignore[import-untyped]
        )

        api_client = connector.connect()
        if not isinstance(api_client, k8s_client.ApiClient):
            raise RuntimeError(
                f"Expected kubernetes.client.ApiClient from connector, "
                f"got {type(api_client).__name__}."
            )
        return api_client

    def _build_connection_config(self, eff: K8sAgentSandboxSettings) -> Any:
        """Builds a ``SandboxConnectionConfig`` from the effective settings.

        Args:
            eff: Effective settings merged from config + overrides.
                Currently unused but kept on the signature so future
                per-step connection knobs (e.g. an override
                ``api_url``) plug in cleanly.

        Returns:
            One of the SDK's ``Sandbox*ConnectionConfig`` instances,
            sized to the configured ``connection_mode``.

        Raises:
            ValueError: If ``connection_mode=direct`` and ``api_url``
                is not configured.
        """
        del eff
        from k8s_agent_sandbox.models import (
            SandboxDirectConnectionConfig,
            SandboxGatewayConnectionConfig,
            SandboxInClusterConnectionConfig,
            SandboxLocalTunnelConnectionConfig,
        )

        mode = self.config.connection_mode
        if mode == ConnectionMode.DIRECT:
            if not self.config.api_url:
                raise ValueError(
                    "connection_mode=direct requires `api_url` on the "
                    "component config."
                )
            return SandboxDirectConnectionConfig(api_url=self.config.api_url)
        if mode == ConnectionMode.GATEWAY:
            return SandboxGatewayConnectionConfig(
                gateway_name=self.config.gateway_name,
                gateway_namespace=self.config.gateway_namespace,
            )
        if mode == ConnectionMode.IN_CLUSTER:
            return SandboxInClusterConnectionConfig()
        return SandboxLocalTunnelConnectionConfig()

    def _get_client(self, eff: K8sAgentSandboxSettings) -> "SandboxClient":
        """Returns a memoised ``SandboxClient`` for this component.

        Plumbs the connector-provided kubeconfig (when available) into
        ``kubernetes.client.Configuration.set_default`` so the SDK's
        internal ``K8sHelper`` picks it up at construction time. This
        is the SDK's documented integration seam: ``K8sHelper.__init__``
        calls ``config.load_kube_config()`` which honours the default
        configuration if one is already set.

        Args:
            eff: Effective per-call settings (forwarded to
                ``_build_connection_config``).

        Returns:
            The shared ``SandboxClient`` instance.
        """
        if self._client is not None:
            return self._client

        api_client = self._get_kube_api_client()
        if api_client is not None:
            from kubernetes import (
                client as k8s_client,  # type: ignore[import-untyped]
            )

            k8s_client.Configuration.set_default(api_client.configuration)

        from k8s_agent_sandbox import SandboxClient

        self._client = SandboxClient(
            connection_config=self._build_connection_config(eff),
        )
        return self._client

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a new Agent Sandbox Session.

        Args:
            settings: Per-call overrides on top of the component config.

        Returns:
            A live ``K8sAgentSandboxSession`` ready for ``exec`` calls.

        Raises:
            ValueError: If ``template_name`` is unset (inline template
                synthesis is planned but not yet implemented in this
                skeleton).
        """
        eff = cast(
            K8sAgentSandboxSettings, self.resolve_settings(override=settings)
        )

        if not eff.template_name:
            raise ValueError(
                "Inline template synthesis is not yet implemented. "
                "Pre-create a SandboxTemplate in the cluster and set "
                "`template_name` on the component config or per-step "
                "settings."
            )

        client = self._get_client(eff)
        namespace = eff.namespace or self.config.default_namespace
        sandbox = client.create_sandbox(
            template=eff.template_name,
            namespace=namespace,
            sandbox_ready_timeout=eff.sandbox_ready_timeout,
        )
        return K8sAgentSandboxSession(sandbox, parent=self)
