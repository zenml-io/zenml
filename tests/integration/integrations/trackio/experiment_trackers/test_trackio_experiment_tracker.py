#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.enums import StackComponentType
from zenml.integrations.trackio.experiment_trackers.trackio_experiment_tracker import (
    HF_TOKEN_ENV_VAR,
    TrackioExperimentTracker,
)
from zenml.integrations.trackio.flavors.trackio_experiment_tracker_flavor import (
    TrackioExperimentTrackerConfig,
    TrackioExperimentTrackerSettings,
)
from zenml.metadata.metadata_types import Uri


def _tracker(**config_kwargs):
    return TrackioExperimentTracker(
        name="trackio",
        id=uuid4(),
        config=TrackioExperimentTrackerConfig(
            project_name="test-project",
            **config_kwargs,
        ),
        flavor="trackio",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _settings(**kwargs):
    return TrackioExperimentTrackerSettings(**kwargs)


def _info():
    return SimpleNamespace(
        run_name="pipeline_run",
        pipeline_step_name="trainer",
        pipeline=SimpleNamespace(
            name="pipeline",
        ),
    )


def _mock_trackio_signature(
    mock_signature: MagicMock,
) -> None:
    mock_signature.return_value.parameters = {
        "project": None,
        "name": None,
        "config": None,
        "dir": None,
        "resume": None,
        "tracking_uri": None,
        "sdk": None,
        "space": None,
    }


@pytest.fixture
def mock_trackio_signature():
    with patch(
        "zenml.integrations.trackio.experiment_trackers."
        "trackio_experiment_tracker.inspect.signature"
    ) as mock_signature:
        _mock_trackio_signature(mock_signature)
        yield mock_signature


def test_trackio_experiment_tracker_attributes() -> None:
    tracker = _tracker()

    assert tracker.type == StackComponentType.EXPERIMENT_TRACKER
    assert tracker.flavor == "trackio"


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
def test_trackio_run_initialization(
    mock_init: MagicMock,
    mock_trackio_signature,
) -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(return_value=_settings())

    tracker.prepare_step_run(_info())

    kwargs = mock_init.call_args.kwargs

    assert kwargs["project"] == "test-project"
    assert kwargs["name"] == "pipeline_run_trainer"
    assert kwargs["resume"] == "allow"


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
def test_trackio_custom_run_name(
    mock_init: MagicMock,
    mock_trackio_signature,
) -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(
        return_value=_settings(
            run_name="custom-run",
        )
    )

    tracker.prepare_step_run(_info())

    kwargs = mock_init.call_args.kwargs

    assert kwargs["name"] == "custom-run"


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
def test_trackio_static_backend_adds_sdk(
    mock_init: MagicMock,
    mock_trackio_signature,
) -> None:
    tracker = _tracker(
        backend="static",
    )

    tracker.get_settings = MagicMock(return_value=_settings())

    tracker.prepare_step_run(_info())

    kwargs = mock_init.call_args.kwargs

    assert kwargs["sdk"] == "static"


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
def test_trackio_hf_space_passed(
    mock_init: MagicMock,
    mock_trackio_signature,
) -> None:
    tracker = _tracker(
        hf_space="test-space",
    )

    tracker.get_settings = MagicMock(return_value=_settings())

    tracker.prepare_step_run(_info())

    kwargs = mock_init.call_args.kwargs

    assert kwargs["space"] == "test-space"


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.log"
)
@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
def test_trackio_tags_logged(
    mock_init: MagicMock,
    mock_log: MagicMock,
    mock_trackio_signature,
) -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(
        return_value=_settings(
            tags=["team", "prod"],
        )
    )

    tracker.prepare_step_run(_info())

    mock_log.assert_called_once_with(
        {
            "zenml_tags": [
                "team",
                "prod",
            ]
        }
    )


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.finish"
)
@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.sync"
)
def test_trackio_sync_enabled(
    mock_sync: MagicMock,
    mock_finish: MagicMock,
) -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(
        return_value=_settings(
            auto_sync=True,
        )
    )

    tracker.cleanup_step_run(
        _info(),
        step_failed=False,
    )

    mock_sync.assert_called_once_with(
        project="test-project",
    )

    mock_finish.assert_called_once()


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.finish"
)
@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.freeze"
)
def test_trackio_freeze_enabled(
    mock_freeze: MagicMock,
    mock_finish: MagicMock,
) -> None:
    tracker = _tracker(
        hf_space="space-id",
    )

    tracker.get_settings = MagicMock(
        return_value=_settings(
            auto_freeze=True,
        )
    )

    tracker.cleanup_step_run(
        _info(),
        step_failed=False,
    )

    mock_freeze.assert_called_once_with(
        space_id="space-id",
        project="test-project",
    )

    mock_finish.assert_called_once()


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.finish"
)
@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.sync"
)
def test_trackio_cleanup_calls_finish_on_failure(
    mock_sync: MagicMock,
    mock_finish: MagicMock,
) -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(
        return_value=_settings(
            auto_sync=True,
        )
    )

    mock_sync.side_effect = RuntimeError("sync failed")

    tracker.cleanup_step_run(
        _info(),
        step_failed=False,
    )

    mock_finish.assert_called_once()


def test_trackio_metadata() -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(return_value=_settings())

    with patch(
        "zenml.integrations.trackio.experiment_trackers."
        "trackio_experiment_tracker.trackio.run",
        new=SimpleNamespace(
            name="trackio-run",
            url="https://trackio.ai/run/123",
        ),
    ):
        metadata = tracker.get_step_run_metadata(_info())

    assert metadata["trackio_run_name"] == "trackio-run"

    assert metadata[METADATA_EXPERIMENT_TRACKER_URL] == Uri(
        "https://trackio.ai/run/123"
    )


def test_trackio_metadata_without_run() -> None:
    tracker = _tracker()

    tracker.get_settings = MagicMock(return_value=_settings())

    with patch(
        "zenml.integrations.trackio.experiment_trackers."
        "trackio_experiment_tracker.trackio.run",
        new=None,
    ):
        metadata = tracker.get_step_run_metadata(_info())

    assert metadata["trackio_run_name"] == ("pipeline_run_trainer")


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.finish"
)
def test_hf_token_restored_after_cleanup(
    mock_finish: MagicMock,
    mock_init: MagicMock,
    monkeypatch,
    mock_trackio_signature,
) -> None:
    monkeypatch.setenv(
        HF_TOKEN_ENV_VAR,
        "original-token",
    )

    tracker = _tracker(
        hf_token="temporary-token",
    )

    tracker.get_settings = MagicMock(return_value=_settings())

    info = _info()

    tracker.prepare_step_run(info)

    assert os.environ[HF_TOKEN_ENV_VAR] == "temporary-token"

    tracker.cleanup_step_run(
        info,
        step_failed=False,
    )

    assert os.environ[HF_TOKEN_ENV_VAR] == "original-token"


@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.init"
)
@patch(
    "zenml.integrations.trackio.experiment_trackers."
    "trackio_experiment_tracker.trackio.finish"
)
def test_hf_token_removed_after_cleanup(
    mock_finish: MagicMock,
    mock_init: MagicMock,
    monkeypatch,
    mock_trackio_signature,
) -> None:
    monkeypatch.delenv(
        HF_TOKEN_ENV_VAR,
        raising=False,
    )

    tracker = _tracker(
        hf_token="temporary-token",
    )

    tracker.get_settings = MagicMock(return_value=_settings())

    info = _info()

    tracker.prepare_step_run(info)

    tracker.cleanup_step_run(
        info,
        step_failed=False,
    )

    assert HF_TOKEN_ENV_VAR not in os.environ
