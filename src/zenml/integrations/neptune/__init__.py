from typing import List, Type

from zenml.integrations.constants import NEPTUNE
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

# This is the flavor that will be used when registering this stack component
#  `zenml experiment_tracker register ... -f neptune`
NEPTUNE_MODEL_EXPERIMENT_TRACKER_FLAVOR = "neptune"


# Create a Subclass of the Integration Class
class NeptuneIntegration(Integration):
    """Definition of Neptune integration for ZenML."""

    NAME = NEPTUNE
    REQUIREMENTS = [
        "neptune-client>=0.16.10",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the <EXAMPLE> integration."""
        from zenml.integrations.neptune.flavors import (
            NeptuneExperimentTrackerFlavor,
        )

        return [
            NeptuneExperimentTrackerFlavor,
        ]


NeptuneIntegration.check_installation()  # this checks if the requirements are installed
