# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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


from zenml import get_step_context, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def promote_model_version_in_model_control_plane(promotion_decision: bool):
    """Step to promote current model version to target environment in Model Control Plane.

    Args:
        promotion_decision: Whether to promote current model version to target environment
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    if promotion_decision:
        target_env = (
            get_step_context().pipeline_run.config.extra["target_env"].lower()
        )
        model_version = get_step_context().model_config._get_model_version()
        model_version.set_stage(stage=target_env, force=True)
        logger.info(f"Current model version was promoted to '{target_env}'.")
    else:
        logger.info("Current model version was not promoted.")
    ### YOUR CODE ENDS HERE ###
