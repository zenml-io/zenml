#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Unit tests for the Trackio experiment tracker flavor."""

from zenml.enums import StackComponentType
from zenml.integrations.trackio import TRACKIO_EXPERIMENT_TRACKER_FLAVOR
from zenml.integrations.trackio.experiment_trackers import (
    TrackioExperimentTracker,
)
from zenml.integrations.trackio.flavors import (
    TrackioExperimentTrackerConfig,
    TrackioExperimentTrackerFlavor,
)


def test_trackio_flavor_metadata() -> None:
    """Trackio experiment tracker flavor advertises the expected metadata."""

    flavor = TrackioExperimentTrackerFlavor()

    assert flavor.name == TRACKIO_EXPERIMENT_TRACKER_FLAVOR
    assert flavor.type == StackComponentType.EXPERIMENT_TRACKER
    assert flavor.config_class is TrackioExperimentTrackerConfig
    assert flavor.implementation_class is TrackioExperimentTracker


def test_trackio_config_defaults() -> None:
    """Trackio configuration defaults to optional fields."""

    config = TrackioExperimentTrackerConfig()

    assert config.workspace is None
    assert config.project is None
    assert config.api_key is None
    assert config.base_url is None
