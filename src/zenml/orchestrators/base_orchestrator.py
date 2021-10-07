import os
from abc import abstractmethod
from typing import TYPE_CHECKING

from zenml.core.base_component import BaseComponent
from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.utils.path_utils import get_zenml_config_dir

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


@orchestrator_store_factory.register(OrchestratorTypes.base)
class BaseOrchestrator(BaseComponent):
    """Base Orchestrator class to orchestrate ZenML pipelines."""

    _ORCHESTRATOR_STORE_DIR_NAME: str = "orchestrators"

    @abstractmethod
    def run(self, zenml_pipeline: "BasePipeline", **kwargs):
        """Abstract method to run a pipeline. Overwrite this in subclasses
        with a concrete implementation on how to run the given pipeline.

        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Potential additional parameters used in subclass
                implementations.
        """

    def get_serialization_dir(self) -> str:
        """Gets the local path where artifacts are stored."""
        return os.path.join(
            get_zenml_config_dir(), self._ORCHESTRATOR_STORE_DIR_NAME
        )

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_orchestrator_"
