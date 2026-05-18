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
"""Helper module exercising PEP 563 stringized annotations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from typing_extensions import Annotated

from zenml.artifacts.artifact_config import ArtifactConfig

if TYPE_CHECKING:
    # Importing only under TYPE_CHECKING simulates the failure case where
    # an annotation references a name that isn't available at runtime.
    from decimal import Decimal  # noqa: F401


def func_stringized_param(x: int) -> int:
    return x + 1


def func_stringized_return() -> int:
    return 1


def func_stringized_annotated_name() -> Annotated[int, "named"]:
    return 1


def func_stringized_artifact_config() -> Annotated[
    int, ArtifactConfig(name="ac_named")
]:
    return 1


def func_stringized_multi_output() -> Tuple[int, str]:
    return 1, "foo"


def func_stringized_optional(x: Optional[int]) -> int:
    return x or 0


def func_with_unresolved_return() -> Decimal:  # type: ignore[name-defined]
    raise NotImplementedError


def func_with_unresolved_input(x: Decimal) -> int:  # type: ignore[name-defined]
    return 0
