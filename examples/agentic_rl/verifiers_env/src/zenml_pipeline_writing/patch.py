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
"""Select ZenMLSandboxRuntime until the upstream verifiers PR lands.

Why a patch at all: ``verifiers.v1.runtimes.RuntimeConfig`` is a closed
pydantic discriminated union (Subprocess | Docker | Prime | Modal) and
``_runtime_cls`` dispatches on ``isinstance`` — runtimes are the one
verifiers plugin type without dynamic loading. Vendors join the union
in-tree (Modal #1594, Daytona #1663); the ZenML runtime is written to
that shape (``runtime.py``) and this patch dies the day it merges.

Why the patch rides the ``docker`` discriminator instead of adding a
``zenml`` one: prime-rl's ORCHESTRATOR process validates the full TOML
(including ``[harness.runtime] type``) at startup and never imports the
env package, so a ``type = "zenml"`` value is rejected by pydantic
before any import side-effect of this package could extend the union.
``type = "docker"`` validates everywhere; the env-server process — the
only place ``make_runtime`` runs — imports this package (it hosts the
taskset), which patches ``_runtime_cls`` so DockerConfig-selected
rollouts execute on the ZenML sandbox instead. DockerConfig's fields
(image, workdir, cpu, memory) map onto sandbox settings almost 1:1, so
nothing is lost in the ride.

Opt-in via environment variable so the same taskset package can run on
verifiers' own Docker runtime unpatched:

    ZENML_VERIFIERS_RUNTIME=1
"""

import os

from zenml_pipeline_writing.runtime import ZenMLSandboxRuntime


def apply() -> bool:
    """Patch verifiers' runtime dispatch to select the ZenML runtime.

    Returns:
        Whether the patch was applied (False when opted out or when
        verifiers is not importable in this process).
    """
    if os.environ.get("ZENML_VERIFIERS_RUNTIME", "").lower() not in (
        "1",
        "true",
    ):
        return False

    try:
        import verifiers.v1.runtimes as runtimes
    except ImportError:
        return False

    original_runtime_cls = runtimes._runtime_cls

    def _zenml_runtime_cls(config):  # type: ignore[no-untyped-def]
        if isinstance(config, runtimes.DockerConfig):
            return ZenMLSandboxRuntime
        return original_runtime_cls(config)

    runtimes._runtime_cls = _zenml_runtime_cls
    return True
