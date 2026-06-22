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
import re
import shlex
import threading
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

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

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
    from k8s_agent_sandbox.models import (
        ExecutionResult,
        SandboxConnectionConfig,
    )
    from k8s_agent_sandbox.sandbox import Sandbox

logger = get_logger(__name__)


_SANDBOX_TEMPLATE_GROUP = "extensions.agents.x-k8s.io"
_SANDBOX_TEMPLATE_VERSION = "v1beta1"
_SANDBOX_TEMPLATE_PLURAL = "sandboxtemplates"

# Env var keys are interpolated unquoted into `export <key>=...`; only
# shell-identifier keys are safe there.
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# ``Configuration._default`` is process-global; serializing
# ``_kube_default_config`` scopes keeps concurrent sessions for
# different clusters from cross-wiring credentials. The scope is held
# only while API clients are built (they snapshot the default at
# construction), not across the slow readiness wait, so fan-out stays
# parallel. A plain Lock (not RLock) suffices: no call path re-enters
# the context — each scope closes before the next one opens.
_kube_default_config_lock = threading.Lock()


def _delete_sandbox_template(name: str, namespace: str) -> None:
    """Deletes a SandboxTemplate CR by name + namespace.

    Lets kubernetes API exceptions propagate; callers decide whether
    to log + swallow (best-effort cleanup) or surface them.

    Args:
        name: SandboxTemplate name.
        namespace: Target namespace.
    """
    k8s_client.CustomObjectsApi().delete_namespaced_custom_object(
        group=_SANDBOX_TEMPLATE_GROUP,
        version=_SANDBOX_TEMPLATE_VERSION,
        namespace=namespace,
        plural=_SANDBOX_TEMPLATE_PLURAL,
        name=name,
    )


class K8sAgentSandboxProcess(SandboxProcess):
    """Single-shot process wrapping an ``ExecutionResult``."""

    def __init__(
        self,
        result: "ExecutionResult",
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
        parent: "K8sAgentSandbox",
        inline_template_name: Optional[str] = None,
        inline_template_namespace: Optional[str] = None,
    ) -> None:
        """Initializes the session wrapper.

        Args:
            sandbox: The live ``Sandbox`` returned by
                ``SandboxClient.create_sandbox``.
            parent: The owning ``K8sAgentSandbox`` component.
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

    def _exec(
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
            cwd: Working directory. The command is composed as
                ``cd <cwd> && { <exports><cmd><newline>}`` — the braces
                ensure nothing runs in the wrong directory when the
                ``cd`` fails; the SDK's ``commands.run`` doesn't expose
                a workdir kwarg.
            env: Per-exec env vars. Prepended as ``export KEY=value; ``
                statements so they apply to the entire command chain
                (``&&`` / ``;`` / ``|``). Keys must be valid shell
                identifiers (``[A-Za-z_][A-Za-z0-9_]*``).

        Returns:
            An ``K8sAgentSandboxProcess`` carrying the captured
            ``ExecutionResult``.

        Raises:
            ValueError: If an ``env`` key is not a valid shell
                identifier — keys are interpolated unquoted into the
                ``export`` statement, so anything else would allow
                shell injection.
            SandboxExecError: If the SDK raises while issuing the HTTP
                POST (network error, sandbox unhealthy, etc.).
        """
        cmd_str = shlex.join(command) if isinstance(command, list) else command
        if env:
            for key in env:
                if not _ENV_KEY_PATTERN.fullmatch(key):
                    raise ValueError(
                        f"Invalid environment variable name {key!r}: must "
                        "match [A-Za-z_][A-Za-z0-9_]*."
                    )
            exports = "".join(
                f"export {k}={shlex.quote(v)}; " for k, v in env.items()
            )
            cmd_str = f"{exports}{cmd_str}"
        if cwd is not None:
            # The group is terminated with a newline rather than `; }`:
            # a raw string command ending in `#comment`, `;` or `&`
            # would swallow or clash with `; }`, while a newline ends
            # comments and is a valid command terminator in all cases.
            cmd_str = f"cd {shlex.quote(cwd)} && {{ {cmd_str}\n}}"

        self._log_command(command)

        started_at = time.time()
        try:
            result = self._sandbox.commands.run(cmd_str)
        except Exception as e:
            raise SandboxExecError(
                f"agent-sandbox exec failed ({type(e).__name__}): {e}"
            ) from e
        return K8sAgentSandboxProcess(
            result, session=self, started_at=started_at
        )

    def _close(self) -> None:
        """Releases the session without terminating the sandbox."""
        if self._inline_template_name and self._inline_template_namespace:
            self._delete_inline_template()

    def _destroy(self) -> None:
        """Terminates the Sandbox and deletes any inline template CR."""
        try:
            # terminate() routes through the SDK's k8s_helper, whose API
            # clients already captured the connector credentials at build
            # time, so it needs no default-config scope. Keeping it out of
            # the scope also avoids serializing teardown on the global lock.
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
        # Retry the inline-template delete directly: close() is
        # idempotent, so if an earlier close() failed the delete (tracker
        # kept), routing through close() again would be a no-op.
        self._delete_inline_template()

    def _delete_inline_template(self) -> None:
        """Best-effort, idempotent delete of the inline SandboxTemplate CR."""
        name = self._inline_template_name
        namespace = self._inline_template_namespace
        if name is None or namespace is None:
            return
        try:
            with cast("K8sAgentSandbox", self._parent)._kube_default_config():
                _delete_sandbox_template(name, namespace)
        except Exception as e:  # noqa: BLE001
            if not (isinstance(e, ApiException) and e.status == 404):
                logger.warning(
                    "Cleanup of inline SandboxTemplate '%s' failed: %s. "
                    "Delete manually with `kubectl delete sandboxtemplate "
                    "-n %s %s` if it lingers.",
                    name,
                    e,
                    namespace,
                    name,
                )
                return
        # Clear the tracker only on success or 404 (already gone) so a
        # transient delete failure stays retryable from a later
        # destroy().
        self._inline_template_name = None
        self._inline_template_namespace = None


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

    def _get_kube_api_client(self) -> Optional[k8s_client.ApiClient]:
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
        api_client = connector.connect()
        if not isinstance(api_client, k8s_client.ApiClient):
            raise RuntimeError(
                f"Expected kubernetes.client.ApiClient from connector, "
                f"got {type(api_client).__name__}."
            )
        return api_client

    def _build_connection_config(self) -> "SandboxConnectionConfig":
        """Builds a ``SandboxConnectionConfig`` from the component config.

        Returns:
            One of the SDK's ``Sandbox*ConnectionConfig`` instances,
            sized to the configured ``connection_mode``.

        Raises:
            ValueError: If ``connection_mode=direct`` and ``api_url``
                is not configured.
        """
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

    @contextmanager
    def _kube_default_config(self) -> Iterator[None]:
        """Scopes the connector's kubeconfig as the kubernetes default.

        Callers must keep the scope tight: only the work that builds API
        clients (which snapshot the process-global default at
        construction) belongs inside it; slow network operations should
        run afterwards on the already-constructed clients so concurrent
        sessions don't serialize on the module-level lock.

        Yields:
            ``None`` — used as a context manager.

        Raises:
            RuntimeError: If no connector is linked and neither an
                in-cluster config nor a kubeconfig could be loaded.
        """
        with _kube_default_config_lock:
            api_client = self._get_kube_api_client()
            # ``Configuration._default`` is the same attribute
            # ``Configuration.set_default`` writes to; reading it directly
            # is the only way to snapshot the current default since the
            # upstream library doesn't expose a getter.
            previous = k8s_client.Configuration._default
            loader_overrides: List[Any] = []
            try:
                if api_client is not None:
                    k8s_client.Configuration.set_default(
                        api_client.configuration
                    )

                    # K8sHelper.__init__ calls load_incluster_config()/
                    # load_kube_config() before building its clients, which
                    # would overwrite the connector default with the ambient
                    # kubeconfig (silently using the local cluster). The SDK
                    # has no ApiClient injection seam, so suppress those
                    # loaders for the scope; it resolves them off the shared
                    # kubernetes.config module at call time, so patching the
                    # module intercepts them.
                    def _keep_connector_default(*_: Any, **__: Any) -> None:
                        return None

                    for _loader in (
                        "load_incluster_config",
                        "load_kube_config",
                    ):
                        loader_overrides.append(
                            (_loader, getattr(k8s_config, _loader))
                        )
                        setattr(k8s_config, _loader, _keep_connector_default)
                else:
                    # Both loaders mutate the process-global default in
                    # place; the snapshot above keeps the restore
                    # symmetric with the connector branch.
                    try:
                        k8s_config.load_incluster_config()
                    except k8s_config.ConfigException:
                        try:
                            k8s_config.load_kube_config()
                        except k8s_config.ConfigException as e:
                            raise RuntimeError(
                                "No Kubernetes credentials available: the "
                                "sandbox component has no service connector "
                                "linked, and neither an in-cluster config "
                                "nor a local kubeconfig could be loaded. "
                                "Link a Kubernetes service connector to the "
                                "component or configure a kubeconfig (e.g. "
                                "via `kubectl config use-context`)."
                            ) from e
                yield
            finally:
                for _loader, _original in loader_overrides:
                    setattr(k8s_config, _loader, _original)
                k8s_client.Configuration._default = previous

    def _build_client(self) -> "SandboxClient":
        """Builds a fresh ``SandboxClient`` per call.

        Not cached: connector tokens are short-lived and the SDK doesn't
        refresh them, so each session needs a rebuild.

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
            create_namespaced_custom_object``.

        Raises:
            ValueError: If no ``image`` is configured.
        """
        from zenml.integrations.kubernetes.manifest_utils import (
            add_pod_settings,
        )

        image = eff.image
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
            "apiVersion": f"{_SANDBOX_TEMPLATE_GROUP}/{_SANDBOX_TEMPLATE_VERSION}",
            "kind": "SandboxTemplate",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"podTemplate": {"spec": pod_spec_dict}},
        }

    def _synthesize_inline_template(
        self, eff: K8sAgentSandboxSettings, namespace: str
    ) -> str:
        """Creates a one-off SandboxTemplate CR for this session.

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

        namespace = eff.namespace
        template_name = eff.template_name
        synthesized_name: Optional[str] = None

        # Hold the connector-credential scope only for the fast,
        # default-dependent work: synthesizing the inline template CR and
        # constructing the SandboxClient (its K8sHelper snapshots the
        # config at build time). The slow create_sandbox readiness wait
        # then runs unlocked on the already-built client, so concurrently
        # mapped steps don't serialize on each other's pod boot.
        with self._kube_default_config():
            if not template_name:
                template_name = self._synthesize_inline_template(
                    eff, namespace
                )
                synthesized_name = template_name
            client = self._build_client()

        try:
            sandbox = client.create_sandbox(
                template=template_name,
                namespace=namespace,
                sandbox_ready_timeout=eff.sandbox_ready_timeout,
            )
        except Exception:
            # Allocated a CR but never got a sandbox — drop the CR so
            # flaky clusters / RBAC denials don't accumulate orphans.
            # The delete builds a fresh API client, so it needs the
            # connector scope again.
            if synthesized_name:
                try:
                    with self._kube_default_config():
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
