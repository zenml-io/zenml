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
current operator. This implementation honors the SDK contract: each
``exec()`` issues one HTTP POST and surfaces the captured streams as
one-shot ``stdout()`` / ``stderr()`` iterators on
``K8sAgentSandboxProcess``. Real per-line streaming will land alongside the
snapshot/restore work once the operator exposes it.
"""

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


def _inline_template_error(name: str, namespace: str, exc: Any) -> str:
    """Builds a remediation-oriented error message for inline-template failures.

    Args:
        name: The SandboxTemplate name the create attempted.
        namespace: Target namespace.
        exc: The ``ApiException`` raised by the kubernetes client.

    Returns:
        A user-facing error string with status-specific hints.
    """
    status = getattr(exc, "status", None)
    reason = getattr(exc, "reason", None) or type(exc).__name__
    body = str(getattr(exc, "body", "") or "")
    base = (
        f"Failed to create inline SandboxTemplate '{name}' in namespace "
        f"'{namespace}': {status} {reason}."
    )
    # K8s 404 bodies are JSON like {"message":"namespaces \"foo\" not found",...}.
    # Substring match on both the resource kind and the namespace name
    # is robust against JSON escaping and structure changes.
    if status == 404 and "namespaces" in body and namespace in body:
        return (
            f"{base} Namespace '{namespace}' does not exist — create it "
            f"with `kubectl create namespace {namespace}` or point "
            "`namespace` at an existing one."
        )
    if status == 404:
        return (
            f"{base} The agent-sandbox CRDs aren't installed on this "
            "cluster — verify with `kubectl get crd sandboxtemplates."
            f"{_SANDBOX_TEMPLATE_GROUP}` and install via the operator's "
            "manifests."
        )
    if status == 403:
        return (
            f"{base} The service connector identity lacks create access "
            f"on sandboxtemplates.{_SANDBOX_TEMPLATE_GROUP}. Required "
            "verbs: get / list / create / delete on the same group."
        )
    if status == 409:
        return (
            f"{base} Name collision — unlikely with full-UUID naming, "
            "retry the call once."
        )
    return (
        f"{base} Verify the operator is installed and the connector "
        "identity has CRD create access."
    )


class K8sAgentSandboxProcess(SandboxProcess):
    """Single-shot process wrapping an ``ExecutionResult``.

    The agent-sandbox SDK's ``commands.run`` is a blocking HTTP POST
    that returns once the command has exited. We capture the full
    ``ExecutionResult`` at ``exec()`` time, then expose it through the
    ``SandboxProcess`` API: ``stdout()`` / ``stderr()`` yield captured
    output one line at a time (timing is single-shot, but the shape
    matches the line-iterator contract); ``wait()`` returns the exit
    code immediately; ``kill()`` is a no-op (the process is gone).
    """

    def __init__(
        self,
        result: Any,
        *,
        session: Optional["K8sAgentSandboxSession"] = None,
        started_at: Optional[float] = None,
    ) -> None:
        """Initializes the process wrapper.

        Args:
            result: The ``k8s_agent_sandbox.models.ExecutionResult``
                returned by ``sandbox.commands.run``.
            session: Owning session. When provided, captured output
                is also re-emitted through ``session._wrap_stream`` so
                it lands in the per-session sandbox log source.
            started_at: Wall-clock time the ``exec`` call began,
                forwarded to the base class so ``collect()`` can report
                duration accurately.
        """
        self._result = result
        self._session = session
        self._started_at = started_at

    def stdout(self) -> Iterator[str]:
        """Yields captured stdout one line at a time.

        Returns:
            Line-delimited iterator over the captured stdout (timing is
            single-shot — ``commands.run`` is one POST — but the shape
            matches the contract). Log-wrapped via ``session._wrap_stream``
            when a session is attached.
        """
        lines = iter((self._result.stdout or "").splitlines(keepends=True))
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stdout")

    def stderr(self) -> Iterator[str]:
        """Yields captured stderr one line at a time.

        Returns:
            Line-delimited iterator over the captured stderr, log-wrapped
            via ``session._wrap_stream`` when a session is attached.
        """
        lines = iter((self._result.stderr or "").splitlines(keepends=True))
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

        Always returns an ``int`` for this flavor (the SDK's
        ``commands.run`` is blocking — the process has always exited
        by the time the wrapper is constructed). Typed ``Optional[int]``
        to match the base contract.

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
                semantics. Session-level env should be baked into the
                container image / SandboxTemplate.

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
        return K8sAgentSandboxProcess(
            result, session=self, started_at=started_at
        )

    def close(self) -> None:
        """Releases the local handle.

        Per the base contract, ``close()`` is cheap and does NOT
        terminate the sandbox — call ``destroy()`` for that. The
        agent-sandbox operator has no built-in TTL on a SandboxClaim,
        so a `with create_session()` block that exits via ``close()``
        will leave the underlying pod running until explicitly
        destroyed (or cleaned up cluster-side). Inline-synthesized
        SandboxTemplate CRs ARE cleaned up here, since they're scoped
        to this session (the operator copies the spec into the
        SandboxClaim at claim time, so the template itself becomes
        disposable).

        Idempotent — repeated calls log at debug but do not raise.
        """
        if self._inline_template_name and self._inline_template_namespace:
            self._delete_inline_template()
        self._close_log_ctx()

    def destroy(self) -> None:
        """Terminates the underlying Sandbox and finalizes the session.

        Calls the SDK's ``Sandbox.terminate()`` (deletes the
        SandboxClaim CR; the operator garbage-collects the pod) and
        deletes any inline template CR we own. After this, ``attach()``
        on the session id will fail.

        Best-effort: partial failures (terminate or template delete)
        are logged at warning level but do not raise — callers can
        always `kubectl get sandboxclaim -n <ns>` to inspect remnants.
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
        self._close_log_ctx()

    def _delete_inline_template(self) -> None:
        """Best-effort delete of the inline-synthesized SandboxTemplate CR.

        Idempotent: clears the tracker before the API call so a second
        call (e.g. ``destroy()`` after ``close()``) is a no-op even if
        the first attempt crashed mid-flight.
        """
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
    """Sandbox flavor backed by ``k8s-agent-sandbox``.

    **Token rotation note.** Service connectors mint short-lived
    kubeconfigs (e.g. GKE access tokens expire after ~1h). Each
    ``create_session`` call goes back to the connector for fresh
    credentials, so long-running pipelines do not 401 mid-flight as
    long as session boundaries align with the rotation cadence.
    Sessions that themselves outlive the token will see 401s on
    ``exec`` / ``close`` — open a fresh session in that case.

    **In-cluster caveat.** The upstream SDK's ``K8sHelper.__init__``
    calls ``config.load_incluster_config()`` before falling back to
    ``load_kube_config()`` — so when this flavor runs inside the
    cluster, the in-cluster service account credentials win over any
    connector configuration we set as default. Use the in-cluster SA
    directly (or annotate it with workload-identity) rather than
    relying on the connector in that environment.
    """

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
        """Scopes connector-provided kubeconfig as the kubernetes default.

        The upstream SDK's ``K8sHelper.__init__`` calls
        ``config.load_kube_config()`` and provides no seam to inject an
        external ``ApiClient`` — so we set the connector's
        configuration as the process default for the duration of the
        block, then restore the previous default. This prevents two
        K8s-targeting components on the same stack from clobbering
        each other's auth at construction time when used sequentially.

        Not thread-safe: ``Configuration._default`` is process-global,
        so concurrent ``create_session`` calls from different threads
        can race on the snapshot/restore. In practice ZenML steps are
        sequential and the integration's primary use case is one
        session at a time; document if you encounter a concurrent
        pattern that needs different.

        Yields:
            ``None`` — used as a context manager.
        """
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
        """Builds a fresh ``SandboxClient``.

        Not memoised on purpose — connector tokens are short-lived
        (GKE access tokens expire ~1h) and the SDK doesn't refresh on
        its own, so we rebuild per ``create_session`` so each new
        session picks up freshly-minted credentials.

        Returns:
            A new ``SandboxClient`` instance configured for this
            component's connection mode.
        """
        from k8s_agent_sandbox import SandboxClient

        return SandboxClient(
            connection_config=self._build_connection_config(),
        )

    def _build_inline_template_body(
        self, eff: K8sAgentSandboxSettings, namespace: str, name: str
    ) -> Dict[str, Any]:
        """Constructs the SandboxTemplate CR body for inline mode.

        Reuses the Kubernetes integration's helpers rather than
        hand-rolling pod-spec construction:

        - ``kube_utils.convert_resource_settings_to_k8s_format`` maps
          the active step's ``ResourceSettings`` (cpu/memory/gpu) to
          K8s ``resources.requests`` / ``limits`` — handles fractional
          CPU as millicores, memory in MiB, and ``nvidia.com/gpu``
          mirrored to limits.
        - ``manifest_utils.add_pod_settings`` applies user-supplied
          ``KubernetesPodSettings`` (affinity, tolerations,
          node_selectors, volumes, env, security_context,
          additional_pod_spec_args, ...).
        - ``kubernetes.client`` typed objects (``V1PodSpec`` /
          ``V1Container``) + ``ApiClient.sanitize_for_serialization``
          for the final dict — same path the SDK itself uses.

        Args:
            eff: Effective settings (used for ``base_image`` and
                ``pod_settings``).
            namespace: Target namespace.
            name: Pre-generated template name.

        Returns:
            A dict ready to pass to ``CustomObjectsApi.
            create_namespaced_custom_object``. Mirrors the layout of
            the SDK's example ``python-sandbox-template.yaml``: a
            single container exposing port 8888 with an HTTP readiness
            probe, plus resource requests/limits and any pod-level
            customizations from settings.

        Raises:
            ValueError: If neither per-step ``base_image`` nor
                component-level ``default_image`` is set. Inline mode
                requires an explicit image — reproducibility-first.
        """
        from kubernetes import (
            client as k8s_client,
        )

        from zenml.integrations.kubernetes.kube_utils import (
            convert_resource_settings_to_k8s_format,
        )
        from zenml.integrations.kubernetes.manifest_utils import (
            add_pod_settings,
        )
        from zenml.steps.step_context import StepContext

        image = eff.base_image or self.config.default_image
        if not image:
            raise ValueError(
                "Inline SandboxTemplate synthesis requires an image. "
                "Set per-step `base_image` on K8sAgentSandboxSettings or "
                "`default_image` on the component config to a runtime "
                "image that exposes the agent-sandbox HTTP API on port "
                "8888 (e.g. the upstream `python-runtime-sandbox` image "
                "pinned to a specific digest). Or set `template_name` "
                "to reference a pre-created SandboxTemplate."
            )
        # Container shape mirrors the upstream
        # `python-sandbox-template.yaml`: name `python-runtime`, port
        # 8888 with HTTP readiness + liveness probes, default
        # `ephemeral-storage` request — the operator looks for these
        # signals to mark the pod Ready.
        probe = k8s_client.V1Probe(
            http_get=k8s_client.V1HTTPGetAction(path="/", port=8888),
            initial_delay_seconds=0,
            period_seconds=1,
        )
        container = k8s_client.V1Container(
            name="python-runtime",
            image=image,
            ports=[k8s_client.V1ContainerPort(container_port=8888)],
            readiness_probe=probe,
            liveness_probe=k8s_client.V1Probe(
                http_get=k8s_client.V1HTTPGetAction(path="/", port=8888),
                initial_delay_seconds=2,
                period_seconds=10,
            ),
        )

        # Default minimum resource requests matching the upstream
        # example. ResourceSettings (below) overrides these per step.
        requests: Dict[str, str] = {"ephemeral-storage": "512Mi"}
        limits: Dict[str, str] = {}
        ctx = StepContext.get()
        if ctx is not None:
            (
                rs_requests,
                rs_limits,
                _,
            ) = convert_resource_settings_to_k8s_format(
                ctx.step_run.config.resource_settings
            )
            requests.update(rs_requests)
            limits.update(rs_limits)
        container.resources = k8s_client.V1ResourceRequirements(
            requests=requests or None,
            limits=limits or None,
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
        a single Sandbox claim and are deleted on session close (unless
        ``inline_template_cleanup=False`` on the component config).

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
                _inline_template_error(name, namespace, e)
            ) from e
        return name

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a new Agent Sandbox Session.

        Resolves ``settings`` against the component config, then either
        references the configured ``template_name`` or — in inline mode
        — synthesizes a SandboxTemplate CR from ``base_image`` +
        ResourceSettings before claiming the sandbox.

        Args:
            settings: Per-call overrides on top of the component config.

        Returns:
            A live ``K8sAgentSandboxSession`` ready for ``exec`` calls.

        Raises:
            Exception: Re-raises whatever ``client.create_sandbox`` or
                ``_synthesize_inline_template`` raises — typically a
                ``RuntimeError`` from the kubernetes API (RBAC, missing
                CRDs, namespace permissions) or an SDK timeout when the
                claim doesn't become Ready. Any inline-synthesized
                SandboxTemplate CR is cleaned up before re-raising.
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
                # unconditionally so flaky clusters / RBAC denials don't
                # accumulate orphans, regardless of the user's
                # `inline_template_cleanup` setting (which only governs
                # *successful* session teardown).
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

            track_for_cleanup = (
                synthesized_name is not None
                and self.config.inline_template_cleanup
            )
            return K8sAgentSandboxSession(
                sandbox,
                parent=self,
                inline_template_name=(
                    synthesized_name if track_for_cleanup else None
                ),
                inline_template_namespace=(
                    namespace if track_for_cleanup else None
                ),
            )
