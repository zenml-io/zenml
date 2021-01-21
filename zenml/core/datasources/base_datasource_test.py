#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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
import os
import zenml
from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.repo.repo import Repository

ZENML_ROOT = os.path.dirname(zenml.__path__[0])


@pytest.fixture
def cleanup_metadata_store():
    # Remove metadata db after a test to avoid test failures by duplicated
    # data sources
    metadata_db_location = os.path.join(".zenml", "local_store", "metadata.db")
    try:
        os.remove(os.path.join(ZENML_ROOT, metadata_db_location))
    except Exception as e:
        print(e)


def test_datasource_create():
    assert Repository.get_instance()
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    assert not first_ds._immutable

    # load-reload the same datasource by dummy config save
    # TODO[HIGH]: This does not do what I think it does
    second_ds = BaseDatasource.from_config(first_ds.to_config())

    assert second_ds._immutable

    # attempt at duplicate datasource creation
    with pytest.raises(Exception):
        _ = BaseDatasource(name=name)


def test_datasource_name():
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    pipeline_name = first_ds.get_pipeline_name_from_name()

    # round trip
    assert BaseDatasource.get_name_from_pipeline_name(pipeline_name) == name


def test_get_datastep():
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    # BaseStep.DATA_STEP is None
    # get_data_step is implemented, so the raised exception will NOT be a
    # NotImplementedError
    with pytest.raises(Exception):
        _ = first_ds.get_data_step()

