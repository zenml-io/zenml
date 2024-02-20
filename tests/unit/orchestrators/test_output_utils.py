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

import os

from zenml.config.step_configurations import Step
from zenml.orchestrators import output_utils


def test_output_artifact_preparation(create_step_run, local_stack):
    """Tests that the output artifact generation computes the correct artifact
    uris and creates the directories."""
    step_run = create_step_run(
        step_run_name="step_run_name",
        outputs={
            "output_name": {"materializer_source": "module.materializer_class"}
        },
    )

    step = Step(spec=step_run.spec, config=step_run.config)

    output_artifact_uris = output_utils.prepare_output_artifact_uris(
        step_run=step_run, stack=local_stack, step=step
    )
    expected_path = os.path.join(
        local_stack.artifact_store.path,
        "step_run_name",
        "output_name",
        str(step_run.id),
    )
    output_artifact_uris["output_name"] = os.path.split(
        output_artifact_uris["output_name"]
    )[0]

    assert output_artifact_uris == {"output_name": expected_path}
    assert os.path.isdir(expected_path)
