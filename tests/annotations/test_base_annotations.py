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

import pytest

from zenml.annotations import base_annotations


@pytest.fixture()
def base_annotation_meta_fixture():
    """Fixture for a BaseAnnotationMeta instance"""
    return base_annotations.BaseAnnotationMeta("base", (object,), {})


class TestBaseAnnotationMeta:
    """Test the BaseAnnotationMeta class"""

    def test_base_annotation_meta_instance_is_right_class(
        self, base_annotation_meta_fixture
    ):
        """Check that our instance is BaseAnnotationMeta class"""
        assert (
            base_annotation_meta_fixture.__class__
            == base_annotations.BaseAnnotationMeta
        )

    def test_base_annotation_meta_has_a___get_item_method(
        self, base_annotation_meta_fixture
    ):
        """Check that our instance has a __get_item__ method"""
        assert hasattr(base_annotation_meta_fixture, "__getitem__")

    @pytest.mark.xfail()
    def test_get_item_method_returns_instance_of_the_annotation(
        self, base_annotation_meta_fixture
    ):
        """Check that the __get_item__ method returns an instance of the annotation"""
        # TODO: [MEDIUM]
