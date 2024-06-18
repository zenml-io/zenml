#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)


class TestModelRegistryModelMetadata:
    def test_custom_attributes(self):
        metadata = ModelRegistryModelMetadata(
            zenml_version="1.0",
            zenml_workspace="test_workspace",
            custom_attr_1="foo",
            custom_attr_2="bar",
        )
        expected = {"custom_attr_1": "foo", "custom_attr_2": "bar"}
        assert metadata.custom_attributes == expected

    def test_dict(self):
        metadata = ModelRegistryModelMetadata(
            zenml_version="1.55",
            custom_attr_1="foo",
            zenml_workspace="test_workspace",
            custom_attr_2=None,
        )
        expected = {
            "zenml_version": "1.55",
            "custom_attr_1": "foo",
            "zenml_workspace": "test_workspace",
        }
        assert isinstance(metadata.model_dump()["zenml_version"], str)
        assert metadata.model_dump() == expected

    def test_exclude_unset_none(self):
        metadata = ModelRegistryModelMetadata(
            zenml_version="1.55",
            custom_attr_1="foo",
            zenml_workspace="test_workspace",
            custom_attr_2=None,
            zenml_pipeline_name=None,
        )

        # Test exclude_unset and exclude_none both False
        expected = {
            "zenml_version": "1.55",
            "zenml_run_name": None,
            "zenml_pipeline_name": None,
            "zenml_pipeline_uuid": None,
            "zenml_pipeline_run_uuid": None,
            "zenml_step_name": None,
            "zenml_workspace": "test_workspace",
            "custom_attr_1": "foo",
            "custom_attr_2": None,
        }
        assert (
            metadata.model_dump(exclude_unset=False, exclude_none=False)
            == expected
        )

        # Test exclude_unset and exclude_none both True
        expected = {
            "zenml_version": "1.55",
            "zenml_workspace": "test_workspace",
            "custom_attr_1": "foo",
        }
        assert (
            metadata.model_dump(exclude_unset=True, exclude_none=True)
            == expected
        )

        # Test exclude_unset False and exclude_none True
        expected = {
            "zenml_version": "1.55",
            "zenml_workspace": "test_workspace",
            "custom_attr_1": "foo",
        }
        assert (
            metadata.model_dump(exclude_unset=False, exclude_none=True)
            == expected
        )

        # Test exclude_unset True and exclude_none False
        expected = {
            "zenml_version": "1.55",
            "zenml_pipeline_name": None,
            "zenml_workspace": "test_workspace",
            "custom_attr_1": "foo",
            "custom_attr_2": None,
        }
        assert (
            metadata.model_dump(exclude_unset=True, exclude_none=False)
            == expected
        )
