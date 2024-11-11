# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import Any, Dict

from zenml import get_step_context, log_model_metadata, step


@step(enable_cache=False)
def log_metadata_from_step_artifact(
    step_name: str,
    artifact_name: str,
) -> None:
    """Log metadata to the model from saved artifact.

    Args:
        step_name: The name of the step.
        artifact_name: The name of the artifact.
    """

    context = get_step_context()
    metadata_dict: Dict[str, Any] = (
        context.pipeline_run.steps[step_name].outputs[artifact_name][0].load()
    )

    metadata = {artifact_name: metadata_dict}

    log_model_metadata(metadata)
