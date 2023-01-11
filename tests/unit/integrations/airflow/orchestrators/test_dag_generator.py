#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from zenml.integrations.airflow.orchestrators import dag_generator


def test_dag_generator_constants():
    """Tests that the constants redefined in the dag generator file match the actual ZenML constants."""
    from zenml.constants import (
        ENV_ZENML_LOCAL_STORES_PATH as ORIGINAL_ENV_ZENML_LOCAL_STORES_PATH,
    )

    assert (
        ORIGINAL_ENV_ZENML_LOCAL_STORES_PATH
        == dag_generator.ENV_ZENML_LOCAL_STORES_PATH
    )


def test_class_importing_by_path():
    """Tests importing a class by path."""
    from zenml.client import Client

    imported_class = dag_generator.import_class_by_path("zenml.client.Client")
    assert Client is imported_class

    with pytest.raises(ModuleNotFoundError):
        dag_generator.import_class_by_path("zenml.not_a_module.Class")

    with pytest.raises(AttributeError):
        dag_generator.import_class_by_path("zenml.client.NotAClass")
