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
"""Unit tests for tag schemas."""

from zenml.enums import ColorVariants
from zenml.models import TagUpdate
from zenml.zen_stores.schemas import TagSchema


def test_explicit_null_tag_update_fields_are_ignored() -> None:
    """Explicit nulls leave the stored values unchanged."""
    tag = TagSchema(
        name="test-tag",
        color=ColorVariants.RED.value,
        exclusive=True,
    )

    tag.update(TagUpdate(name=None, color=None, exclusive=None))

    assert tag.name == "test-tag"
    assert tag.color == ColorVariants.RED.value
    assert tag.exclusive is True
