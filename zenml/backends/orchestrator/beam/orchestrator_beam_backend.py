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
"""Definition of the DataFlow Orchestrator Backend"""

import os
from typing import Any, Text, Dict

from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.backends.orchestrator.beam.zenml_beam_orchestrator import \
    ZenMLBeamlDagRunner
from zenml.pipelines.utils import parse_yaml_beam_args


class OrchestratorBeamBackend(OrchestratorBaseBackend):
    """Uses Apache Beam as a Pipeline orchestrator."""

    def __init__(
            self,
            worker_machine_type: Text = 'e2-medium',
            num_workers: int = 4,
            max_num_workers: int = 10,
            disk_size_gb: int = 100,
            autoscaling_algorithm: Text = 'THROUGHPUT_BASED'):
        self.worker_machine_type = worker_machine_type
        self.num_workers = num_workers
        self.max_num_workers = max_num_workers
        self.disk_size_gb = disk_size_gb
        self.autoscaling_algorithm = autoscaling_algorithm
        super().__init__(
            worker_machine_type=worker_machine_type,
            num_workers=num_workers,
            max_num_workers=max_num_workers,
            disk_size_gb=disk_size_gb,
            autoscaling_algorithm=autoscaling_algorithm,
        )
        raise NotImplementedError('Its coming soon!')

    def run(self, config: Dict[Text, Any]):
        """
        This run function essentially calls an underlying TFX orchestrator run.
        However it is meant as a higher level abstraction with some
        opinionated decisions taken.

        Args:
            config: a ZenML config dict
        """
        beam_orchestrator_args = parse_yaml_beam_args({
            'worker_machine_type': self.worker_machine_type,
            'num_workers': self.num_workers,
            'max_num_workers': self.max_num_workers,
            'disk_size_gb': self.disk_size_gb,
            'autoscaling_algorithm': self.autoscaling_algorithm,
            'setup_file': os.path.join(os.getcwd(), 'setup.py'),
            # 'job_name': 'zenml-' + run_name,
            # 'temp_location': pipeline_temp,
            # 'staging_location': staging_location,
            # 'extra_package': gz_path,
            # 'requirements_file': req_path,
        })
        tfx_pipeline = self.get_tfx_pipeline(config)
        ZenMLBeamlDagRunner(beam_orchestrator_args).run(tfx_pipeline)
