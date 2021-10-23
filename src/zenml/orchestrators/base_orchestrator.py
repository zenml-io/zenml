import os
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from zenml.core.base_component import BaseComponent
from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.utils.path_utils import get_zenml_config_dir

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline

# TODO [MEDIUM]: Can we remove this registration?
@orchestrator_store_factory.register(OrchestratorTypes.base)  # type: ignore[misc] # noqa
class BaseOrchestrator(BaseComponent):
    """Base Orchestrator class to orchestrate ZenML pipelines."""

    _ORCHESTRATOR_STORE_DIR_NAME: str = "orchestrators"

    @abstractmethod
    def run(self, zenml_pipeline: "BasePipeline", **kwargs: Any) -> Any:
        """Abstract method to run a pipeline. Overwrite this in subclasses
        with a concrete implementation on how to run the given pipeline.

        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Potential additional parameters used in subclass
                implementations.
        """
        raise NotImplementedError

    def get_serialization_dir(self) -> str:
        """Gets the local path where artifacts are stored."""
        return os.path.join(
            get_zenml_config_dir(), self._ORCHESTRATOR_STORE_DIR_NAME
        )

    def pre_run(self) -> None:
        """Should be run before the `run()` function to prepare orchestrator."""

    def post_run(self) -> None:
        """Should be run after the `run()` to clean up."""

    def up(self) -> None:
        """Provisions resources for the orchestrator."""

    def down(self) -> None:
        """Destroys resources for the orchestrator."""

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_orchestrator_"
