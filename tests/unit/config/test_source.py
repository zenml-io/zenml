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
"""Tests for source serialization."""

from typing import Optional

from pydantic import BaseModel

from zenml.config.source import (
    SERIALIZE_AS_STRING_CONTEXT_KEY,
    Source,
    StringSerializableSource,
)


class _ModelWithSource(BaseModel):
    source: Optional[StringSerializableSource] = None


def test_string_serializable_source_default_serialization():
    """Without the context flag, the source is serialized as a dict."""
    source = Source.from_import_path("zenml.client.Client")
    model = _ModelWithSource(source=source)

    assert model.model_dump()["source"] == source.model_dump()
    assert (
        _ModelWithSource.model_validate_json(model.model_dump_json()).source
        == source
    )


def test_string_serializable_source_serialization_as_string():
    """With the context flag, the source is serialized as its import path."""
    model = _ModelWithSource(
        source=Source.from_import_path("zenml.client.Client")
    )

    dumped = model.model_dump(context={SERIALIZE_AS_STRING_CONTEXT_KEY: True})

    assert dumped["source"] == "zenml.client.Client"
