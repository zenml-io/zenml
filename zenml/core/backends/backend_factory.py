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
"""Factory to register backend classes to backends"""

from zenml.core.backends.orchestrator.beam.orchestrator_beam_backend import \
    OrchestratorBeamBackend
from zenml.core.backends.orchestrator.gcp.orchestrator_gcp_backend import \
    OrchestratorGCPBackend
from zenml.core.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend \
    import OrchestratorKubeFlowBackend
from zenml.core.backends.orchestrator.kubernetes \
    .orchestrator_kubernetes_backend import \
    OrchestratorKubernetesBackend
from zenml.core.backends.orchestrator.local.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_dataflow_backend import \
    ProcessingDataFlowBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.core.backends.processing.processing_spark_backend import \
    ProcessingSparkBackend
from zenml.core.backends.training.training_gcaip_backend import \
    TrainingGCAIPBackend
from zenml.core.backends.training.training_local_backend import \
    TrainingLocalBackend


class BackendFactory:
    """Definition of BackendFactory to track all backends in ZenML.

    All backends (including custom backends) are to be registered here.
    """

    def __init__(self):
        self.backends = {}

    def get_backends(self):
        return self.backends

    def register_backend(self, backend):
        if backend.BACKEND_KEY not in self.backends:
            self.backends[backend.BACKEND_KEY] = {}
        self.backends[backend.BACKEND_KEY][backend.BACKEND_TYPE] = backend

    def get_backend(self, key, type_):
        return self.backends[key][type_]


# Register the injections into the factory
backend_factory = BackendFactory()
backend_factory.register_backend(OrchestratorBeamBackend)
backend_factory.register_backend(OrchestratorLocalBackend)
backend_factory.register_backend(OrchestratorGCPBackend)
backend_factory.register_backend(OrchestratorKubeFlowBackend)
backend_factory.register_backend(OrchestratorKubernetesBackend)
backend_factory.register_backend(ProcessingDataFlowBackend)
backend_factory.register_backend(ProcessingLocalBackend)
backend_factory.register_backend(ProcessingSparkBackend)
backend_factory.register_backend(TrainingGCAIPBackend)
backend_factory.register_backend(TrainingLocalBackend)
