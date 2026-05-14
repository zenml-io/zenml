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
"""Adapters for experimental ZenBabel step specifications."""

from typing import Any

from zenml.steps.base_step import BaseStep

PORTABLE_STEP_ADAPTER_SOURCE = "zenml.zenbabel.adapters.PortableStepAdapter"


class PortableStepAdapter(BaseStep):
    """Importable marker step for portable ZenBabel step bodies.

    Portable steps still need a Python ``Source`` so existing snapshot and
    pre-execution code can load a ``BaseStep`` and extract source/docstring
    information. This adapter provides that shape, but it is not a runnable
    step body. Portable execution must be routed through the dedicated portable
    runner once that runner exists.
    """

    def __init__(self) -> None:
        """Initialize without normal step interface validation.

        The adapter intentionally accepts arbitrary accidental execution
        arguments below, but normal ZenML step validation rejects catch-all
        entrypoints. This marker only needs the minimal ``BaseStep`` shape used
        for source/docstring/source-code extraction.
        """

    def entrypoint(self, *args: Any, **kwargs: Any) -> Any:
        """Reject accidental execution through the normal Python step path.

        Args:
            *args: Accidental positional arguments.
            **kwargs: Accidental keyword arguments.

        Raises:
            RuntimeError: Always, because this adapter is never the real step
                body.
        """
        raise RuntimeError(
            "PortableStepAdapter is a marker for ZenBabel portable steps and "
            "must not be executed as a normal Python step. Route this step "
            "through the portable step runner instead."
        )
