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
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.exceptions import StepContextError
from zenml.materializers import BuiltInMaterializer
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.repository import Repository
from zenml.steps import StepContext


def test_initialize_step_context_with_mismatched_keys():
    """Tests that initializing a step context with mismatched keys for
    materializers and artifacts raises an Exception."""

    materializers = {"some_output_name": BaseMaterializer}
    artifacts = {"some_different_output_name": BaseArtifact()}

    with pytest.raises(StepContextError):
        StepContext(
            step_name="",
            output_materializers=materializers,
            output_artifacts=artifacts,
        )


def test_initialize_step_context_with_matching_keys():
    """Tests that initializing a step context with matching keys for
    materializers and artifacts works."""

    materializers = {"some_output_name": BaseMaterializer}
    artifacts = {"some_output_name": BaseArtifact()}

    with does_not_raise():
        StepContext(
            step_name="",
            output_materializers=materializers,
            output_artifacts=artifacts,
        )


def test_get_step_context_output_for_step_with_no_outputs(
    step_context_with_no_output,
):
    """Tests that getting the artifact uri or materializer for a step context
    with no outputs raises an exception."""

    with pytest.raises(StepContextError):
        step_context_with_no_output.get_output_artifact_uri()

    with pytest.raises(StepContextError):
        step_context_with_no_output.get_output_materializer()


def test_get_step_context_output_for_step_with_one_output(
    step_context_with_single_output,
):
    """Tests that getting the artifact uri or materializer for a step context
    with a single output does NOT raise an exception."""

    with does_not_raise():
        step_context_with_single_output.get_output_artifact_uri()
        step_context_with_single_output.get_output_materializer()


def test_get_step_context_output_for_step_with_multiple_outputs(
    step_context_with_two_outputs,
):
    """Tests that getting the artifact uri or materializer for a step context
    with multiple outputs raises an exception."""

    with pytest.raises(StepContextError):
        step_context_with_two_outputs.get_output_artifact_uri()

    with pytest.raises(StepContextError):
        step_context_with_two_outputs.get_output_materializer()


def test_get_step_context_output_for_non_existent_output_key(
    step_context_with_single_output,
):
    """Tests that getting the artifact uri or materializer for a non-existent
    output raises an exception."""

    with pytest.raises(StepContextError):
        step_context_with_single_output.get_output_artifact_uri(
            "some_non_existent_output_name"
        )

    with pytest.raises(StepContextError):
        step_context_with_single_output.get_output_materializer(
            "some_non_existent_output_name"
        )


def test_get_step_context_output_for_non_existing_output_key(
    step_context_with_two_outputs,
):
    """Tests that getting the artifact uri or materializer for an existing
    output does NOT raise an exception."""

    with does_not_raise():
        step_context_with_two_outputs.get_output_artifact_uri("output_1")
        step_context_with_two_outputs.get_output_materializer("output_2")


def test_step_context_returns_instance_of_custom_materializer_class(
    step_context_with_single_output,
):
    """Tests that the returned materializer is an instance of the custom
    materializer class if it was passed."""

    materializer = step_context_with_single_output.get_output_materializer(
        custom_materializer_class=BuiltInMaterializer
    )
    assert isinstance(materializer, BuiltInMaterializer)


def test_step_context_returns_metadata_store_of_active_stack():
    """Tests that the step context returns the metadata store of the active
    stack."""
    context = StepContext(
        step_name="some_step_name", output_materializers={}, output_artifacts={}
    )
    assert Repository().active_stack.metadata_store == context.metadata_store
