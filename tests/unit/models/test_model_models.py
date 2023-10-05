#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from tests.unit.steps.test_external_artifact import MockZenmlClient
from zenml.enums import ModelStages
from zenml.models.model_base_model import ModelConfigModel
from zenml.models.model_models import (
    ModelResponseModel,
    ModelVersionResponseModel,
)

ARTIFACT_IDS = [uuid4(), uuid4()]


@pytest.mark.parametrize(
    "artifact_object_ids,query_name,query_pipe,query_step,query_version,expected",
    (
        (
            {"foo::bar::artifact": {"1": ARTIFACT_IDS[0]}},
            "artifact",
            None,
            None,
            None,
            ARTIFACT_IDS[0],
        ),
        (
            {
                "bar::bar::artifact": {"1": ARTIFACT_IDS[0]},
                "foo::foo::artifact": {"1": ARTIFACT_IDS[1]},
            },
            "artifact",
            None,
            None,
            None,
            "RuntimeError",
        ),
        (
            {
                "bar::bar::artifact": {"1": ARTIFACT_IDS[0]},
                "foo::foo::artifact": {"1": ARTIFACT_IDS[1]},
            },
            "artifact",
            None,
            "bar",
            None,
            ARTIFACT_IDS[0],
        ),
        (
            {
                "bar::bar::artifact": {"1": ARTIFACT_IDS[0]},
                "foo::foo::artifact": {"1": ARTIFACT_IDS[1]},
            },
            "artifact",
            "bar",
            None,
            None,
            ARTIFACT_IDS[0],
        ),
        (
            {
                "bar::bar::artifact": {"1": ARTIFACT_IDS[0]},
                "foo::foo::artifact": {"1": ARTIFACT_IDS[1]},
            },
            "artifact",
            "foo",
            "foo",
            None,
            ARTIFACT_IDS[1],
        ),
        (
            {
                "foo::bar::artifact": {
                    "1": ARTIFACT_IDS[0],
                    "2": ARTIFACT_IDS[1],
                }
            },
            "artifact",
            None,
            None,
            None,
            ARTIFACT_IDS[1],
        ),
        (
            {
                "foo::bar::artifact": {
                    "1": ARTIFACT_IDS[0],
                    "2": ARTIFACT_IDS[1],
                }
            },
            "artifact",
            None,
            None,
            "1",
            ARTIFACT_IDS[0],
        ),
        (
            {},
            "artifact",
            None,
            "bar",
            None,
            None,
        ),
    ),
    ids=[
        "No collision",
        "Collision - only name",
        "Collision resolved - name+step",
        "Collision resolved - name+pipeline",
        "Collision resolved - name+step+pipeline",
        "Latest version",
        "Specific version",
        "Not found",
    ],
)
def test_getters(
    artifact_object_ids,
    query_name,
    query_pipe,
    query_step,
    query_version,
    expected,
    sample_workspace_model,
):
    """Test that the getters work as expected."""
    with patch.dict(
        "sys.modules",
        {
            "zenml.client": MockZenmlClient,
        },
    ):
        model = ModelResponseModel(
            id=uuid4(),
            name="model",
            workspace=sample_workspace_model,
            created=datetime.now(),
            updated=datetime.now(),
        )
        mv = ModelVersionResponseModel(
            name="foo",
            model=model,
            workspace=sample_workspace_model,
            created=datetime.now(),
            updated=datetime.now(),
            id=uuid4(),
            artifact_object_ids=artifact_object_ids,
        )
        if expected != "RuntimeError":
            got = mv.get_artifact_object(
                name=query_name,
                pipeline_name=query_pipe,
                step_name=query_step,
                version=query_version,
            )
            if got is not None:
                assert got.id == expected
            else:
                assert expected is None
        else:
            with pytest.raises(RuntimeError):
                mv.get_artifact_object(
                    name=query_name,
                    pipeline_name=query_pipe,
                    step_name=query_step,
                    version=query_version,
                )


@pytest.mark.parametrize(
    "version_name,version_number,create_new_model_version,delete_new_version_on_failure,logger",
    [
        [None, None, False, False, "warning"],
        ["bar", 1, False, True, "warning"],
        [None, None, True, False, "info"],
        ["staging", None, False, False, "info"],
    ],
    ids=[
        "No new version, but recovery",
        "Version number over version name",
        "Default running version",
        "Pick model by text stage",
    ],
)
def test_init_warns(
    version_name,
    version_number,
    create_new_model_version,
    delete_new_version_on_failure,
    logger,
):
    with patch(f"zenml.models.model_base_model.logger.{logger}") as logger:
        ModelConfigModel(
            name="foo",
            version_name=version_name,
            version_number=version_number,
            create_new_model_version=create_new_model_version,
            delete_new_version_on_failure=delete_new_version_on_failure,
        )
        logger.assert_called_once()


@pytest.mark.parametrize(
    "version_name,version_number,create_new_model_version",
    [
        [None, 1, True],
        [ModelStages.PRODUCTION, None, True],
    ],
    ids=[
        "Version number and new version request",
        "Version name as stage and new version request",
    ],
)
def test_init_raises(
    version_name,
    version_number,
    create_new_model_version,
):
    with pytest.raises(ValueError):
        ModelConfigModel(
            name="foo",
            version_name=version_name,
            version_number=version_number,
            create_new_model_version=create_new_model_version,
        )
