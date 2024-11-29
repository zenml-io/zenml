#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Custom ZenML types."""

from typing import TYPE_CHECKING, Callable, Union

if TYPE_CHECKING:
    from types import FunctionType

    from zenml.config.source import Source

    HookSpecification = Union[str, Source, FunctionType, Callable[..., None]]


class HTMLString(str):
    """Special string class to indicate an HTML string."""


class MarkdownString(str):
    """Special string class to indicate a Markdown string."""


class CSVString(str):
    """Special string class to indicate a CSV string."""


class JSONString(str):
    """Special string class to indicate a JSON string."""
