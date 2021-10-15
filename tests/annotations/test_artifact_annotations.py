#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from zenml.annotations import artifact_annotations, base_annotations


def test_input_is_subclass_of_base_annotation():
    """Check Input is a subclass of BaseAnnotation"""
    assert issubclass(
        artifact_annotations.Input, base_annotations.BaseAnnotation
    )


def test_output_is_subclass_of_base_annotation():
    """Check Output is a subclass of BaseAnnotation"""
    assert issubclass(
        artifact_annotations.Output, base_annotations.BaseAnnotation
    )


def test_input_and_output_have_valid_types_property():
    """Check that Input and Output have VALID_TYPES properties"""
    assert hasattr(artifact_annotations.Input, "VALID_TYPES")
    assert hasattr(artifact_annotations.Output, "VALID_TYPES")


def test_input_is_named_input():
    """Check that the Input annotation is named Input"""
    assert artifact_annotations.Input.__name__ == "Input"


def test_output_is_named_output():
    """Check that the Output annotation is named Output"""
    assert artifact_annotations.Output.__name__ == "Output"
