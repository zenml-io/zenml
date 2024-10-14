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

import uuid

from tests.unit.test_general import _test_materializer
from zenml.materializers.uuid_materializer import UUIDMaterializer


def test_uuid_materializer():
    """Test the UUID materializer."""
    test_uuid = uuid.uuid4()

    result = _test_materializer(
        step_output_type=uuid.UUID,
        materializer_class=UUIDMaterializer,
        step_output=test_uuid,
        expected_metadata_size=4,
    )
    assert result == test_uuid
    assert isinstance(result, uuid.UUID)


def test_uuid_materializer_metadata():
    """Test the metadata extraction of the UUID materializer."""
    test_uuid = uuid.uuid4()
    materializer = UUIDMaterializer("test_uri")
    metadata = materializer.extract_metadata(test_uuid)
    assert len(metadata) == 3
    assert metadata["uuid_version"] == test_uuid.version
    assert metadata["uuid_variant"] == test_uuid.variant
    assert metadata["string_representation"] == str(test_uuid)
