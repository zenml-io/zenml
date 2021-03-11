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
"""Definition of the Kubeflow Orchestrator Backend"""

from typing import Text

from tfx.orchestration import pipeline

from zenml.backends.orchestrator import OrchestratorBaseBackend


class OrchestratorKubeFlowBackend(OrchestratorBaseBackend):
    """
    Runs a ZenML pipeline on a Kubeflow cluster.

    This backend is not implemented yet.
    """

    def __init__(self, image: Text = None, **kwargs):
        self.image = image
        super().__init__(**kwargs)
        raise NotImplementedError('Its coming soon!')

    def run(self, tfx_pipeline: pipeline.Pipeline):
        raise NotImplementedError('Coming soon!')
