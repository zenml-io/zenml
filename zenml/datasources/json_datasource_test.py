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

import os
from pathlib import Path

import zenml
from zenml.datasources.json_datasource import JSONDatasource

ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")


def test_json_commit(repo):
    data = Path(__file__).resolve() \
               .parent.parent.parent / 'tests' / 'test_data' / 'simple.json'
    ds = JSONDatasource(
        name='json_ds',
        path=str(data.resolve())
    )

    assert not ds.commits

    _id = ds.commit()

    # check that this commit made
    assert _id == ds.get_latest_commit()
