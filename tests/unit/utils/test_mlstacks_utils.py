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

from zenml.utils.mlstacks_utils import (
    _add_extra_config_to_components,
    _construct_base_stack,
    _construct_components,
    _get_component_flavor,
    get_stack_spec_file_path,
    stack_exists,
    stack_spec_exists,
)


def test_stack_exists_works(local_stack):
    """Tests that stack_exists util function works.

    Args:
        local_stack: ZenML local stack fixture.
    """
    stack_name = "aria_test_stack"
    assert not stack_exists(stack_name)
    assert stack_exists(local_stack.name)


def test_get_stack_spec_file_path_fails_when_no_stack():
    """Checks util function fails if no stack found."""
    with pytest.raises(KeyError):
        get_stack_spec_file_path("blupus_stack")


def test_get_stack_spec_file_path_works():
    """Checks util function works for default stack (always present)."""
    assert get_stack_spec_file_path("default") == ""


def test_get_stack_spec_file_path_only_works_with_full_name():
    """Checks util function only works for full name matches."""
    with pytest.raises(KeyError):
        get_stack_spec_file_path("defau")  # prefix of 'default'


def test_spec_file_exists_works_when_no_file():
    """Checks spec file search works when no file."""
    assert not stack_spec_exists("default")
    assert not stack_spec_exists("humpty-dumpty")


def test_component_flavor_parsing_works():
    """Checks component flavor parsing."""
    assert (
        _get_component_flavor(key="artifact_store", value=True, provider="aws")
        == "s3"
    )
    assert (
        _get_component_flavor(
            key="experiment_tracker", value="mlflow", provider="aws"
        )
        == "mlflow"
    )
    assert (
        _get_component_flavor(
            key="experiment_tracker", value="mlflow", provider="azure"
        )
        == "mlflow"
    )
    assert (
        _get_component_flavor(
            key="mlops_platform", value="zenml", provider="azure"
        )
        == "zenml"
    )
    assert (
        _get_component_flavor(
            key="container_registry", value=True, provider="azure"
        )
        == "azure"
    )
    assert (
        _get_component_flavor(key="artifact_store", value=True, provider="k3d")
        == "minio"
    )


def test_config_addition_works():
    """Checks ability to add extra_config values to components."""
    from mlstacks.models.component import Component

    artifact_store_name = "blupus-ka-artifact-store"
    container_registry_name = "blupus-ka-container-registry"
    bucket_name = "blupus-ka-bucket"
    repo_name = "blupus-ka-repo"
    components = [
        Component(
            name=artifact_store_name,
            component_type="artifact_store",
            component_flavor="gcp",
            provider="gcp",
        ),
        Component(
            name=container_registry_name,
            component_type="container_registry",
            component_flavor="gcp",
            provider="gcp",
        ),
    ]
    extra_config = {
        "repo_name": repo_name,
        "bucket_name": bucket_name,
        "project_id": "blupus-ka-project",  # needed for GCP
    }
    _add_extra_config_to_components(
        components=components, extra_config=extra_config
    )
    artifact_store = [
        component
        for component in components
        if component.name == artifact_store_name
    ][0]
    assert artifact_store.metadata.config["bucket_name"] == "blupus-ka-bucket"

    container_registry = [
        component
        for component in components
        if component.name == container_registry_name
    ][0]
    assert container_registry.metadata.config["repo_name"] == "blupus-ka-repo"


def test_component_construction_works_for_stack_deploy():
    """Tests zenml component construction helper works for stack deploy."""
    from mlstacks.models.component import Component

    params = {
        "provider": "aws",
        "region": "us-east-1",
        "mlops_platform": "zenml",
        "artifact_store": True,
        "extra_config": (
            "something_extra=something_blue",
            "bucket_name=bikkel",
        ),
    }
    components = _construct_components(
        params=params, zenml_component_deploy=False
    )
    assert isinstance(components, list)
    assert len(components) == 2
    zenml_component = [
        component
        for component in components
        if component.component_flavor == "zenml"
    ][0]
    assert isinstance(zenml_component, Component)
    assert zenml_component.component_flavor == "zenml"
    assert zenml_component.component_type == "mlops_platform"
    assert not zenml_component.metadata.config.get("something_extra")

    s3_bucket = [
        component
        for component in components
        if component.component_flavor == "s3"
    ][0]
    assert s3_bucket.component_flavor == "s3"
    assert s3_bucket.component_type == "artifact_store"


def test_component_construction_works_for_component_deploy():
    """Tests zenml component construction helper works for stack deploy."""
    from mlstacks.models.component import Component

    artifact_store_name = "aria-ka-artifact-store"

    params = {
        "provider": "aws",
        "region": "us-east-1",
        "artifact_store": artifact_store_name,
        "extra_config": (
            "something_extra=something_blue",
            "bucket_name=bikkel",
        ),
    }
    components = _construct_components(
        params=params, zenml_component_deploy=True
    )
    assert isinstance(components, list)
    assert len(components) == 1

    s3_bucket = [
        component
        for component in components
        if component.component_flavor == "s3"
    ][0]
    assert isinstance(s3_bucket, Component)
    assert s3_bucket.component_flavor == "s3"
    assert s3_bucket.name == artifact_store_name
    assert s3_bucket.component_type == "artifact_store"
    assert not s3_bucket.metadata.config.get("something_extra")


def test_stack_construction_works_for_stack_deploy():
    """Tests zenml component construction helper works for stack deploy."""
    from mlstacks.models.stack import Stack

    artifact_store_name = "aria-ka-artifact-store"
    params = {
        "provider": "aws",
        "region": "us-east-1",
        "stack_name": "aria",
        "artifact_store": artifact_store_name,
        "extra_config": (
            "something_extra=something_blue",
            "bucket_name=bikkel",
        ),
        "tags": ("windy_city=chicago",),
    }
    stack = _construct_base_stack(params=params)
    assert isinstance(stack, Stack)
    assert stack.name == "aria"
    assert stack.provider == "aws"
    assert stack.default_region == "us-east-1"
    assert stack.default_tags.get("windy_city") == "chicago"
    assert len(stack.components) == 0
