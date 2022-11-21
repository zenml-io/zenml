from typing import Type

from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.neptune import NEPTUNE_MODEL_EXPERIMENT_TRACKER_FLAVOR
from zenml.integrations.neptune.experiment_trackers import (
    NeptuneExperimentTracker,
    NeptuneExperimentTrackerConfig,
)


class NeptuneExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Class for the `NeptuneExperimentTrackerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.
        Returns:
            The name of the flavor.
        """
        return NEPTUNE_MODEL_EXPERIMENT_TRACKER_FLAVOR

    @property
    def config_class(self) -> Type[NeptuneExperimentTrackerConfig]:
        """Returns `NeptuneExperimentTrackerConfig` config class.
        Returns:
                The config class.
        """
        return NeptuneExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["NeptuneExperimentTracker"]:
        """Implementation class for this flavor.
        Returns:
            The implementation class.
        """
        from zenml.integrations.neptune.experiment_trackers import (
            NeptuneExperimentTracker,
        )

        return NeptuneExperimentTracker
