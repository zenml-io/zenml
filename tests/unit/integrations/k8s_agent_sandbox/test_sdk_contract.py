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
"""Canary test pinning the k8s-agent-sandbox SDK's eager-construction contract.

The integration's connector-scoping fix
(``K8sAgentSandbox._kube_default_config``) is correct *only* because the SDK
builds its kubernetes API clients eagerly inside ``SandboxClient.__init__``:
each client snapshots ``Configuration._default`` at construction time. The fix
installs the connector's configuration as that default and suppresses the
ambient-config loaders for the short window in which ``SandboxClient(...)`` runs
(``sandboxes/k8s_agent_sandbox.py`` — see ``_build_client``), so the built
clients bind to the connector's cluster.

If a future SDK release defers client construction (or config loading) to the
first API call, that call would happen *outside* the scoped window — where the
loaders are un-patched and the default has been restored — and the sandbox
would silently talk to the ambient kubeconfig instead of the connector's
cluster. The mock-level unit tests in ``sandboxes/test_k8s_agent_sandbox.py``
stub the SDK wholesale, so they cannot observe this. This test exercises the
*real* installed SDK and fails loudly if the eager-construction contract breaks.

Loading the real SDK here is non-trivial: this test lives in the package
``tests/unit/integrations/k8s_agent_sandbox/``, which pytest imports as the
top-level package ``k8s_agent_sandbox`` — the *same* name as the SDK
distribution. That test package shadows the SDK on ``sys.path``, so an ordinary
``import k8s_agent_sandbox`` (or any dotted-submodule import) resolves to the
test package, not the installed SDK (``ModuleNotFoundError`` for real
submodules). ``_real_sandbox_client`` sidesteps the shadow by locating the
installed distribution's files via ``importlib.metadata`` and loading its
top-level ``__init__.py`` from disk with ``spec_from_file_location``. It loads
under the real name ``k8s_agent_sandbox`` (anchored to the real package dir via
``submodule_search_locations``) so the SDK's mixed relative/absolute self-
imports resolve to a single module tree — loading under a synthetic name makes
``from .metrics`` and ``from k8s_agent_sandbox.metrics`` diverge into two module
objects and the SDK's import-time Prometheus registration then fails with a
duplicate-timeseries error. The previous ``sys.modules`` state (the test
package) is restored afterwards.

The canary runs wherever the SDK is installed. In CI that is every unit-test
leg: they install all non-ignored integrations (``install_integrations: 'yes'``
in ``.github/workflows/unit-test.yml``), and ``k8s-agent-sandbox`` is one of
them. Where the SDK is absent (e.g. a bare ``PYTHONPATH=src`` run) it skips.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import sys
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional, Type
from unittest.mock import patch

import pytest

try:
    _SDK_VERSION: Optional[str] = importlib.metadata.version(
        "k8s-agent-sandbox"
    )
except importlib.metadata.PackageNotFoundError:
    _SDK_VERSION = None

pytestmark = pytest.mark.skipif(
    _SDK_VERSION is None,
    reason="k8s-agent-sandbox SDK not installed; canary only runs where it is.",
)

# A host no real cluster would answer on, used to prove a freshly built client
# snapshotted the default we installed rather than some ambient kubeconfig.
_SENTINEL_HOST = "https://zenml-canary-sentinel.invalid:6443"

_REAL_SANDBOX_CLIENT: Optional[Type] = None


def _real_sandbox_client() -> Type:
    """Returns the *real* installed ``SandboxClient`` class.

    Loads the SDK distribution from disk, bypassing the same-named test package
    that shadows it on ``sys.path`` (see module docstring). Uses only the
    top-level public ``SandboxClient`` export — the SDK's only contract with
    the integration. The load happens once and the class is cached: the SDK
    registers Prometheus timeseries against the global default registry at
    import time, so re-importing would raise a duplicate-timeseries error.

    Returns:
        The real ``k8s_agent_sandbox.SandboxClient`` class.
    """
    global _REAL_SANDBOX_CLIENT
    if _REAL_SANDBOX_CLIENT is not None:
        return _REAL_SANDBOX_CLIENT

    files = importlib.metadata.files("k8s-agent-sandbox") or []
    init = next(
        (
            f
            for f in files
            if f.name == "__init__.py"
            and f.parent.as_posix() == "k8s_agent_sandbox"
        ),
        None,
    )
    if init is None:
        pytest.fail(
            "k8s-agent-sandbox is installed but its top-level __init__.py "
            "could not be located in the distribution's file list."
        )
    init_path = str(init.locate())
    pkg_dir = os.path.dirname(init_path)

    saved = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "k8s_agent_sandbox" or name.startswith("k8s_agent_sandbox.")
    }
    for name in saved:
        del sys.modules[name]
    try:
        spec = importlib.util.spec_from_file_location(
            "k8s_agent_sandbox",
            init_path,
            submodule_search_locations=[pkg_dir],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        # Register under the real name before executing so the SDK's own
        # relative and absolute self-imports resolve to this single module.
        sys.modules["k8s_agent_sandbox"] = module
        spec.loader.exec_module(module)
        _REAL_SANDBOX_CLIENT = module.SandboxClient
    finally:
        for name in [
            n
            for n in list(sys.modules)
            if n == "k8s_agent_sandbox" or n.startswith("k8s_agent_sandbox.")
        ]:
            del sys.modules[name]
        sys.modules.update(saved)
    return _REAL_SANDBOX_CLIENT


@contextmanager
def _sentinel_default() -> Iterator[None]:
    """Installs a sentinel ``Configuration`` as the process-global default.

    Mirrors the connector branch of ``_kube_default_config``: the sentinel
    stands in for the connector's configuration, and the ambient-config loaders
    are suppressed so nothing can overwrite it while the SDK constructs its
    clients. The previous default is restored on exit.

    Yields:
        ``None`` — used as a context manager.
    """
    from kubernetes import client as k8s_client
    from kubernetes import config as k8s_config

    sentinel = k8s_client.Configuration()
    sentinel.host = _SENTINEL_HOST
    previous = k8s_client.Configuration._default
    try:
        k8s_client.Configuration.set_default(sentinel)
        with (
            patch.object(k8s_config, "load_incluster_config"),
            patch.object(k8s_config, "load_kube_config"),
        ):
            yield
    finally:
        k8s_client.Configuration._default = previous


def _collect_api_client_hosts(root: Any, max_depth: int = 5) -> List[str]:
    """Walks an object graph collecting kubernetes API-client config hosts.

    Duck-types the eager-construction check without naming SDK internals
    (``k8s_helper`` / ``custom_objects_api`` may move across the pinned SDK
    range): any reachable object exposing an ``api_client`` whose
    ``configuration.host`` is set is a constructed kubernetes API client. An
    empty result means the SDK built no clients eagerly.

    Args:
        root: The constructed ``SandboxClient`` to walk.
        max_depth: Maximum traversal depth.

    Returns:
        The ``configuration.host`` of every reachable kubernetes API client.
    """
    seen: set[int] = set()
    hosts: List[str] = []
    stack: List[tuple[Any, int]] = [(root, 0)]
    while stack:
        obj, depth = stack.pop()
        if id(obj) in seen or depth > max_depth:
            continue
        seen.add(id(obj))

        api_client = getattr(obj, "api_client", None)
        if api_client is not None:
            configuration = getattr(api_client, "configuration", None)
            host = getattr(configuration, "host", None)
            if host is not None:
                hosts.append(host)

        children: List[Any] = []
        instance_dict = getattr(obj, "__dict__", None)
        if isinstance(instance_dict, dict):
            children.extend(instance_dict.values())
        elif isinstance(obj, dict):
            children.extend(obj.values())
        elif isinstance(obj, (list, tuple, set)):
            children.extend(obj)
        for child in children:
            if not isinstance(child, (str, bytes, int, float, bool)):
                stack.append((child, depth + 1))
    return hosts


class TestSdkEagerConstructionContract:
    """Fails loudly if the SDK stops building API clients eagerly."""

    def test_sandbox_client_builds_api_clients_eagerly(self) -> None:
        sandbox_client_cls = _real_sandbox_client()
        with _sentinel_default():
            client = sandbox_client_cls()

        # SandboxClient.__init__ must build its kubernetes API clients right
        # away; create_sandbox()/terminate() run outside the connector-scoped
        # window and must reuse these already-built clients. A lazy SDK builds
        # nothing here, leaving the graph without any API client.
        hosts = _collect_api_client_hosts(client)
        assert hosts, (
            "SandboxClient() built no kubernetes API clients eagerly — the "
            "connector-scoping fix in _kube_default_config would silently "
            "fall back to the ambient kubeconfig. Widen the locked scope to "
            "cover the first real API call, or adopt an ApiClient injection "
            "seam if the SDK now exposes one."
        )

    def test_eagerly_built_clients_snapshot_connector_default(self) -> None:
        sandbox_client_cls = _real_sandbox_client()
        with _sentinel_default():
            client = sandbox_client_cls()

        # Each eagerly built client must have snapshotted the process-global
        # default while the sentinel (standing in for the connector config)
        # was installed — the exact mechanism connector isolation relies on.
        hosts = _collect_api_client_hosts(client)
        assert hosts  # guarded by the sibling test; keep this one focused
        assert all(host == _SENTINEL_HOST for host in hosts), (
            f"API clients did not snapshot the installed default at "
            f"construction (hosts={hosts!r}); expected all {_SENTINEL_HOST!r}."
        )
