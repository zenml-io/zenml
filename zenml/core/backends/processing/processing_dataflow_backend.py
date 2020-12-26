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

from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.utils import path_utils
from zenml.utils.logger import get_logger
from zenml.utils.version import __version__

logger = get_logger(__name__)


class ProcessingDataFlowBackend(ProcessingLocalBackend):
    """
    Use this to run a ZenML pipeline on Google Dataflow.

    This backend is not implemented yet.
    """
    BACKEND_TYPE = 'dataflow'

    def __init__(
            self,
            project: Text,
            region: Text = 'europe-west1',
            job_name: Text = f'zen_{int(time.time())}',
            requirements_file: Text = None,
            machine_type: Text = 'n1-standard-4',
            num_workers: int = 4,
            max_num_workers: int = 10,
            disk_size_gb: int = 50,
            autoscaling_algorithm: Text = 'THROUGHPUT_BASED',
            **kwargs):
        self.project = project
        self.region = region
        self.job_name = job_name
        self.machine_type = machine_type
        self.num_workers = num_workers
        self.max_num_workers = max_num_workers
        self.disk_size_gb = disk_size_gb
        self.autoscaling_algorithm = autoscaling_algorithm

        # Resolve requirements.txt
        if requirements_file:
            self.requirements_file = requirements_file
        else:
            from zenml.core.repo.repo import Repository
            config_dir = Repository.get_instance().zenml_config.config_dir
            self.requirements_file = os.path.join(
                config_dir, 'requirements.txt')

        if not path_utils.file_exists(self.requirements_file):
            logger.info(f'Creating requirements file at: '
                        f'{self.requirements_file}')
            path_utils.write_file_contents(self.requirements_file,
                                           f'zenml=={__version__}')
        else:
            logger.info(
                f'requirements.txt found at {self.requirements_file}. Please '
                f'make sure that one of the requirements is zenml=='
                f'{__version__} otherwise the dataflow jobs will fail.')

        super().__init__(**kwargs)

    def get_beam_args(self,
                      pipeline_name: Text = None,
                      pipeline_root: Text = None) -> \
            Optional[List[Text]]:
        temp_location = os.path.join(pipeline_root, 'tmp', pipeline_name)
        stage_location = os.path.join(pipeline_root, 'staging', pipeline_name)

        return [
            '--runner=DataflowRunner',
            '--project=' + self.project,
            '--temp_location=' + temp_location,
            '--staging_location=' + stage_location,
            '--region=' + self.region,
            # '--job_name=' + self.job_name,
            '--num_workers=' + str(self.num_workers),
            '--max_num_workers=' + str(self.max_num_workers),

            # Specifying dependencies
            # '--extra_package=' + self.extra_package,
            # '--requirements_file=' + self.requirements_file,
            # '--setup_file=' + self.setup_file,

            # Temporary overrides of defaults.
            '--disk_size_gb=' + str(self.disk_size_gb),
            '--experiments=shuffle_mode=auto',
            '--machine_type=' + self.machine_type,
        ]
