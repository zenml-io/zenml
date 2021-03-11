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
"""Definition of the DataFlow Processing Backend"""

import os
import time
from typing import Optional, List, Text

from zenml.backends.processing import ProcessingBaseBackend
from zenml.utils import requirement_utils
from zenml.constants import ZENML_DATAFLOW_IMAGE_NAME
from zenml.logger import get_logger

requirement_utils.check_integration(requirement_utils.GCP_INTEGRATION)

logger = get_logger(__name__)


class ProcessingDataFlowBackend(ProcessingBaseBackend):
    """
    Use this to run a ZenML pipeline on Google Dataflow.

    This backend utilizes the beam v2 runner to run a custom docker image on
    the Dataflow job.
    """

    def __init__(
            self,
            project: Text,
            staging_location: Text = None,
            temp_location: Text = None,
            region: Text = 'europe-west1',
            job_name: Text = f'zen_{int(time.time())}',
            image: Text = ZENML_DATAFLOW_IMAGE_NAME,
            machine_type: Text = 'n1-standard-4',
            num_workers: int = 4,
            max_num_workers: int = 10,
            disk_size_gb: int = 50,
            autoscaling_algorithm: Text = 'THROUGHPUT_BASED'):
        """
        Adding this Backend will cause all 'Beam'-supported Steps in the
        pipeline to run on Google Dataflow.

        Args:
            project: GCP project to launch dataflow job.
            region: GCP region to launch dataflow job.
            job_name: Name of dataflow job.
            image: Docker Image to use. Must inherit from the beam base image.
            machine_type: Type of machine to run workload.
            num_workers: Number of workers on that machine.
            max_num_workers: Max number of workers in the workload.
            disk_size_gb: Disk size per worker.
            autoscaling_algorithm: Autoscaling algorithm to use.
            **kwargs:
        """
        self.project = project
        self.region = region
        self.job_name = job_name
        self.machine_type = machine_type
        self.num_workers = num_workers
        self.max_num_workers = max_num_workers
        self.disk_size_gb = disk_size_gb
        self.autoscaling_algorithm = autoscaling_algorithm
        self.image = image
        self.staging_location = staging_location
        self.temp_location = temp_location

        # staging and temp can be the same if one is specified
        if staging_location is not None and temp_location is None:
            self.temp_location = self.staging_location

        super().__init__(
            project=project,
            staging_location=staging_location,
            temp_location=temp_location,
            region=region,
            job_name=job_name,
            image=image,
            machine_type=machine_type,
            num_workers=num_workers,
            max_num_workers=max_num_workers,
            disk_size_gb=disk_size_gb,
            autoscaling_algorithm=autoscaling_algorithm,
        )

    def get_beam_args(self,
                      pipeline_name: Text = None,
                      pipeline_root: Text = None) -> \
            Optional[List[Text]]:
        if self.temp_location is None:
            self.temp_location = os.path.join(
                pipeline_root, 'tmp', pipeline_name)
        if self.staging_location is None:
            self.staging_location = os.path.join(
                pipeline_root, 'staging', pipeline_name)

        return [
            '--runner=dataflow',
            '--project=' + self.project,
            '--temp_location=' + self.temp_location,
            '--staging_location=' + self.staging_location,
            '--region=' + self.region,
            # '--job_name=' + self.job_name,
            '--num_workers=' + str(self.num_workers),
            '--max_num_workers=' + str(self.max_num_workers),

            # Temporary overrides of defaults.
            '--disk_size_gb=' + str(self.disk_size_gb),
            '--experiments=shuffle_mode=auto',
            '--machine_type=' + self.machine_type,

            # Using docker
            '--experiment=use_runner_v2',
            f'--worker_harness_container_image={self.image}'
        ]
