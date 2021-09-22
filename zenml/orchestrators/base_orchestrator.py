import os
from abc import abstractmethod
from typing import Text

from zenml.core.base_component import BaseComponent
from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.utils.path_utils import get_zenml_config_dir


@orchestrator_store_factory.register(OrchestratorTypes.base)
class BaseOrchestrator(BaseComponent):
    _ORCHESTRATOR_STORE_DIR_NAME: Text = "orchestrators"

    @abstractmethod
    def run(self, zenml_pipeline, **kwargs):
        pass

    def get_serialization_dir(self):
        """Gets the local path where artifacts are stored."""
        return os.path.join(
            get_zenml_config_dir(), self._ORCHESTRATOR_STORE_DIR_NAME
        )

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_orchestrator_"
