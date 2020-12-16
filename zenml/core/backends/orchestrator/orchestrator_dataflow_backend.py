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

from typing import Text

from zenml.core.backends.orchestrator.orchestrator_local_backend import \
    OrchestratorLocalBackend


class OrchestratorDataFlowBackend(OrchestratorLocalBackend):
    """Uses Google DataFlow as an orchestrator.

    Every ZenML pipeline runs in backends.
    """
    BACKEND_TYPE = 'dataflow'

    def __init__(
            self, worker_machine_type: Text = 'n1-standard-4',
            num_workers: int = 4,
            max_num_workers: int = 10,
            disk_size_gb: int = 100,
            autoscaling_algorithm: Text = 'THROUGHPUT_BASED',
            **kwargs):
        self.worker_machine_type = worker_machine_type
        self.num_workers = num_workers
        self.max_num_workers = max_num_workers
        self.disk_size_gb = disk_size_gb
        self.autoscaling_algorithm = autoscaling_algorithm
        super().__init__(**kwargs)
