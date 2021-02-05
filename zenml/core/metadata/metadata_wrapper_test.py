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
import random
from zenml.core.repo.repo import Repository
from zenml.utils.enums import GDPComponent
from zenml.core.metadata.metadata_wrapper import ZenMLMetadataStore

ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipelines_dir = os.path.join(TEST_ROOT, "test_pipelines")
repo: Repository = Repository.get_instance()
repo.zenml_config.set_pipelines_dir(pipelines_dir)

# we expect all queries to fail since the metadata store
# cannot be instantiated
expected_query_error = ValueError


def test_metadata_init():

    mds1 = ZenMLMetadataStore()

    with pytest.raises(expected_query_error):
        _ = mds1.store


def test_to_from_config(equal_md_stores):
    mds1 = ZenMLMetadataStore()

    mds2 = ZenMLMetadataStore.from_config(mds1.to_config())

    # TODO: This fails because from_config throws (base store is
    #  not in the factory)
    assert equal_md_stores(mds1, mds2, loaded=True)


def test_get_pipeline_status(run_test_pipelines):
    run_test_pipelines()
    random_pipeline = random.choice(repo.get_pipelines())

    mds1 = ZenMLMetadataStore()

    # TODO: This returns a NotStarted enum, which may be misleading as the
    #  associated store does not even exist
    with pytest.raises(expected_query_error):
        _ = mds1.get_pipeline_status(random_pipeline)


def test_get_pipeline_executions():
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    # if we query a different metadata store for the pipeline,
    # there should be no executions, i.e. an empty list
    with pytest.raises(expected_query_error):
        _ = mds1.get_pipeline_executions(random_pipeline)


def test_get_components_status():
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    with pytest.raises(expected_query_error):
        _ = mds1.get_components_status(random_pipeline)


def test_get_artifacts_by_component():
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    # pick a component guaranteed to be present
    component_name = GDPComponent.SplitGen.name

    with pytest.raises(expected_query_error):
        _ = mds1.get_artifacts_by_component(random_pipeline,
                                            component_name)


def test_get_component_execution():
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    component_name = GDPComponent.SplitGen.name

    with pytest.raises(expected_query_error):
        _ = mds1.get_component_execution(random_pipeline,
                                         component_name)


def test_get_pipeline_context():
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    with pytest.raises(expected_query_error):
        _ = mds1.get_pipeline_context(random_pipeline)


def test_get_artifacts_by_execution():
    mds1 = ZenMLMetadataStore()

    # no execution possible
    fake_id = "abcdefg"
    with pytest.raises(expected_query_error):
        _ = mds1.get_artifacts_by_execution(fake_id)
