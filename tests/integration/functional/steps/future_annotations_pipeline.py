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
"""Pipeline module that exercises stringized annotations via PEP 563."""

from __future__ import annotations

from typing import Tuple

from typing_extensions import Annotated

from zenml import pipeline, step

ARTIFACT_NAME = "future_output"


@step
def produce(x: int) -> Annotated[int, ARTIFACT_NAME]:
    return x * 2


@step
def consume(value: int) -> Tuple[int, str]:
    return value + 1, "ok"


@pipeline(enable_cache=False)
def future_annotations_pipeline(x: int) -> None:
    out = produce(x=x)
    consume(value=out)
