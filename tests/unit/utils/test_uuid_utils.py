#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from hypothesis.strategies import uuids

from zenml.utils import uuid_utils


@given(uuids(allow_nil=False))
def test_is_valid_uuid_works(generated_uuid):
    """Test the is_valid_uuid function."""
    assert uuid_utils.is_valid_uuid(generated_uuid)
    assert uuid_utils.is_valid_uuid(str(generated_uuid))
    assert not uuid_utils.is_valid_uuid("abc")
    assert not uuid_utils.is_valid_uuid(1234)


@given(uuids(allow_nil=False))
def test_parse_name_or_uuid_works(generated_uuid):
    """Test the parse_name_or_uuid function."""
    assert uuid_utils.parse_name_or_uuid("abc") == "abc"
    assert uuid_utils.parse_name_or_uuid("1234") == "1234"
    str_generated_uuid = str(generated_uuid)
    parsed_generated = uuid_utils.parse_name_or_uuid(str_generated_uuid)
    assert parsed_generated == generated_uuid
    assert isinstance(parsed_generated, UUID)
    assert uuid_utils.parse_name_or_uuid(None) is None


def test_generate_uuid_from_string_works():
    """Test the generate_uuid_from_string function."""
    assert isinstance(uuid_utils.generate_uuid_from_string("abc"), UUID)
    assert uuid_utils.generate_uuid_from_string("abc") != "abc"

    run1_output = uuid_utils.generate_uuid_from_string("abc")
    run2_output = uuid_utils.generate_uuid_from_string("abc")
    run3_output = uuid_utils.generate_uuid_from_string("def")
    assert run1_output == run2_output
    assert run1_output != run3_output
