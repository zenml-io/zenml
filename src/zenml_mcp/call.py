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
"""What a tool call runs with, and what its host decides for it.

A local server builds a `ZenMLCall` with only a client. A server that hosts
these tools for several users adds what it decides per call: a page where
the user types a secret instead of sending it through the model, a check
before a sensitive write, and whether it offers write tools at all.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from zenml_mcp.client import ZenMLRestClient


@dataclass(frozen=True)
class Asked:
    """A secret a secret page asks the user for.

    Attributes:
        path: Where the secret goes in the tool's arguments.
        label: What the field is called.
        required: Whether the write needs it.
    """

    path: tuple[str, ...]
    label: str
    required: bool


class SecretPage(Protocol):
    """A host's page where the user types a write's secret.

    With one, a write that carries a secret writes nothing: the tool answers
    with the page's link, and the page runs the same tool, with the secret in
    its arguments and without a page.
    """

    def awaiting_user(
        self, tool: str, arguments: dict[str, Any], asked: Sequence[Asked]
    ) -> dict[str, Any]:
        """The answer a tool gives in place of a secret write.

        Args:
            tool: The tool's name.
            arguments: The call's arguments, without the secret.
            asked: The secrets the page asks for.

        Returns:
            The tool's answer, such as the page's link.
        """


def _allow(what: str) -> None:
    """Allow every sensitive write.

    Args:
        what: The write, as in "Changing a model version's stage".
    """


@dataclass(frozen=True)
class ZenMLCall:
    """One tool call's client and its host's decisions.

    Attributes:
        client: The caller's client, built for this call.
        secret_page: Where the user types a write's secret. Without one, a
            secret in the arguments is sent to ZenML, as a local server does.
        sensitive_write: Called before a generic resource write that can
            start runs (a pipeline trigger's) or changes which model version
            holds a stage, with what it does; it raises to refuse the write.
            The tools that start runs themselves don't call it: a host
            restricts them by their annotations.
        read_only: Whether the host offers no write tool, so the resource
            catalog describes reads only.
    """

    client: ZenMLRestClient
    secret_page: SecretPage | None = None
    sensitive_write: Callable[[str], None] = field(default=_allow)
    read_only: bool = False
