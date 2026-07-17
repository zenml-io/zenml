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
builds its kubernetes API clients eagerly inside ``SandboxClient.__init__`` /
``K8sHelper.__init__``: each client snapshots ``Configuration._default`` at
construction time. The fix installs the connector's configuration as that
default and suppresses the ambient-config loaders for the short window in which
those constructors run, so the built clients bind to the connector's cluster.

If a future SDK release defers client construction (or config loading) to the
first API call, that call would happen *outside* the scoped window — where the
loaders are un-patched and the default has been restored — and the sandbox
would silently talk to the ambient kubeconfig instead of the connector's
cluster. The mock-level unit tests in ``sandboxes/test_k8s_agent_sandbox.py``
stub the SDK wholesale, so they cannot observe this. This test exercises the
*real* installed SDK and fails loudly if the eager-construction contract breaks.

It runs wherever the SDK is installed. In CI that is every unit-test leg: they
install all non-ignored integrations (``install_integrations: 'yes'`` in
``.github/workflows/unit-test.yml``), and ``k8s-agent-sandbox`` is one of them.
Where the SDK is absent (e.g. a bare ``PYTHONPATH=src`` run) it skips. The
skip gate reads the installed *distribution* rather than using a plain
``importorskip`` because the sibling test module installs a mock
``k8s_agent_sandbox`` in ``sys.modules`` at import time; an ``importorskip``
could hand back that stub instead of skipping.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import sys
from contextlib import contextmanager
from typing import Iterator, Optional, Tuple, Type
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

_REAL_CLASSES: Optional[Tuple[Type, Type]] = None


def _real_sdk() -> Tuple[Type, Type]:
    """Returns the *real* ``(K8sHelper, SandboxClient)`` classes.

    The sibling ``sandboxes/test_k8s_agent_sandbox.py`` module installs a mock
    ``k8s_agent_sandbox`` package in ``sys.modules``. To bypass it, drop any
    ``k8s_agent_sandbox`` entries, import the real distribution from disk, then
    restore the previous ``sys.modules`` state so the sibling's stub survives
    regardless of test ordering.

    The import happens exactly once and the classes are cached: the SDK's
    ``metrics`` module registers Prometheus timeseries against the global
    default registry at import time, so re-importing would raise a duplicate
    timeseries error. The cached class objects keep working after the module
    is removed from ``sys.modules`` — instantiating them re-uses the globals
    bound at import.

    Returns:
        The real ``K8sHelper`` and ``SandboxClient`` classes.
    """
    global _REAL_CLASSES
    if _REAL_CLASSES is not None:
        return _REAL_CLASSES

    saved = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "k8s_agent_sandbox" or name.startswith("k8s_agent_sandbox.")
    }
    for name in saved:
        del sys.modules[name]
    try:
        k8s_helper = importlib.import_module("k8s_agent_sandbox.k8s_helper")
        sandbox_client = importlib.import_module(
            "k8s_agent_sandbox.sandbox_client"
        )
        _REAL_CLASSES = (k8s_helper.K8sHelper, sandbox_client.SandboxClient)
    finally:
        for name in [
            n
            for n in list(sys.modules)
            if n == "k8s_agent_sandbox" or n.startswith("k8s_agent_sandbox.")
        ]:
            del sys.modules[name]
        sys.modules.update(saved)
    return _REAL_CLASSES


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


class TestSdkEagerConstructionContract:
    """Fails loudly if the SDK stops building API clients eagerly."""

    def test_k8s_helper_snapshots_default_at_construction(self) -> None:
        k8s_helper_cls, _ = _real_sdk()
        with _sentinel_default():
            helper = k8s_helper_cls()

        # Eager construction: the clients exist right after __init__, not
        # lazily on first use.
        assert helper.custom_objects_api is not None
        assert helper.core_v1_api is not None

        # Each client snapshotted the process-global default while the
        # sentinel was installed — the exact mechanism the connector fix
        # relies on. A lazy SDK would bind to the ambient default (some other
        # host, or None) instead.
        assert (
            helper.custom_objects_api.api_client.configuration.host
            == _SENTINEL_HOST
        )
        assert (
            helper.core_v1_api.api_client.configuration.host == _SENTINEL_HOST
        )

    def test_sandbox_client_builds_k8s_helper_eagerly(self) -> None:
        k8s_helper_cls, sandbox_client_cls = _real_sdk()
        with _sentinel_default():
            client = sandbox_client_cls()

        # SandboxClient.__init__ must build the K8sHelper (and thus its API
        # clients) eagerly; create_sandbox()/terminate() run outside the
        # scoped window and must reuse these already-bound clients.
        assert isinstance(client.k8s_helper, k8s_helper_cls)
        assert (
            client.k8s_helper.custom_objects_api.api_client.configuration.host
            == _SENTINEL_HOST
        )
