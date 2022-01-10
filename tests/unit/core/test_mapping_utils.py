#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from uuid import UUID

from hypothesis import given
from hypothesis.strategies import integers, text

from zenml.core.mapping_utils import UUIDSourceTuple, get_key_from_uuid


@given(
    sample_uuid=integers(
        min_value=11111111111111111111111111111111,
        max_value=99999999999999999999999999999999,
    ),
    sample_source=text(min_size=1),
)
def test_uuidsourcetuple_instance_is_instance_of_pydantic_base_model(
    sample_uuid: int, sample_source: str
) -> None:
    """Check to make sure that instances of the UUIDSourceTuple class
    are of type BaseComponent"""
    uuid_st_instance = UUIDSourceTuple(
        uuid=UUID(str(sample_uuid)), source=sample_source
    )
    assert isinstance(uuid_st_instance, UUIDSourceTuple)
    assert uuid_st_instance.uuid == UUID(str(sample_uuid))
    assert uuid_st_instance.source == sample_source


@given(
    sample_uuid=integers(
        min_value=11111111111111111111111111111111,
        max_value=99999999999999999999999999999999,
    ),
    sample_source=text(min_size=1),
)
def test_get_key_from_uuid_returns_key_pointing_to_uuid(
    sample_uuid: int, sample_source: str
) -> None:
    """Check to make sure that get_key_from_uuid returns the key
    pointing to a certain uuid in a mapping"""
    uuid_st_instance = UUIDSourceTuple(
        uuid=UUID(str(sample_uuid)), source=sample_source
    )
    mapping_dict = {
        sample_source: uuid_st_instance,
    }
    assert (
        get_key_from_uuid(uuid_st_instance.uuid, mapping_dict) == sample_source
    )
