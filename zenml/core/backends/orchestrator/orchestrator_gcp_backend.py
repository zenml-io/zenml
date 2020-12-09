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
"""Definition of the GCP VM Orchestrator Backend"""

from typing import Text

from zenml.core.backends.orchestrator.orchestrator_local_backend import \
    OrchestratorLocalBackend


class OrchestratorGCPBackend(OrchestratorLocalBackend):
    """Orchestrates pipeline in a VM.

    Every ZenML pipeline runs in backends.
    """
    BACKEND_TYPE = 'gcp'

    def __init__(self,
                 machine_type: Text = 'n1-standard-4',
                 preemptible: bool = True,
                 image: Text = None, **kwargs):
        self.image = image
        self.machine_type = machine_type
        self.preemptible = preemptible
        super().__init__(**kwargs)
        raise NotImplementedError('Its coming soon!')
