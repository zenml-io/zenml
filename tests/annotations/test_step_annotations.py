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

from zenml.annotations import base_annotations, step_annotations


def test_step_is_subclass_of_base_annotation():
    """Check Step is a subclass of BaseAnnotation"""
    assert issubclass(step_annotations.Step, base_annotations.BaseAnnotation)


def test_step_has_valid_types_property():
    """Check that Step has VALID_TYPES property"""
    assert hasattr(step_annotations.Step, "VALID_TYPES")


def test_step_is_named_step():
    """Check that the Step annotation is named Step"""
    assert step_annotations.Step.__name__ == "Step"
