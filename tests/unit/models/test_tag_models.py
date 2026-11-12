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

import random

import pytest

from zenml.constants import ENV_ZENML_USE_GLOBAL_RANDOM_SEED
from zenml.enums import ColorVariants
from zenml.models import TagRequest


@pytest.mark.parametrize(
    "env_value, colors_repeat", [("false", False), ("true", True)]
)
def test_tag_color_global_seed(
    monkeypatch: pytest.MonkeyPatch, env_value: str, colors_repeat: bool
) -> None:
    """Tests that tag colors only repeat for a repeated seed when users opt in."""
    monkeypatch.setenv(ENV_ZENML_USE_GLOBAL_RANDOM_SEED, env_value)

    random.seed(42)
    first = [TagRequest(name="tag").color for _ in range(8)]
    random.seed(42)
    second = [TagRequest(name="tag").color for _ in range(8)]

    assert (first == second) is colors_repeat


def test_tag_color_keeps_explicit_color() -> None:
    """Tests that an explicit color is never replaced by a random one."""
    tag = TagRequest(name="tag", color=ColorVariants.PURPLE)
    assert tag.color == ColorVariants.PURPLE
