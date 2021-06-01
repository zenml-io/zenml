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

from zenml.enums import GDPComponent
from zenml.enums import PipelineStatusTypes
from zenml.metadata import ZenMLMetadataStore
from zenml.pipelines import TrainingPipeline
from zenml.standards.standard_keys import MLMetadataKeys

# we expect all queries to fail since the metadata store
# cannot be instantiated
expected_query_error = AssertionError


def test_metadata_init(repo):
    mds = repo.get_default_metadata_store()
    _ = mds.store


def test_to_config(repo):
    mds = repo.get_default_metadata_store()
    mds.to_config()


def test_from_config():
    config = {MLMetadataKeys.TYPE: None,
              MLMetadataKeys.ARGS: {}}

    # throws because base MDStore is not in the factory
    with pytest.raises(AssertionError):
        _ = ZenMLMetadataStore.from_config(config)


def test_get_pipeline_status(repo):
    random_pipeline = random.choice(repo.get_pipelines())

    mds = repo.get_default_metadata_store()

    assert mds.get_pipeline_status(random_pipeline) == \
           PipelineStatusTypes.Succeeded.name


def test_get_pipeline_executions(repo):
    mds = repo.get_default_metadata_store()

    random_pipeline = random.choice(repo.get_pipelines())

    _ = mds.get_pipeline_executions(random_pipeline)


def test_get_components_status(repo):
    mds = repo.get_default_metadata_store()

    random_pipeline = random.choice(repo.get_pipelines())

    mds.get_components_status(random_pipeline)


def test_get_artifacts_by_component(repo):
    mds = repo.get_default_metadata_store()

    random_pipeline = repo.get_pipelines_by_type(
        TrainingPipeline.PIPELINE_TYPE)[0]

    # pick a component guaranteed to be present
    component_name = GDPComponent.SplitGen.name

    artifacts = mds.get_artifacts_by_component(random_pipeline, component_name)

    assert len(artifacts) >= 1


def test_get_pipeline_context(repo):
    mds = repo.get_default_metadata_store()

    random_pipeline = random.choice(repo.get_pipelines())

    mds.get_pipeline_context(random_pipeline)
