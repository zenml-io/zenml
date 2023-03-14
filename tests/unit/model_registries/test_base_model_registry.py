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
            custom_attr_1="foo",
            custom_attr_2="bar",
        )
        expected = {"custom_attr_1": "foo", "custom_attr_2": "bar"}
        assert metadata.custom_attributes == expected

    def test_dict(self):
        metadata = ModelRegistryModelMetadata(
            zenml_version="1.0",
            custom_attr_1="foo",
            custom_attr_2=None,
        )
        expected = {"zenml_version": "1.0", "custom_attr_1": "foo"}
        assert metadata.dict() == expected
