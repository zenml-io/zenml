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

from zenml.constants import ENV_ZENML_DEBUG
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)


def test_handle_int_env_var():
    """Checks that the ZENML_DEBUG is set in the tests."""
    assert os.environ[ENV_ZENML_DEBUG] == "true"


def _test_materializer(
    step_output: Any,
    step_output_type: Optional[Type[Any]] = None,
    materializer_class: Optional[Type[BaseMaterializer]] = None,
    validation_function: Optional[Callable[[str], Any]] = None,
) -> Any:
    """Test whether the materialization of a given step output works.

    To do so, we first materialize the output to disk, then read it again with
    the same materializer and ensure that:
    - `materializer.save()` did write something to disk
    - `materializer.load()` did load the original data type again

    Args:
        step_output: The output artifact we want to materialize.
        step_output_type: The type of the output artifact. If not provided,
            `type(step_output)` will be used.
        materializer_class: The materializer class. If not provided, we query
            the default materializer registry using `step_output_type`.
        validation_function: An optional function to call on the absolute path
            to `artifact_uri`. Can be used, e.g., to check whether a certain
            file exists or a certain number of files were written.

    Returns:
        The result of materializing `step_output` to disk and loading it again.
    """
    if step_output_type is None:
        step_output_type = type(step_output)

    if materializer_class is None:
        materializer_class = default_materializer_registry[step_output_type]

    with TemporaryDirectory() as artifact_uri:
        materializer = materializer_class(uri=artifact_uri)
        existing_files = os.listdir(artifact_uri)
        materializer.save(step_output)
        new_files = os.listdir(artifact_uri)
        assert len(new_files) > len(existing_files)  # something was written
        loaded_data = materializer.load(step_output_type)
        assert isinstance(loaded_data, step_output_type)  # correct type
        if validation_function:
            validation_function(artifact_uri)
        return loaded_data
