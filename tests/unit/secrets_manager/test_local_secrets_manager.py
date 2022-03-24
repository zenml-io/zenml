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
import pydantic
import pytest

from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema
from zenml.secrets_managers.local.local_secrets_manager import LocalSecretsManager
from zenml.utils import yaml_utils

def test_local_secrets_manager_attributes():
    """Tests that the basic attributes of the local secrets manager are set
    correctly."""
    test_secrets_manager = LocalSecretsManager()
    assert test_secrets_manager.supports_local_execution is True
    assert test_secrets_manager.supports_remote_execution is False
    assert test_secrets_manager.type == StackComponentType.SECRETS_MANAGER
    assert test_secrets_manager.flavor == SecretsManagerFlavor.LOCAL

def test_local_secrets_manager_creates_file():
    """Tests that the initialization of the local secrets manager creates
    a yaml file at the right location."""
    test_secrets_manager = LocalSecretsManager()
    
    secrets_file = test_secrets_manager.secrets_file
    assert(os.path.exists(secrets_file))

def test_local_secrets_manager_creates_key_value():
    test_secrets_manager = LocalSecretsManager()
    some_secret_name = 'test'
    some_arbitary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={"unittest" : True})

    test_secrets_manager.register_secret(some_arbitary_schema)

    secret_store_items = yaml_utils.read_yaml(test_secrets_manager.secrets_file)
    assert(secret_store_items[some_secret_name] is not None)

def test_local_secrets_manager_fetches_key_value(secret_key, secret_value):
    test_secrets_manager = LocalSecretsManager()
    some_secret_name = 'test'
    some_arbitary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={"unittest" : True})

    test_secrets_manager.register_secret(some_arbitary_schema)
    fetched_schema = test_secrets_manager.get_secret(some_secret_name)

    assert(fetched_schema.content["unittest"] == True)