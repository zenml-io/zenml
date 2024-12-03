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
from typing import Any, Callable, Optional, Type

from zenml.client import Client
from zenml.constants import ENV_ZENML_DEBUG
from zenml.enums import VisualizationType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.materializer_registry import materializer_registry
from zenml.metadata.metadata_types import MetadataTypeTuple


def test_debug_mode_enabled_for_tests():
    """Checks that the ZENML_DEBUG is set in the tests."""
    assert os.environ[ENV_ZENML_DEBUG] == "true"


def _test_materializer(
    step_output: Any,
    step_output_type: Optional[Type[Any]] = None,
    materializer_class: Optional[Type[BaseMaterializer]] = None,
    validation_function: Optional[Callable[[str], Any]] = None,
    expected_metadata_size: Optional[int] = None,
    return_metadata: bool = False,
    assert_data_exists: bool = True,
    assert_data_type: bool = True,
    assert_visualization_exists: bool = False,
) -> Any:
    """Test whether the materialization of a given step output works.

    To do so, we first materialize the output to disk, then read it again with
    the same materializer and ensure that:
    - `materializer.save()` did write something to disk
    - `materializer.load()` did load the original data type again
    - `materializer.extract_full_metadata()` returned a dict

    Args:
        step_output: The output artifact we want to materialize.
        step_output_type: The type of the output artifact. If not provided,
            `type(step_output)` will be used.
        materializer_class: The materializer class. If not provided, we query
            the default materializer registry using `step_output_type`.
        validation_function: An optional function to call on the absolute path
            to `artifact_uri`. Can be used, e.g., to check whether a certain
            file exists or a certain number of files were written.
        expected_metadata_size: If provided, we assert that the metadata dict
            returned by `materializer.extract_full_metadata()` has this size.
        return_metadata: If True, we return the metadata dict returned by
            `materializer.extract_full_metadata()`.
        assert_data_exists: If `True`, we also assert that `materializer.save()`
            wrote something to disk.
        assert_data_type: If `True`, we also assert that `materializer.load()`
            returns an object of the same type as `step_output`.
        assert_visualization_exists: If `True`, we also assert that the result
            of `materializer.save_visualizations()` is not empty.

    Returns:
        The result of materializing `step_output` to disk and loading it again.
    """
    if step_output_type is None:
        step_output_type = type(step_output)

    if materializer_class is None:
        materializer_class = materializer_registry[step_output_type]

    artifact_store_uri = Client().active_stack.artifact_store.path
    with TemporaryDirectory(dir=artifact_store_uri) as artifact_uri:
        materializer = materializer_class(uri=artifact_uri)
        existing_files = os.listdir(artifact_uri)

        # Assert that materializer saves something to disk
        materializer.save(step_output)
        if assert_data_exists:
            new_files = os.listdir(artifact_uri)
            assert len(new_files) > len(existing_files)

        # Assert that visualization extraction returns a dict
        visualizations = materializer.save_visualizations(step_output)
        assert isinstance(visualizations, dict)
        if assert_visualization_exists:
            assert len(visualizations) > 0
        for uri, value in visualizations.items():
            assert isinstance(uri, str)
            assert "\\" not in uri
            assert isinstance(value, VisualizationType)
            assert os.path.exists(uri)

        # Assert that metadata extraction returns a dict
        metadata = materializer.extract_full_metadata(step_output)
        assert isinstance(metadata, dict)
        if expected_metadata_size is not None:
            assert len(metadata) == expected_metadata_size
        for key, value in metadata.items():
            assert isinstance(key, str)
            assert isinstance(value, MetadataTypeTuple)

        # Assert that materializer loads the data with the correct type
        loaded_data = materializer.load(step_output_type)
        if assert_data_type:
            assert isinstance(loaded_data, step_output_type)  # correct type

        # Run additional validation function if provided
        if validation_function:
            validation_function(artifact_uri)

        # Return the loaded data and metadata if requested
        if return_metadata:
            return loaded_data, metadata

        # Return the loaded data
        return loaded_data
