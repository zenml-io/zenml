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

from typing import Any, Optional
from uuid import UUID, uuid4

import pytest

from zenml.steps.external_artifact import ExternalArtifact


@pytest.mark.parametrize(
    argnames="value,id,pipeline_name,artifact_name,exception_start",
    argvalues=[
        [1, None, None, None, ""],
        [None, uuid4(), None, None, ""],
        [None, None, "foo", "bar", ""],
        [None, None, None, None, "Either a value,"],
        [1, uuid4(), None, None, "Only a value,"],
        [None, uuid4(), "foo", "bar", "Only a value,"],
        [1, None, "foo", "bar", "Only a value,"],
        [None, None, "foo", None, "`pipeline_name` and `artifact_name`"],
        [None, None, None, "bar", "`pipeline_name` and `artifact_name`"],
    ],
    ids=[
        "good_by_value",
        "good_by_id",
        "good_by_pipeline_artifact",
        "bad_all_none",
        "bad_id_and_value",
        "bad_id_and_pipeline_artifact",
        "bad_value_and_pipeline_artifact",
        "bad_only_pipeline",
        "bad_only_artifact",
    ],
)
def test_external_artifact_init(
    value: Optional[Any],
    id: Optional[UUID],
    pipeline_name: Optional[str],
    artifact_name: Optional[str],
    exception_start: str,
):
    """Tests that initialization logic of `ExternalArtifact` works expectedly."""
    if exception_start:
        with pytest.raises(ValueError, match=exception_start):
            ExternalArtifact(
                value=value,
                id=id,
                pipeline_name=pipeline_name,
                artifact_name=artifact_name,
            )
    else:
        ExternalArtifact(
            value=value,
            id=id,
            pipeline_name=pipeline_name,
            artifact_name=artifact_name,
        )
