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

# Nicholas a way to get to the root
ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")

# TODO [LOW]: These require GOOGLE_APPLICATION_CREDENTIALS in the runner so
#  we take out for now.

# from zenml.datasources import BigQueryDatasource
# def test_bq_public_commit(repo):
#     ds = BigQueryDatasource(
#         name='bq_datasource_public',
#         query_project='bigquery-public-data',
#         query_dataset='samples',
#         query_table='shakespeare',
#         gcs_location='gs://zenml_tests/bq_datasource_test',
#         dest_project='maiot-zenml',
#         query_limit=100,
#     )
#     assert not ds.commits
#
#     _id = ds.commit()
#
#     # check that this commit made
#     assert _id == ds.get_latest_commit()
#
#
# def test_bq_private_commit(repo):
#     ds = BigQueryDatasource(
#         name='bq_datasource_private',
#         query_project='maiot-zenml',
#         query_dataset='zenml_tests',
#         query_table='shakespeare',
#         gcs_location='gs://zenml_tests/bq_datasource_test',
#         query_limit=100,
#     )
#     assert not ds.commits
#
#     _id = ds.commit()
#
#     # check that this commit made
#     assert _id == ds.get_latest_commit()
