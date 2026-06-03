#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
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
"""Unit tests for SkyPilot utility helpers."""

import importlib
import sys
import types
from typing import Any

import pytest

from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorSettings,
)


def _load_utils_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Loads the SkyPilot utils module with a stubbed `sky` module."""
    fake_sky = types.ModuleType("sky")
    fake_sky.stream_and_get = lambda request_id: (42, object())
    fake_sky.get = lambda request_id: (42, object())
    fake_sky.tail_logs = lambda **kwargs: 0
    monkeypatch.setitem(sys.modules, "sky", fake_sky)

    import zenml.integrations.skypilot.utils as utils

    return importlib.reload(utils)


def test_prepare_docker_setup_uses_password_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests docker login setup uses password-stdin."""
    utils = _load_utils_module(monkeypatch)

    setup, task_envs = utils.prepare_docker_setup(
        container_registry_uri="index.docker.io",
        credentials=("user", "pass"),
        use_sudo=True,
    )

    assert setup is not None
    assert "--password-stdin" in setup
    assert "--password $DOCKER_PASSWORD" not in setup
    assert task_envs == {"DOCKER_USERNAME": "user", "DOCKER_PASSWORD": "pass"}


def test_create_docker_run_command_uses_env_names_not_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests docker command does not inline secret environment values."""
    utils = _load_utils_module(monkeypatch)

    command = utils.create_docker_run_command(
        image="my-registry.io/test/image:latest",
        entrypoint_str="python -m zenml.entrypoints.entrypoint",
        arguments_str="--snapshot_id abc",
        environment={"SAFE_KEY": "secret with spaces", "TOKEN": "abc$123"},
        docker_run_args=["--gpus=all", "--name", "zenml test"],
        use_sudo=False,
    )

    assert "-e SAFE_KEY" in command
    assert "-e TOKEN" in command
    assert "SAFE_KEY=secret with spaces" not in command
    assert "abc$123" not in command
    assert "'zenml test'" in command


def test_create_docker_run_command_rejects_invalid_env_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests invalid environment variable names are rejected."""
    utils = _load_utils_module(monkeypatch)

    with pytest.raises(ValueError, match="Invalid environment variable"):
        utils.create_docker_run_command(
            image="test/image",
            entrypoint_str="python -m x",
            arguments_str="",
            environment={"BAD-NAME": "value"},
            docker_run_args=[],
            use_sudo=False,
        )


def test_prepare_resources_kwargs_omits_cloud_region_zone_when_infra_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests infra mode omits cloud/region/zone kwargs."""
    utils = _load_utils_module(monkeypatch)
    settings = SkypilotBaseOrchestratorSettings(infra="aws/us-east-1")

    resources_kwargs = utils.prepare_resources_kwargs(
        cloud=object(),
        settings=settings,
        default_instance_type="m5.large",
    )

    assert resources_kwargs["infra"] == "aws/us-east-1"
    assert resources_kwargs["instance_type"] == "m5.large"
    assert "cloud" not in resources_kwargs
    assert "region" not in resources_kwargs
    assert "zone" not in resources_kwargs


def test_prepare_resources_kwargs_rejects_conflicting_resources_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests infra mode rejects cloud/region/zone in resources_settings."""
    utils = _load_utils_module(monkeypatch)
    settings = SkypilotBaseOrchestratorSettings().model_copy(
        update={
            "infra": "aws/us-east-1",
            "resources_settings": {"cloud": "aws"},
        },
        deep=True,
    )

    with pytest.raises(ValueError, match="cannot be combined"):
        utils.prepare_resources_kwargs(
            cloud=object(),
            settings=settings,
            default_instance_type="m5.large",
        )


def test_prepare_launch_kwargs_filters_unsupported_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests unsupported launch_settings keys are removed."""
    utils = _load_utils_module(monkeypatch)
    settings = SkypilotBaseOrchestratorSettings(
        launch_settings={
            "stream_logs": False,
            "detach_setup": True,
            "detach_run": True,
            "num_nodes": 4,
            "foo": "bar",
        }
    )

    launch_kwargs = utils.prepare_launch_kwargs(settings=settings)

    for key in utils.UNSUPPORTED_LAUNCH_SETTINGS_KEYS:
        assert key not in launch_kwargs
    assert launch_kwargs["foo"] == "bar"


def test_sky_job_get_returns_waiter_when_streaming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests sky_job_get returns a waiter function when streaming logs."""
    utils = _load_utils_module(monkeypatch)

    calls = {}

    def _stream_and_get(request_id: Any) -> Any:
        calls["request_id"] = request_id
        return (11, object())

    def _tail_logs(cluster_name: str, job_id: int, follow: bool) -> int:
        calls["tail_logs"] = (cluster_name, job_id, follow)
        return 0

    utils.sky.stream_and_get = _stream_and_get
    utils.sky.tail_logs = _tail_logs

    result = utils.sky_job_get(
        request_id="request-1",
        stream_logs=True,
        cluster_name="cluster-a",
    )

    assert result is not None
    assert result.wait_for_completion is not None
    result.wait_for_completion()
    assert calls["request_id"] == "request-1"
    assert calls["tail_logs"] == ("cluster-a", 11, True)


def test_sky_job_get_is_non_blocking_without_streaming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests sky_job_get keeps non-blocking behavior when logs are disabled."""
    utils = _load_utils_module(monkeypatch)

    utils.sky.get = lambda request_id: (7, object())
    result = utils.sky_job_get(
        request_id="request-2",
        stream_logs=False,
        cluster_name="cluster-b",
    )

    assert result is not None
    assert result.wait_for_completion is None


def test_sky_job_get_rejects_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests malformed SkyPilot API response is surfaced clearly."""
    utils = _load_utils_module(monkeypatch)
    utils.sky.get = lambda request_id: None

    with pytest.raises(RuntimeError, match="expected a non-empty tuple"):
        utils.sky_job_get(
            request_id="request-3",
            stream_logs=False,
            cluster_name="cluster-c",
        )


def test_sky_job_get_rejects_non_integer_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests non-int job IDs fail with contextual errors."""
    utils = _load_utils_module(monkeypatch)
    utils.sky.get = lambda request_id: ("abc", object())

    with pytest.raises(RuntimeError, match="expected int"):
        utils.sky_job_get(
            request_id="request-4",
            stream_logs=False,
            cluster_name="cluster-d",
        )
