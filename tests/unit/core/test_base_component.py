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
from uuid import uuid4

from zenml.core.base_component import BaseComponent
from zenml.utils.yaml_utils import read_json, write_json


def test_base_component_detects_superfluous_arguments(tmp_path):
    """Tests that the base component correctly detects arguments that are
    not defined in the class."""
    component = BaseComponent(
        some_random_key=None, uuid=uuid4(), serialization_dir=str(tmp_path)
    )
    assert "some_random_key" in component._superfluous_options
    assert "uuid" not in component._superfluous_options


def test_base_component_creates_backup_file_if_schema_changes(tmp_path):
    """Tests that a base component creates a backup file if the json file
    schema is different than the current class definition."""
    uuid = uuid4()
    component = BaseComponent(uuid=uuid, serialization_dir=str(tmp_path))
    config_path = component.get_serialization_full_path()
    # write a config file with a superfluous key
    write_json(config_path, {"uuid": str(uuid), "superfluous": 0})

    # instantiate new BaseComponent which should create a backup file
    BaseComponent(uuid=uuid, serialization_dir=str(tmp_path))

    # config dict should be with new schema, so no superfluous options
    config_dict = read_json(config_path)
    assert config_dict["uuid"] == str(uuid)
    assert "superfluous" not in config_dict

    # backup file should contain both the uuid and superfluous options
    backup_path = config_path + ".backup"
    assert os.path.exists(backup_path)
    backup_dict = read_json(backup_path)
    assert backup_dict["superfluous"] == 0
    assert backup_dict["uuid"] == str(uuid)
