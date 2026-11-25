#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Functional tests for deployment snapshot request creation."""

from typing import Annotated, Dict, List

from zenml import pipeline, step
from zenml.client import Client
from zenml.deployers.utils import (
    deployment_snapshot_request_from_source_snapshot,
)


@step(enable_cache=False)
def _echo_parameters(
    mapping: Dict[str, int], items: List[int]
) -> Annotated[Dict[str, int], "mapping"]:
    return mapping


@pipeline(enable_cache=False)
def _parametrized_pipeline(
    mapping: Dict[str, int] = {"default": 1},
    items: List[int] = [1, 2, 3],
) -> Dict[str, int]:
    return _echo_parameters(mapping=mapping, items=items)


def test_deployment_parameters_replace_dict_defaults(
    clean_client: Client,
) -> None:
    """Deployment parameters replace defaults instead of merging into them.

    A dict-valued parameter used to be merged recursively with its compiled
    default when building the invocation snapshot, leaking stale default keys
    into the value the step actually executed with. The provided value must
    replace the default wholesale, matching how the parameter behaves in a
    batch run.
    """
    run = _parametrized_pipeline()
    source_snapshot = clean_client.get_pipeline_run(run.id).snapshot

    request = deployment_snapshot_request_from_source_snapshot(
        source_snapshot=source_snapshot,
        run_name=None,
        deployment_parameters={"mapping": {"override": 5}},
    )

    step_config = next(iter(request.step_configurations.values()))
    assert step_config.config.parameters["mapping"] == {"override": 5}
    assert step_config.config.parameters["items"] == [1, 2, 3]
