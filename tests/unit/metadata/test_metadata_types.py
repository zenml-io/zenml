#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Unit tests for metadata_types module."""

from zenml.metadata.metadata_types import (
    MetadataTypeEnum,
    get_metadata_type,
    validate_metadata,
)


class TestValidateMetadata:
    """Tests for validate_metadata function."""

    def test_validate_metadata_with_set(self):
        """Test that metadata with sets is validated without errors."""
        metadata = {"my_set": {1, 2, 3}, "my_string": "hello"}
        validated = validate_metadata(metadata)
        # Both entries should be kept
        assert "my_set" in validated
        assert "my_string" in validated
        assert validated["my_set"] == {1, 2, 3}
        assert validated["my_string"] == "hello"

    def test_validate_metadata_with_tuple(self):
        """Test that metadata with tuples is validated without errors."""
        metadata = {"my_tuple": (1, 2, 3)}
        validated = validate_metadata(metadata)
        assert "my_tuple" in validated
        assert validated["my_tuple"] == (1, 2, 3)

    def test_validate_metadata_with_nested_sets(self):
        """Test that metadata with nested sets is validated without errors."""
        metadata = {
            "nested": {
                "my_set": {1, 2, 3},
                "my_tuple": (4, 5, 6),
            }
        }
        validated = validate_metadata(metadata)
        assert "nested" in validated
        assert validated["nested"]["my_set"] == {1, 2, 3}
        assert validated["nested"]["my_tuple"] == (4, 5, 6)


class TestGetMetadataType:
    """Tests for get_metadata_type function."""

    def test_get_metadata_type_for_set(self):
        """Test that the correct type enum is returned for sets."""
        test_set = {1, 2, 3}
        result = get_metadata_type(test_set)
        assert result == MetadataTypeEnum.SET

    def test_get_metadata_type_for_tuple(self):
        """Test that the correct type enum is returned for tuples."""
        test_tuple = (1, 2, 3)
        result = get_metadata_type(test_tuple)
        assert result == MetadataTypeEnum.TUPLE
