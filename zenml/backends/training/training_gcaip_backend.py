#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
"""Definition of the GCAIP Training Backend"""

import time
from typing import Text

from tfx.dsl.components.base import executor_spec
from tfx.extensions.google_cloud_ai_platform.trainer import \
    executor as ai_platform_trainer_executor
from tfx.extensions.google_cloud_ai_platform.trainer.executor \
    import TRAINING_ARGS_KEY, JOB_ID_KEY

from zenml.backends.training import TrainingBaseBackend
from zenml.pipelines.utils import sanitize_name_for_ai_platform
from zenml.utils import requirement_utils
from zenml.constants import ZENML_TRAINER_IMAGE_NAME
from zenml.enums import GCPGPUTypes
from zenml.logger import get_logger

requirement_utils.check_integration(requirement_utils.GCP_INTEGRATION)

logger = get_logger(__name__)


class SingleGPUTrainingGCAIPBackend(TrainingBaseBackend):
    """
    Runs a TrainerStep on Google Cloud AI Platform.

    A training backend can be used to efficiently train a machine learning
    model on large amounts of data. This triggers a Training job on the Google
    Cloud AI Platform service: https://cloud.google.com/ai-platform.

    This backend is meant for a training job with a single GPU only. The user
    has a choice of three GPUs, specified in the GCPGPUTypes Enum.
    """

    def __init__(
            self,
            project: Text,
            job_dir: Text,
            gpu_type: Text = GCPGPUTypes.K80.name,
            machine_type: Text = 'n1-standard-4',
            image: Text = ZENML_TRAINER_IMAGE_NAME,
            job_name: Text = f'train_{int(time.time())}',
            region: Text = 'europe-west1',
            python_version: Text = '3.7',
            max_running_time: int = 7200):
        """
        An opinionated wrapper around a GCAIP training job.

        Args:
            project: The GCP project in which to run the job.
            job_dir: A bucket where to store some metadata while training.
            gpu_type: The type of gpu.
            machine_type: The type of machine to use. This must conform to
            the GCP compatability matrix with the gpu_type. See details
            here: https://cloud.google.com/ai-platform/training/docs/using
            -gpus#compute-engine-machine-types-with-gpu
            image: The Docker image with which to run the job.
            job_name: The name of the job.
            region: The GCP region to run the job in.
            python_version: The Python version for the job.
            max_running_time: The maximum running time of the job in seconds.
            **kwargs:
        """
        if gpu_type not in GCPGPUTypes.__members__.keys():
            raise AssertionError(f'gpu_type must be one of: '
                                 f'{list(GCPGPUTypes.__members__.keys())}')
        self.project = project
        self.job_dir = job_dir
        self.gpu_type = gpu_type
        self.machine_type = machine_type
        self.image = image
        self.job_name = job_name
        self.region = region
        self.python_version = python_version
        self.max_running_time = max_running_time
        super().__init__(
            project=project,
            job_dir=job_dir,
            gpu_type=gpu_type,
            machine_type=machine_type,
            image=image,
            job_name=job_name,
            region=region,
            python_version=python_version,
            max_running_time=max_running_time,
        )

    def get_executor_spec(self):
        return executor_spec.ExecutorClassSpec(
            ai_platform_trainer_executor.GenericExecutor)

    def get_custom_config(self):
        train_args = {
            'project': self.project,
            'region': self.region,
            'jobDir': self.job_dir,
            'masterConfig': {
                'imageUri': self.image,
                'acceleratorConfig': {
                    'count': 1,  # always 1 to avoid complications
                    'type': f'NVIDIA_TESLA_{self.gpu_type}'
                }
            },
            'masterType': self.machine_type,
            'scaleTier': 'CUSTOM',
            'pythonVersion': self.python_version,
            'scheduling': {'maxRunningTime': f'{self.max_running_time}s'},
        }
        logger.debug(f'Configuring GCAIP Trainer job {self.job_name} '
                     f'with args: {train_args}')
        logger.info(f'Launching GCAIP Trainer job {self.job_name}')
        return {
            TRAINING_ARGS_KEY: train_args,
            JOB_ID_KEY: sanitize_name_for_ai_platform(
                self.job_name)
        }
