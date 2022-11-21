from typing import TYPE_CHECKING, Any, Optional, Set, Type, cast

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
    BaseExperimentTrackerConfig,
)
from zenml.integrations.neptune.experiment_trackers.run_state import RunProvider
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo


class NeptuneExperimentTrackerConfig(BaseExperimentTrackerConfig):
    project: Optional[str] = None
    api_token: Optional[str] = SecretField()


class NeptuneExperimentTrackerSettings(BaseSettings):
    tags: Set[str] = set()


class NeptuneExperimentTracker(BaseExperimentTracker):
    """
    Track experiments using neptune.ai
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the experiment tracker.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.run_state: RunProvider = RunProvider()

    @property
    def config(self) -> NeptuneExperimentTrackerConfig:
        """Returns the `NeptuneExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(NeptuneExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Neptune experiment tracker.

        Returns:
            The settings class.
        """
        return NeptuneExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Initializes neptune run and stores it in the run_state
        object, so that it can be accessed later from other places
        e.g. step."""

        settings = cast(
            NeptuneExperimentTrackerSettings,
            self.get_settings(info) or NeptuneExperimentTrackerSettings(),
        )

        self.run_state.token = self.config.api_token
        self.run_state.project = self.config.project
        self.run_state.run_name = info.run_name
        self.run_state.tags = list(settings.tags)
