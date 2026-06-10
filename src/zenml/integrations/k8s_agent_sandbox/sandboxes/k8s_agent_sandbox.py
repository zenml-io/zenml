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
"""Agent Sandbox flavor implementation."""

import logging
import shlex
import time
import uuid
from contextlib import contextmanager
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
    from k8s_agent_sandbox import (
        SandboxClient,  # type: ignore[import-not-found]
    )
    from k8s_agent_sandbox.sandbox import (
        Sandbox,  # type: ignore[import-not-found]
    )

logger = get_logger(__name__)


_SANDBOX_TEMPLATE_GROUP = "extensions.agents.x-k8s.io"
_SANDBOX_TEMPLATE_VERSION = "v1beta1"
_SANDBOX_TEMPLATE_PLURAL = "sandboxtemplates"


def _delete_sandbox_template(name: str, namespace: str) -> None:
    """Deletes a SandboxTemplate CR by name + namespace.

    Lets kubernetes API exceptions propagate; callers decide whether
    to log + swallow (best-effort cleanup) or surface them.

    Args:
        name: SandboxTemplate name.
        namespace: Target namespace.
    """
    from kubernetes import (
        client as k8s_client,
    )

    k8s_client.CustomObjectsApi().delete_namespaced_custom_object(
        group=_SANDBOX_TEMPLATE_GROUP,
        version=_SANDBOX_TEMPLATE_VERSION,
        namespace=namespace,
        plural=_SANDBOX_TEMPLATE_PLURAL,
        name=name,
    )


class K8sAgentSandboxProcess(SandboxProcess):
    """Single-shot process wrapping an ``ExecutionResult``.

    The SDK's ``commands.run`` blocks until the command exits, so the
    full output is already captured by construction time.
    """

    def __init__(
        self,
        result: Any,
        *,
        session: "K8sAgentSandboxSession",
        started_at: float,
    ) -> None:
        """Initialize the process wrapper.

        Args:
            result: The k8s_agent_sandbox ExecutionResult returned by
                sandbox.commands.run.
            session: The owning session.
            started_at: Wall-clock time the exec call began.
        """
        super().__init__(session=session, started_at=started_at)
        self._result = result

    def stdout(self) -> Iterator[str]:
        """Stdout line iterator.

        Returns:
            Stdout line iterator.
        """
        lines = iter((self._result.stdout or "").splitlines(keepends=True))
        return self._session._wrap_stream(lines, log_level=logging.INFO)

    def stderr(self) -> Iterator[str]:
        """Stderr line iterator.

        Returns:
            Stderr line iterator.
        """
        lines = iter((self._result.stderr or "").splitlines(keepends=True))
        return self._session._wrap_stream(lines, log_level=logging.ERROR)

    def wait(self, timeout: Optional[float] = None) -> int:
        """Returns the exit code immediately.

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
            The captured exit code.
        """
        return int(self._result.exit_code)


class K8sAgentSandboxSession(SandboxSession):
    """Wraps a ``k8s_agent_sandbox.Sandbox`` handle in the session interface."""

    def __init__(
        self,
        sandbox: "Sandbox",
        *,
        parent: "BaseSandbox",
        inline_template_name: Optional[str] = None,
        inline_template_namespace: Optional[str] = None,
    ) -> None:
        """Initializes the session wrapper.

        Args:
            sandbox: The live ``Sandbox`` returned by
                ``SandboxClient.create_sandbox``.
            parent: The owning ``BaseSandbox`` component.
            inline_template_name: Name of an inline-synthesized
                SandboxTemplate CR to delete on close, or ``None`` when
                the session was created from a pre-existing template.
            inline_template_namespace: Namespace of the inline template
                (paired with ``inline_template_name``).
        """
        super().__init__(
            id=str(sandbox.name),
            parent=parent,
        )
        self._sandbox = sandbox
        self._inline_template_name = inline_template_name
        self._inline_template_namespace = inline_template_namespace

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
                via ``shlex.join`` — unambiguous shell semantics. A
                string is passed through unmodified; callers are
                responsible for any internal escaping.
            cwd: Working directory. Prepended as ``cd <cwd> && ...`` —
                the SDK's ``commands.run`` doesn't expose a workdir
                kwarg.
            env: Per-exec env vars. Prepended as inline ``KEY=value``
                exports. **Caveat**: when ``command`` is a
                shell-string containing ``&&`` / ``;`` / ``|``, the
                env prefix only binds to the first command in the
                chain. Pass ``command`` as a list, or pre-export the
                vars inside the command string, for unambiguous
                semantics.

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

        self._log_command(command)

        started_at = time.time()
        try:
            result = self._sandbox.commands.run(cmd_str)
        except Exception as e:
            raise SandboxExecError(
                f"agent-sandbox exec failed to launch "
                f"({type(e).__name__}): {e}"
            ) from e
        return K8sAgentSandboxProcess(
            result, session=self, started_at=started_at
        )

    def close(self) -> None:
        """Releases the session without terminating the sandbox.

        Deletes any inline-synthesized SandboxTemplate CR. Idempotent.
        """
        if self._inline_template_name and self._inline_template_namespace:
            self._delete_inline_template()

    def destroy(self) -> None:
        """Terminates the Sandbox and deletes any inline template CR.

        Best-effort: failures are logged with the kubectl command to
        reconcile manually, never raised.
        """
        try:
            self._sandbox.terminate()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "agent-sandbox terminate() failed: %s. The sandbox may "
                "still be running; reconcile via `kubectl delete "
                "sandboxclaim -n %s %s`.",
                e,
                self._inline_template_namespace or "<unknown>",
                self.id,
            )
        if self._inline_template_name and self._inline_template_namespace:
            self._delete_inline_template()

    def _delete_inline_template(self) -> None:
        """Best-effort, idempotent delete of the inline SandboxTemplate CR."""
        # Clear the tracker before the API call so a second call (e.g.
        # destroy() after close()) is a no-op even if this one crashes.
        name = self._inline_template_name
        namespace = self._inline_template_namespace
        self._inline_template_name = None
        self._inline_template_namespace = None
        if name is None or namespace is None:
            return
        try:
            _delete_sandbox_template(name, namespace)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Cleanup of inline SandboxTemplate '%s' failed: %s. "
                "Delete manually with `kubectl delete sandboxtemplate "
                "-n %s %s` if it lingers.",
                name,
                e,
                namespace,
                name,
            )


class K8sAgentSandbox(BaseSandbox):
    """Sandbox flavor backed by the ``k8s-agent-sandbox`` SDK."""

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
        """Resolves an ``ApiClient`` from the linked service connector.

        Returns:
            A configured ``kubernetes.client.ApiClient``, or ``None``
            when no connector is linked (caller falls back to the
            ambient kubeconfig the SDK loads by default).

        Raises:
            RuntimeError: If the connector returns something other than
                an ``ApiClient``.
        """
        connector = self.get_connector()
        if connector is None:
            return None
        from kubernetes import (
            client as k8s_client,
        )

        api_client = connector.connect()
        if not isinstance(api_client, k8s_client.ApiClient):
            raise RuntimeError(
                f"Expected kubernetes.client.ApiClient from connector, "
                f"got {type(api_client).__name__}."
            )
        return api_client

    def _build_connection_config(self) -> Any:
        """Builds a ``SandboxConnectionConfig`` from the component config.

        Returns:
            One of the SDK's ``Sandbox*ConnectionConfig`` instances,
            sized to the configured ``connection_mode``.

        Raises:
            ValueError: If ``connection_mode=direct`` and ``api_url``
                is not configured.
        """
        from k8s_agent_sandbox.models import (  # type: ignore[import-not-found]
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

    @contextmanager
    def _kube_default_config(self) -> Iterator[None]:
        """Scopes the connector's kubeconfig as the kubernetes default.

        Not thread-safe: ``Configuration._default`` is process-global.
        ZenML steps run sequentially, so this only matters for callers
        spawning concurrent ``create_session`` calls themselves.

        Yields:
            ``None`` — used as a context manager.
        """
        # The SDK's K8sHelper.__init__ calls config.load_kube_config()
        # with no seam to inject an ApiClient, so the only way to make
        # it use connector credentials is to set the process default
        # for the duration of the block. Inside a cluster the SDK tries
        # load_incluster_config() first, which wins over this default.
        api_client = self._get_kube_api_client()
        if api_client is None:
            yield
            return
        from kubernetes import (
            client as k8s_client,
        )

        # ``Configuration._default`` is the same attribute
        # ``Configuration.set_default`` writes to; reading it directly
        # is the only way to snapshot the current default since the
        # upstream library doesn't expose a getter.
        previous = k8s_client.Configuration._default
        try:
            k8s_client.Configuration.set_default(api_client.configuration)
            yield
        finally:
            k8s_client.Configuration._default = previous

    def _build_client(self) -> "SandboxClient":
        """Builds a fresh ``SandboxClient`` per call.

        Deliberately not cached: connector tokens are short-lived and
        the SDK doesn't refresh them, so each session needs a rebuild.

        Returns:
            A new ``SandboxClient`` for this component's connection mode.
        """
        from k8s_agent_sandbox import SandboxClient

        return SandboxClient(
            connection_config=self._build_connection_config(),
        )

    def _build_inline_template_body(
        self, eff: K8sAgentSandboxSettings, namespace: str, name: str
    ) -> Dict[str, Any]:
        """Constructs the SandboxTemplate CR body for inline mode.

        Args:
            eff: Effective settings (``image``, ``sandbox_environment``
                and ``pod_settings``).
            namespace: Target namespace.
            name: Pre-generated template name.

        Returns:
            A dict ready to pass to ``CustomObjectsApi.
            create_namespaced_custom_object``. Mirrors the layout of
            the SDK's example ``python-sandbox-template.yaml``: a
            single container exposing port 8888 with HTTP readiness /
            liveness probes, plus any pod-level customizations from
            settings.

        Raises:
            ValueError: If no ``image`` is configured. Inline mode
                requires an explicit image — reproducibility-first.
        """
        from kubernetes import (
            client as k8s_client,
        )

        from zenml.integrations.kubernetes.manifest_utils import (
            add_pod_settings,
        )

        image = eff.image or self.config.image
        if not image:
            raise ValueError(
                "Inline SandboxTemplate synthesis requires an image. "
                "Set `image` on the component config or per-step on "
                "K8sAgentSandboxSettings to a runtime image that exposes "
                "the agent-sandbox HTTP API on port 8888 (e.g. the "
                "upstream `python-runtime-sandbox` image pinned to a "
                "specific digest). Or set `template_name` to reference "
                "a pre-created SandboxTemplate."
            )
        # Container shape mirrors the upstream
        # `python-sandbox-template.yaml`: name `python-runtime`, port
        # 8888 with HTTP readiness + liveness probes — the operator
        # looks for these signals to mark the pod Ready.
        container = k8s_client.V1Container(
            name="python-runtime",
            image=image,
            ports=[k8s_client.V1ContainerPort(container_port=8888)],
            readiness_probe=k8s_client.V1Probe(
                http_get=k8s_client.V1HTTPGetAction(path="/", port=8888),
                initial_delay_seconds=0,
                period_seconds=1,
            ),
            liveness_probe=k8s_client.V1Probe(
                http_get=k8s_client.V1HTTPGetAction(path="/", port=8888),
                initial_delay_seconds=2,
                period_seconds=10,
            ),
            env=[
                k8s_client.V1EnvVar(name=key, value=value)
                for key, value in self._resolve_session_environment(
                    eff
                ).items()
            ]
            or None,
        )

        pod_spec = k8s_client.V1PodSpec(
            containers=[container],
            restart_policy="OnFailure",
        )

        if eff.pod_settings is not None:
            add_pod_settings(
                pod_spec=pod_spec,
                settings=eff.pod_settings,
                substitutions={"{{ image }}": image},
            )

        # `add_pod_settings` overwrites container resources with
        # `pod_settings.resources` (default `{}`), so the upstream
        # example's minimum ephemeral-storage request is applied
        # afterwards — and only when the user didn't size the pod
        # via `pod_settings.resources`.
        if not container.resources:
            container.resources = k8s_client.V1ResourceRequirements(
                requests={"ephemeral-storage": "512Mi"}
            )

        # Serialize the typed pod spec to a dict the k8s API will accept
        # inside the SandboxTemplate CR body.
        pod_spec_dict = k8s_client.ApiClient().sanitize_for_serialization(
            pod_spec
        )

        return {
            "apiVersion": "extensions.agents.x-k8s.io/v1beta1",
            "kind": "SandboxTemplate",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"podTemplate": {"spec": pod_spec_dict}},
        }

    def _synthesize_inline_template(
        self, eff: K8sAgentSandboxSettings, namespace: str
    ) -> str:
        """Creates a one-off SandboxTemplate CR for this session.

        Synthesized templates are short-lived — they exist only to back
        a single Sandbox claim and are deleted on session close.

        Args:
            eff: Effective settings.
            namespace: Target namespace for the CR.

        Returns:
            The generated template name.

        Raises:
            RuntimeError: If the Kubernetes API rejects the create
                (RBAC failure, CRD not installed, name collision, …).
                Raises with the underlying ``ApiException`` chained for
                diagnostics.
        """
        from kubernetes import (
            client as k8s_client,
        )
        from kubernetes.client.rest import (
            ApiException,
        )

        # Full uuid4 hex (32 chars) — fan-out workflows (step.map at
        # large N) make short names a real collision risk.
        name = f"zenml-sb-tpl-{uuid.uuid4().hex}"
        body = self._build_inline_template_body(eff, namespace, name)
        try:
            k8s_client.CustomObjectsApi().create_namespaced_custom_object(
                group=_SANDBOX_TEMPLATE_GROUP,
                version=_SANDBOX_TEMPLATE_VERSION,
                namespace=namespace,
                plural=_SANDBOX_TEMPLATE_PLURAL,
                body=body,
            )
        except ApiException as e:
            raise RuntimeError(
                f"Failed to create inline SandboxTemplate '{name}' in "
                f"namespace '{namespace}'. Verify the agent-sandbox CRDs "
                "are installed and the connector identity can create "
                f"sandboxtemplates.{_SANDBOX_TEMPLATE_GROUP}."
            ) from e
        return name

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a new Agent Sandbox Session.

        Uses the configured ``template_name``, or synthesizes an inline
        SandboxTemplate CR from the resolved settings when unset.

        Args:
            settings: Per-call overrides on top of the component config.

        Returns:
            A live ``K8sAgentSandboxSession`` ready for ``exec`` calls.

        Raises:
            Exception: Re-raised from the kubernetes API or the SDK
                (RBAC, missing CRDs, claim-readiness timeout). Any
                inline template CR is cleaned up before re-raising.
        """
        eff = cast(
            K8sAgentSandboxSettings, self.resolve_settings(override=settings)
        )

        # Scope connector-provided kubeconfig as the kubernetes default
        # for the duration of this call so CR creation + the
        # SandboxClient's K8sHelper all see the same credentials, and
        # restore the previous default on exit to avoid polluting
        # process-global state for sibling components.
        with self._kube_default_config():
            namespace = eff.namespace

            template_name = eff.template_name
            synthesized_name: Optional[str] = None
            if not template_name:
                template_name = self._synthesize_inline_template(
                    eff, namespace
                )
                synthesized_name = template_name

            try:
                sandbox = self._build_client().create_sandbox(
                    template=template_name,
                    namespace=namespace,
                    sandbox_ready_timeout=eff.sandbox_ready_timeout,
                )
            except Exception:
                # Allocated a CR but never got a sandbox — drop the CR
                # so flaky clusters / RBAC denials don't accumulate
                # orphans.
                if synthesized_name:
                    try:
                        _delete_sandbox_template(synthesized_name, namespace)
                    except Exception as cleanup_exc:  # noqa: BLE001
                        logger.warning(
                            "Failed to clean up orphan SandboxTemplate "
                            "'%s/%s' after create_sandbox failure: %s",
                            namespace,
                            synthesized_name,
                            cleanup_exc,
                        )
                raise

            return K8sAgentSandboxSession(
                sandbox,
                parent=self,
                inline_template_name=synthesized_name,
                inline_template_namespace=(
                    namespace if synthesized_name else None
                ),
            )
