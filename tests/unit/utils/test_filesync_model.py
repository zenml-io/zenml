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

import pytest
from pydantic import ValidationError

from zenml.utils import filesync_model, yaml_utils

SOFTCAT1 = "aria"
SOFTCAT2 = "axel"


def test_file_sync_model_works(tmp_path):
    """Test that the file sync model works as expected.

    Create a test model, set a value, confirm that values are written to
    the config file, and that the config file is updated when the value
    is changed.
    """

    class TestModel(filesync_model.FileSyncModel):
        cat_name: str = SOFTCAT1

    config_file = str(tmp_path / "test.yaml")
    model = TestModel(config_file=config_file)
    assert model.cat_name == SOFTCAT1

    config_dict = yaml_utils.read_yaml(config_file)
    assert config_dict["cat_name"] == SOFTCAT1

    model.cat_name = SOFTCAT2
    updated_config_dict = yaml_utils.read_yaml(config_file)
    assert updated_config_dict["cat_name"] == SOFTCAT2


def test_missing_config_file():
    """Ensure the FileSyncModel raises an error if the config file is missing."""

    class TestModel(filesync_model.FileSyncModel):
        cat_name: str = SOFTCAT1

    with pytest.raises(ValidationError):
        TestModel()


def test_invalid_config_file(tmp_path):
    """Ensure the FileSyncModel raises an error if the config file is invalid."""

    class TestModel(filesync_model.FileSyncModel):
        cat_name: str = SOFTCAT1

    invalid_config_file = str(tmp_path / "test.txt")
    with open(invalid_config_file, "w") as f:
        f.write("This is not a valid YAML file")

    with pytest.raises(AttributeError):
        TestModel(config_file=invalid_config_file)


def test_concurrent_updates(tmp_path):
    """Ensure that concurrent updates to the same config file are handled correctly."""

    class TestModel(filesync_model.FileSyncModel):
        cat_name: str = SOFTCAT1

    config_file = str(tmp_path / "test.yaml")
    model1 = TestModel(config_file=config_file)
    model2 = TestModel(config_file=config_file)
    model1.cat_name = SOFTCAT2
    model2.cat_name = SOFTCAT1
    updated_config_dict = yaml_utils.read_yaml(config_file)
    assert updated_config_dict["cat_name"] == SOFTCAT1
