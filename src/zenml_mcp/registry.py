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
"""The specs a server registers the ZenML MCP tools, resources and prompts by.

A spec's handler takes the call's `ZenMLCall` first and the tool's own
arguments as keywords. A host registers each tool under its name with its
description, annotations and `_meta`, and runs it with `ToolSpec.run`, which
validates the arguments and answers a ZenML failure as a tool error. The
specs themselves are in `zenml_mcp.tools`.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Literal, Protocol

from mcp.server.mcpserver.utilities.func_metadata import (
    ArgModelBase,
    func_metadata,
)
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from zenml_mcp.call import Sensitive, ZenMLCall, ask_if_sensitive
from zenml_mcp.client import ZenMLPermissionDenied, ZenMLRestError


class Handler(Protocol):
    """A tool's, resource's or prompt's function, listed by its name."""

    __name__: str
    __qualname__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[Any]:
        """Run it.

        Args:
            *args: Its positional arguments.
            **kwargs: Its keyword arguments.

        Returns:
            Its answer, once awaited.
        """


@dataclass(frozen=True)
class PageOutcome:
    """A secret write's answer, as a secret page shows it.

    Attributes:
        unknown: Whether the write may have happened though the answer can't
            confirm it.
        check: What to read to find out, when `unknown`.
        name: The name of what was written.
        identifier: The id of what was written.
        issued: A secret ZenML issued, shown once.
    """

    unknown: bool = False
    check: Any = ""
    name: Any = None
    identifier: Any = None
    issued: Any = None


@dataclass(frozen=True)
class SecretWrites:
    """The writes of a tool that a secret page may run.

    Attributes:
        names: The resource type and operation a call's arguments name.
        paths: For each, where in the arguments a secret may go (`*` is any
            one key).
        outcome: Reads the tool's answer to a write the page ran.
    """

    names: Callable[[Mapping[str, Any]], tuple[str, str]]
    paths: Mapping[tuple[str, str], tuple[str, ...]]
    outcome: Callable[[Mapping[str, Any]], PageOutcome]


def error_result(kind: str, message: str) -> CallToolResult:
    """A failed call's answer: `{"error": {"kind", "message"}}`.

    Args:
        kind: A stable category, such as `not_found`.
        message: What happened and what to do next.

    Returns:
        The tool result, marked as an error.
    """
    body = {"error": {"kind": kind, "message": message}}
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(body))],
        structured_content=body,
        is_error=True,
    )


@dataclass(frozen=True)
class ToolSpec:
    """One tool.

    Attributes:
        name: The tool's name.
        handler: Runs the tool: the call first, its arguments as keywords.
        annotations: Its MCP annotations, read-only hint included.
        description: Its description, or None for the handler's docstring.
        meta: Its `_meta`, such as the view it opens.
        structured_output: Passed to the MCP SDK as it registers the tool.
        secret_writes: The writes a secret page may run, for a tool whose
            arguments can carry a secret.
        needs_server: Whether the tool reads ZenML. A host may run one that
            doesn't without a server or a sign-in: it never uses its call's
            client.
        sensitive: Whether every call of the tool starts, resumes, stops or
            arms runs, or moves a model stage, so `run` asks the host first.
            The generic write tools declare it per resource type instead.
    """

    name: str
    handler: Handler
    annotations: ToolAnnotations
    description: str | None = None
    meta: dict[str, Any] | None = None
    structured_output: bool | None = None
    secret_writes: SecretWrites | None = None
    needs_server: bool = True
    sensitive: Sensitive | None = None

    @cached_property
    def signature(self) -> inspect.Signature:
        """The tool's own arguments, without the call, with resolved types.

        Returns:
            The signature a host registers the tool with.
        """
        signature = inspect.signature(self.handler, eval_str=True)
        parameters = list(signature.parameters.values())[1:]
        return signature.replace(parameters=parameters)

    @cached_property
    def arguments(self) -> type[ArgModelBase]:
        """The model of the tool's arguments; unknown arguments are refused.

        Returns:
            The arguments model.
        """
        model = func_metadata(self.handler, skip_names=["call"]).arg_model
        model.model_config = {
            **model.model_config,
            "extra": "forbid",
            "hide_input_in_errors": True,
        }
        model.model_rebuild(force=True)
        return model

    async def run(self, call: ZenMLCall, arguments: Mapping[str, Any]) -> Any:
        """Run the tool once.

        A read-only call refuses every tool not marked read-only here, so a
        host need not filter write tools to keep them from running.

        Args:
            call: The call's client and its host's decisions.
            arguments: The tool's arguments, as the client sent them.

        Returns:
            The tool's answer, or an error result when the call is read-only
            and the tool writes, or the host or ZenML refused the call with
            a ZenML error, or ZenML failed it. Any other error the host
            raises to refuse a sensitive write propagates.
        """
        if call.read_only and self.annotations.read_only_hint is not True:
            return error_result(
                ZenMLPermissionDenied.kind,
                f"{self.name} changes ZenML, and this server is read-only.",
            )
        validated = self.arguments.model_validate(dict(arguments))
        given = validated.model_dump_one_level()
        try:
            # Asked here as the generic writes ask in their handler, so a
            # host's refusal is answered the same whichever tool wrote.
            ask_if_sensitive(call, self.sensitive, given)
            return await self.handler(call, **given)
        except ZenMLRestError as error:
            return error_result(error.kind, error.message)


@dataclass(frozen=True)
class ContentSpec:
    """A prompt, or a resource named by its URI or URI template.

    Attributes:
        kind: Whether it is a prompt or a resource.
        name: The prompt's name, or the resource's URI.
        handler: Reads it; one that takes `call` first reads ZenML.
        options: Passed to the MCP SDK as it registers it.
    """

    kind: Literal["prompt", "resource"]
    name: str
    handler: Handler
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_call(self) -> bool:
        """Whether reading it takes a call, to read ZenML.

        Returns:
            True when the handler's first parameter is `call`.
        """
        parameters = list(inspect.signature(self.handler).parameters)
        return bool(parameters) and parameters[0] == "call"


class Tools:
    """Collects the specs each tool module registers, in listing order."""

    def __init__(self) -> None:
        """No specs yet."""
        self.tools: list[ToolSpec] = []
        self.contents: list[ContentSpec] = []

    def tool(
        self,
        *,
        annotations: ToolAnnotations,
        description: str | None = None,
        meta: dict[str, Any] | None = None,
        structured_output: bool | None = None,
        secret_writes: SecretWrites | None = None,
        needs_server: bool = True,
        sensitive: Sensitive | None = None,
    ) -> Callable[[Handler], Handler]:
        """Register a tool under its handler's name.

        Args:
            annotations: Its MCP annotations.
            description: Replaces the docstring, for text whose indentation
                must stay as written.
            meta: Its `_meta`.
            structured_output: Passed to the MCP SDK.
            secret_writes: The writes a secret page may run.
            needs_server: Whether it reads ZenML.
            sensitive: What the host is asked before every call, if anything.

        Returns:
            A decorator that registers the handler and returns it.
        """

        def decorate(handler: Handler) -> Handler:
            self.tools.append(
                ToolSpec(
                    name=handler.__name__,
                    handler=handler,
                    annotations=annotations,
                    description=description,
                    meta=meta,
                    structured_output=structured_output,
                    secret_writes=secret_writes,
                    needs_server=needs_server,
                    sensitive=sensitive,
                )
            )
            return handler

        return decorate

    def prompt(
        self, name: str, **options: Any
    ) -> Callable[[Handler], Handler]:
        """Register a prompt.

        Args:
            name: The prompt's name.
            **options: Passed to the MCP SDK.

        Returns:
            A decorator that registers the handler and returns it.
        """
        return self._content("prompt", name, {"name": name, **options})

    def resource(
        self, uri: str, **options: Any
    ) -> Callable[[Handler], Handler]:
        """Register a resource.

        Args:
            uri: Its URI or URI template.
            **options: Passed to the MCP SDK.

        Returns:
            A decorator that registers the handler and returns it.
        """
        return self._content("resource", uri, options)

    def _content(
        self,
        kind: Literal["prompt", "resource"],
        name: str,
        options: dict[str, Any],
    ) -> Callable[[Handler], Handler]:
        def decorate(handler: Handler) -> Handler:
            self.contents.append(ContentSpec(kind, name, handler, options))
            return handler

        return decorate
