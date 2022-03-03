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

from typing import TYPE_CHECKING, Any, List

import sagemaker

from zenml.enums import StackComponentType, TrainingResourceFlavor
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.training_resources import BaseTrainingResource

if TYPE_CHECKING:
    pass


@register_stack_component_class(
    component_type=StackComponentType.TRAINING_RESOURCE,
    component_flavor=TrainingResourceFlavor.SAGEMAKER,
)
class SagemakerTrainingResource(BaseTrainingResource):
    """Training resource to run a step on Sagemaker."""

    supports_local_execution = True
    supports_remote_execution = True

    @property
    def flavor(self) -> TrainingResourceFlavor:
        """The training resource flavor."""
        return TrainingResourceFlavor.SAGEMAKER

    def launch(
        self, pipeline_name: str, run_name: str, entrypoint_command: List[str]
    ) -> Any:
        """Launches a step on the training resource."""

        role = sagemaker.get_execution_role()

        sess = sagemaker.Session()
        account = sess.boto_session.client("sts").get_caller_identity()[
            "Account"
        ]
        region = sess.boto_session.region_name

        image_name = "zenml-sagemaker"
        image = f"{account}.dkr.ecr.{region}.amazonaws.com/{image_name}:latest"

        # build and push the docker image
        # should contain an entrypoint that runs the training

        # sagemaker mounts the inputs at /opt/ml/input/data/
        # write outputs to /opt/ml/model/, sagemaker will copy them to a specified S3 bucket

        estimator = sagemaker.estimator.Estimator(
            image,
            role,
            1,  # instance count
            "ml.c4.2xlarge",
            output_path="s3://zenfiles/whatever",
            sagemaker_session=sess,
        )

        # synchronous, waits until the job is finished
        estimator.fit()
