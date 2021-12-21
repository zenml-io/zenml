import os
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from zenml.core.base_component import BaseComponent
from zenml.io.utils import get_zenml_config_dir

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


class BaseOrchestrator(BaseComponent):
    """Base Orchestrator class to orchestrate ZenML pipelines."""

    _ORCHESTRATOR_STORE_DIR_NAME: str = "orchestrators"

    def __init__(self, repo_path: str, **kwargs: Any) -> None:
        """Initializes a BaseOrchestrator instance.

        Args:
            repo_path: Path to the repository of this orchestrator.
        """
        serialization_dir = os.path.join(
            get_zenml_config_dir(repo_path),
            self._ORCHESTRATOR_STORE_DIR_NAME,
        )
        super().__init__(serialization_dir=serialization_dir, **kwargs)

    @abstractmethod
    def run(
        self, zenml_pipeline: "BasePipeline", run_name: str, **kwargs: Any
    ) -> Any:
        """Abstract method to run a pipeline. Overwrite this in subclasses
        with a concrete implementation on how to run the given pipeline.

        Args:
            zenml_pipeline: The pipeline to run.
            run_name: Name of the pipeline run.
            **kwargs: Potential additional parameters used in subclass
                implementations.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Returns whether the orchestrator is currently running."""

    @property
    def log_file(self) -> Optional[str]:
        """Returns path to a log file if available."""
        # TODO [ENG-136]: make this more generic in case an orchestrator has
        #  multiple log files, e.g. change to a monitor() method which yields
        #  new logs to output to the CLI
        return None

    def pre_run(self, pipeline: "BasePipeline", caller_filepath: str) -> None:
        """Should be run before the `run()` function to prepare orchestrator.

        Args:
            pipeline: Pipeline that will be run.
            caller_filepath: Path to the file in which `pipeline.run()` was
                called. This is necessary for airflow so we know the file in
                which the DAG is defined.
        """

    def post_run(self) -> None:
        """Should be run after the `run()` to clean up."""

    def up(self) -> None:
        """Provisions resources for the orchestrator."""

    def down(self) -> None:
        """Destroys resources for the orchestrator."""

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_orchestrator_"
