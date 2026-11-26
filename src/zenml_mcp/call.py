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

from collections.abc import Callable, Mapping, Sequence
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
        sensitive_write: Called before a write that starts, resumes, stops
            or arms runs (the run tools, any trigger write, attaching a
            trigger to a snapshot, switching a webhook on, answering a paused
            run) or changes which model version holds a stage, with what it
            does; it raises to refuse the write. Each tool or resource
            catalog entry declares which writes these are (`Sensitive`).
        read_only: Whether the host offers no write tool: every tool not
            marked read-only refuses the call, and the resource catalog
            describes reads only.
        deadline: The event loop time (`loop.time()`) by which the host
            needs the call's answer, or None for no deadline, as the local
            server has. The optional reads after a run start that ZenML
            accepted end by then: the started run comes back without its
            dashboard link rather than as an unknown outcome.
    """

    client: ZenMLRestClient
    secret_page: SecretPage | None = None
    sensitive_write: Callable[[str], None] = field(default=_allow)
    read_only: bool = False
    deadline: float | None = None


@dataclass(frozen=True)
class Sensitive:
    """A write a host may refuse.

    It starts, resumes, stops or arms runs, or moves a model version's stage.

    Attributes:
        what: What the write does, as the host's `sensitive_write` is told.
        when_set: The arguments or payload fields that make the write
            sensitive when one is set to anything but null or false; empty
            when it always is.
    """

    what: str
    when_set: tuple[str, ...] = ()


def ask_if_sensitive(
    call: ZenMLCall,
    sensitive: Sensitive | None,
    given: Mapping[str, Any],
) -> None:
    """Ask the call's host before a sensitive write; it raises to refuse it.

    This is the one place `sensitive_write` is called, so a write is gated
    by what its tool or catalog entry declares, not by each tool remembering
    to ask.

    Args:
        call: The tool call, with its host's check.
        sensitive: What the write declares, or None when it isn't sensitive.
        given: The write's validated arguments or payload.
    """
    if sensitive is None:
        return
    if sensitive.when_set and all(
        given.get(name) is None or given.get(name) is False
        for name in sensitive.when_set
    ):
        return
    call.sensitive_write(sensitive.what)
