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

import random

import pytest

from zenml.metadata import ZenMLMetadataStore
from zenml.standards.standard_keys import MLMetadataKeys
from zenml.enums import GDPComponent
from zenml.enums import PipelineStatusTypes

# we expect all queries to fail since the metadata store
# cannot be instantiated
expected_query_error = AssertionError


def test_metadata_init():
    mds1 = ZenMLMetadataStore()

    with pytest.raises(ValueError):
        _ = mds1.store


def test_to_config():
    mds1 = ZenMLMetadataStore()

    # disallow to/from_config for the base class by checking against
    # factory keys
    with pytest.raises(AssertionError):
        mds1.to_config()


def test_from_config():
    config = {MLMetadataKeys.TYPE: None,
              MLMetadataKeys.ARGS: {}}

    # throws because base MDStore is not in the factory
    with pytest.raises(AssertionError):
        _ = ZenMLMetadataStore.from_config(config)


def test_get_pipeline_status(repo):
    random_pipeline = random.choice(repo.get_pipelines())

    mds1 = ZenMLMetadataStore()

    # TODO: This returns a NotStarted enum, which may be misleading as the
    #  associated store does not even exist
    # with pytest.raises(expected_query_error):
    assert mds1.get_pipeline_status(random_pipeline) == \
           PipelineStatusTypes.NotStarted.name


def test_get_pipeline_executions(repo):
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    # if we query a different metadata store for the pipeline,
    # there should be no executions, i.e. an empty list
    with pytest.raises(expected_query_error):
        _ = mds1.get_pipeline_executions(random_pipeline)


def test_get_components_status(repo):
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    with pytest.raises(expected_query_error):
        _ = mds1.get_components_status(random_pipeline)


def test_get_artifacts_by_component(repo):
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    # pick a component guaranteed to be present
    component_name = GDPComponent.SplitGen.name

    with pytest.raises(expected_query_error):
        _ = mds1.get_artifacts_by_component(random_pipeline,
                                            component_name)


def test_get_component_execution(repo):
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    component_name = GDPComponent.SplitGen.name

    with pytest.raises(expected_query_error):
        _ = mds1.get_component_execution(random_pipeline,
                                         component_name)


def test_get_pipeline_context(repo):
    mds1 = ZenMLMetadataStore()

    random_pipeline = random.choice(repo.get_pipelines())

    with pytest.raises(expected_query_error):
        _ = mds1.get_pipeline_context(random_pipeline)


def test_get_artifacts_by_execution():
    mds1 = ZenMLMetadataStore()

    # no execution possible
    fake_id = "abcdefg"
    with pytest.raises(ValueError):
        _ = mds1.get_artifacts_by_execution(fake_id)
