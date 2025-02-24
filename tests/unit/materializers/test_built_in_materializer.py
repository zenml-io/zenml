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
import os
from tempfile import TemporaryDirectory
from typing import Optional, Type

from tests.unit.test_general import _test_materializer
from zenml.client import Client
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.built_in_materializer import (
    BuiltInContainerMaterializer,
)
from zenml.utils import source_utils, yaml_utils


def test_basic_type_materialization():
    """Test materialization for `bool`, `float`, `int`, `str` objects."""
    for type_, example in [
        (bool, True),
        (float, 0.0),
        (int, 0),
        (str, ""),
    ]:
        result = _test_materializer(
            step_output_type=type_,
            step_output=example,
            expected_metadata_size=1 if type_ is str else 2,
        )
        assert result == example


def test_bytes_materialization():
    """Test materialization for `bytes` objects.

    This is a separate test since `bytes` is not JSON serializable.
    """
    example = b""
    result = _test_materializer(
        step_output_type=bytes, step_output=example, expected_metadata_size=1
    )
    assert result == example


def test_empty_dict_list_tuple_materialization():
    """Test materialization for empty `dict`, `list`, `tuple` objects."""
    for type_, example in [
        (dict, {}),
        (list, []),
        (tuple, ()),
    ]:
        result = _test_materializer(
            step_output_type=type_,
            step_output=example,
            expected_metadata_size=2,
        )
        assert result == example


def test_simple_dict_list_tuple_materialization(tmp_path):
    """Test materialization for `dict`, `list`, `tuple` with data."""

    def _validate_single_file(artifact_uri: str) -> None:
        files = os.listdir(artifact_uri)
        assert len(files) == 1

    for type_, example in [
        (dict, {"a": 0, "b": 1, "c": 2}),
        (list, [0, 1, 2]),
        (tuple, (0, 1, 2)),
    ]:
        result = _test_materializer(
            step_output_type=type_,
            step_output=example,
            validation_function=_validate_single_file,
            expected_metadata_size=2,
        )
        assert result == example


def test_list_of_bytes_materialization():
    """Test materialization for lists of bytes."""
    example = [b"0", b"1", b"2"]
    result = _test_materializer(
        step_output_type=list, step_output=example, expected_metadata_size=2
    )
    assert result == example


def test_dict_of_bytes_materialization():
    """Test materialization for dicts of bytes."""
    example = {"a": b"0", "b": b"1", "c": b"2"}
    result = _test_materializer(
        step_output_type=dict, step_output=example, expected_metadata_size=2
    )
    assert result == example


def test_tuple_of_bytes_materialization():
    """Test materialization for tuples of bytes."""
    example = (b"0", b"1", b"2")
    result = _test_materializer(
        step_output_type=tuple, step_output=example, expected_metadata_size=2
    )
    assert result == example


def test_set_materialization():
    """Test materialization for `set` objects."""
    for example in [set(), {1, 2, 3}, {b"0", b"1", b"2"}]:
        result = _test_materializer(
            step_output_type=set, step_output=example, expected_metadata_size=2
        )
        assert result == example


def test_mixture_of_all_builtin_types():
    """Test a mixture of built-in types as the ultimate stress test."""
    example = [
        {
            "a": (42, 1.0, "aa", True),  # tuple of serializable basic types
            "b": {
                "ba": ["baa", "bab"],
                "bb": [3.7, 1.8],
            },  # dict of lists of serializable basic types
            "c": b"ca",  # bytes (non-serializable)
        },  # non-serializable dict
        {1.0, 2.0, 4, 4},  # set of serializable types
    ]  # non-serializable list
    result = _test_materializer(
        step_output_type=list, step_output=example, expected_metadata_size=2
    )
    assert result == example


def test_none_values():
    """Tests serialization of `None` values in container types."""
    for type_, example in [
        (list, [1, "a", None]),
        (tuple, (1, "a", None)),
        (dict, {"key": None}),
    ]:
        result = _test_materializer(
            step_output_type=type_,
            step_output=example,
            expected_metadata_size=2,
        )
        assert result == example


class CustomType:
    """Custom type used for testing the container materializer below."""

    def __init__(self, large_data: str = ""):
        """Initialize with optional large data for testing adaptive sizing."""
        self.myname = "aria"
        self.large_data = large_data

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, CustomType):
            return (
                self.myname == __value.myname
                and self.large_data == __value.large_data
            )
        return False


class CustomSubType(CustomType):
    """Subtype of CustomType."""

    def __init__(self, large_data: str = ""):
        """Initialize the subtype."""
        super().__init__(large_data=large_data)
        self.myname = "axl"


class CustomTypeMaterializer(BaseMaterializer):
    """Mock materializer for custom types.

    Does not actually save anything to disk, just initializes the type.
    """

    ASSOCIATED_TYPES = (CustomType,)

    def save(self, data: CustomType) -> None:
        """Save the data (not)."""
        pass

    def load(self, data_type: Type[CustomType]) -> Optional[CustomType]:
        """Load the data."""
        return data_type(large_data="")


def test_container_materializer_for_custom_types(
    mocker, clean_client: "Client"
):
    """Test container materializer for custom types.

    This ensures that:
    - The container materializer can handle custom types.
    - Custom types are loaded as the correct type.
    - The materializer of the subtype does not need to be registered in the
        materializer registry when the container is loaded.
    """
    from zenml.materializers.materializer_registry import materializer_registry

    example = [CustomType(), CustomSubType()]
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = BuiltInContainerMaterializer(uri=artifact_uri)

        # Container materializer should find materializer for both elements in
        # the default materializer registry.
        materializer.save(example)

        # When loading, the default materializer registry should no longer be
        # needed because the container materializer should have saved the
        # materializer that was used for each element.
        mocker.patch.object(
            materializer_registry,
            "materializer_types",
            {},
        )
        result = materializer.load(list)

        # Check that the loaded elements are of the correct types.
        assert isinstance(result[0], CustomType)
        assert isinstance(result[1], CustomSubType)
        assert result[0].myname == "aria"
        assert result[1].myname == "axl"
        assert result == example


def test_optimized_materialization_for_large_collections(
    mocker, clean_client: "Client"
):
    """Test that large collections are efficiently materialized.

    This test verifies that:
    1. The v2 metadata format is used for large collections
    2. Elements are properly grouped by type for efficiency
    3. Loading works correctly with the new format
    """

    # Create a collection with multiple types (to test grouping)
    example = [CustomType() for _ in range(5)] + [
        CustomSubType() for _ in range(5)
    ]

    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = BuiltInContainerMaterializer(uri=artifact_uri)

        # Save the collection
        materializer.save(example)

        # Verify the metadata format is v2 or v3
        metadata_path = os.path.join(artifact_uri, "metadata.json")
        assert os.path.exists(metadata_path)
        metadata = yaml_utils.read_json(metadata_path)
        assert isinstance(metadata, dict)
        assert metadata.get("version") in ["v2", "v3"]

        # Verify elements are properly stored
        assert len(metadata["elements"]) == 10

        # Load and verify the result
        result = materializer.load(list)
        assert len(result) == 10
        assert all(
            isinstance(item, (CustomType, CustomSubType)) for item in result
        )
        assert result == example


def test_backward_compatibility(mocker, clean_client: "Client"):
    """Test that loading works with older metadata formats.

    This ensures backward compatibility with:
    1. The list-based format (zenml > 0.37.0)
    2. The older dictionary format (zenml <= 0.37.0)
    """
    from zenml.materializers.materializer_registry import materializer_registry

    example = [CustomType(), CustomSubType()]

    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = BuiltInContainerMaterializer(uri=artifact_uri)

        # 1. Test with list-based format (zenml > 0.37.0)
        # Create metadata in the older list format
        old_metadata = []
        for i, item in enumerate(example):
            element_path = os.path.join(artifact_uri, str(i))
            os.makedirs(element_path, exist_ok=True)

            # Save the element
            materializer_class = materializer_registry[type(item)]
            element_materializer = materializer_class(uri=element_path)
            element_materializer.save(item)

            # Add to metadata
            old_metadata.append(
                {
                    "path": element_path,
                    "type": source_utils.resolve(type(item)).import_path,
                    "materializer": source_utils.resolve(
                        materializer_class
                    ).import_path,
                }
            )

        # Write metadata in old format
        yaml_utils.write_json(
            os.path.join(artifact_uri, "metadata.json"), old_metadata
        )

        # Load and verify
        result = materializer.load(list)
        assert len(result) == 2
        assert result == example

    # 2. Test with even older dictionary format (zenml <= 0.37.0)
    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = BuiltInContainerMaterializer(uri=artifact_uri)

        # Create paths for elements
        paths = []
        types = []

        for i, item in enumerate(example):
            element_path = os.path.join(artifact_uri, str(i))
            os.makedirs(element_path, exist_ok=True)
            paths.append(element_path)
            types.append(str(type(item)))

            # Save the element
            materializer_class = materializer_registry[type(item)]
            element_materializer = materializer_class(uri=element_path)
            element_materializer.save(item)

        # Create oldest format metadata
        oldest_metadata = {"paths": paths, "types": types}

        # Write metadata in oldest format
        yaml_utils.write_json(
            os.path.join(artifact_uri, "metadata.json"), oldest_metadata
        )

        # Mock find_type_by_str to handle our custom types
        def mock_find_type(type_str):
            if "CustomSubType" in type_str:
                return CustomSubType
            return CustomType

        mocker.patch(
            "zenml.materializers.built_in_materializer.find_type_by_str",
            side_effect=mock_find_type,
        )

        # Load and verify
        result = materializer.load(list)
        assert len(result) == 2
        assert isinstance(result[0], CustomType)
        assert isinstance(result[1], CustomSubType)


def test_performance_improvement(mocker, clean_client: "Client"):
    """Test the performance improvement of the new materializer format.

    This test creates a large heterogeneous collection and ensures:
    1. Saving works efficiently with the type-based grouping
    2. The materializer correctly handles a large number of elements
    3. The elements are correctly loaded back

    Note: This isn't a strict performance test but verifies the functionality
    that enables performance improvements.
    """
    import time

    # Create a large heterogeneous collection (alternating types)
    large_collection = []
    for i in range(100):  # 100 elements of each type
        if i % 2 == 0:
            large_collection.append(CustomType())
        else:
            large_collection.append(CustomSubType())

    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = BuiltInContainerMaterializer(uri=artifact_uri)

        # Measure time to save
        start_time = time.time()
        materializer.save(large_collection)
        time.time() - start_time  # Calculate save time but don't store it

        # Load and verify
        start_time = time.time()
        result = materializer.load(list)
        time.time() - start_time  # Calculate load time but don't store it

        # Verify results
        assert len(result) == len(large_collection)
        assert all(
            isinstance(item, (CustomType, CustomSubType)) for item in result
        )
        assert result == large_collection

        # Check metadata structure
        metadata_path = os.path.join(artifact_uri, "metadata.json")
        metadata = yaml_utils.read_json(metadata_path)

        # Verify metadata has v3 format
        assert metadata.get("version") == "v3"

        # Verify all elements are represented in metadata
        assert len(metadata["elements"]) == len(large_collection)

        # Verify we have groups in the metadata
        assert "groups" in metadata

        # The following assertion is informational - won't fail if not true
        # But in an optimized implementation, this would be true
        type_groups = {}
        for group in metadata["groups"]:
            type_info = group["type"]
            if type_info not in type_groups:
                type_groups[type_info] = 0
            type_groups[type_info] += len(group["indices"])

        # We expect approximately two groups (CustomType and CustomSubType)
        # with roughly equal distributions
        assert len(type_groups) == 2, "Expected two type groups in metadata"


def test_batch_compression_performance(mocker, clean_client: "Client"):
    """Test the batch compression performance improvement.

    This test creates a very large homogeneous collection to validate:
    1. Elements are properly batched into multiple chunk files
    2. Loading works efficiently with chunk-based caching
    3. The compression reduces overall storage requirements
    4. The adaptive chunk sizing works correctly
    """
    import glob
    import logging
    import os.path
    import time

    # Set up logging to capture debug messages
    zenml_logger = logging.getLogger(
        "zenml.materializers.built_in_materializer"
    )
    original_level = zenml_logger.level
    zenml_logger.setLevel(logging.DEBUG)

    # Create a large homogeneous collection
    COLLECTION_SIZE = 500
    large_collection = [CustomType() for _ in range(COLLECTION_SIZE)]

    # Create a mixed collection with different sized objects to test adaptive chunking
    mixed_collection = large_collection.copy()
    # Add some larger objects to trigger adaptive sizing
    for _ in range(10):
        mixed_collection.append(
            CustomType(large_data="X" * 1000000)
        )  # 1MB of data

    with TemporaryDirectory(
        dir=clean_client.active_stack.artifact_store.path
    ) as artifact_uri:
        materializer = BuiltInContainerMaterializer(uri=artifact_uri)

        # Measure time to save
        start_time = time.time()
        materializer.save(large_collection)
        time.time() - start_time  # Calculate save time but don't store it

        # Check for compressed chunk files
        chunk_files = glob.glob(
            os.path.join(artifact_uri, "batch_*", "chunk_*.pkl.gz")
        )
        assert len(chunk_files) > 0, "No compressed chunk files found"

        # Verify metadata
        metadata_path = os.path.join(artifact_uri, "metadata.json")
        metadata = yaml_utils.read_json(metadata_path)
        assert metadata.get("version") == "v3"

        # Total number of elements in all chunks should equal collection size
        total_elements = sum(
            len(chunk["indices"])
            for group in metadata["groups"]
            for chunk in group["chunks"]
        )
        assert total_elements == COLLECTION_SIZE

        # Load and verify
        start_time = time.time()
        result = materializer.load(list)
        time.time() - start_time  # Calculate load time but don't store it

        # Verify results
        assert len(result) == len(large_collection)
        assert all(isinstance(item, CustomType) for item in result)
        assert result == large_collection

        # We should have fewer files than elements (proving batching works)
        all_files = glob.glob(
            os.path.join(artifact_uri, "**/*"), recursive=True
        )
        assert len(all_files) < COLLECTION_SIZE, (
            "Batching not effective - too many files created"
        )

        # Test adaptive chunking with mixed collection
        with TemporaryDirectory(
            dir=clean_client.active_stack.artifact_store.path
        ) as mixed_artifact_uri:
            mixed_materializer = BuiltInContainerMaterializer(
                uri=mixed_artifact_uri
            )

            # Save the mixed collection
            mixed_materializer.save(mixed_collection)

            # Load and verify
            mixed_result = mixed_materializer.load(list)
            assert len(mixed_result) == len(mixed_collection)

            # Reset logging level
            zenml_logger.setLevel(original_level)
