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
"""Tests for Databricks utility functions."""

import importlib.util
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from zenml.constants import ENV_ZENML_CUSTOM_SOURCE_ROOT

DATABRICKS_INSTALLED = importlib.util.find_spec("databricks") is not None
pytestmark = pytest.mark.skipif(
    not DATABRICKS_INSTALLED, reason="databricks dependency is not installed."
)

if DATABRICKS_INSTALLED:
    from zenml.integrations.databricks.utils import databricks_utils
    from zenml.integrations.databricks.utils.databricks_utils import (
        ENV_ZENML_DATABRICKS_WHEEL_PACKAGE,
        add_wheel_package_to_sys_path,
        build_databricks_cluster_spec,
        collect_requirements,
        configure_databricks_wheel_environment,
        convert_step_to_task,
    )


def _patch_distribution(monkeypatch: pytest.MonkeyPatch, root: str) -> None:
    """Patch wheel package distribution lookup."""
    fake_distribution = SimpleNamespace(locate_file=lambda _: root)
    monkeypatch.setattr(
        databricks_utils,
        "distribution",
        lambda _: fake_distribution,
    )


def _get_base_settings(**overrides: Any) -> SimpleNamespace:
    """Create settings for cluster spec utility tests."""
    settings = {
        "spark_version": None,
        "num_workers": None,
        "node_type_id": None,
        "driver_node_type_id": None,
        "policy_id": None,
        "autoscale": (0, 1),
        "single_user_name": None,
        "spark_conf": None,
        "availability_type": None,
        "custom_tags": None,
        "docker_image_url": None,
        "docker_image_username": None,
        "docker_image_password": None,
        "init_scripts": None,
        "autotermination_minutes": None,
    }
    settings.update(overrides)
    return SimpleNamespace(**settings)


def test_add_wheel_package_to_sys_path_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Tests that adding a wheel package root only updates sys.path once."""
    _patch_distribution(monkeypatch, str(tmp_path))
    monkeypatch.setattr(sys, "path", ["/existing-path"])

    project_root = add_wheel_package_to_sys_path("project_package")
    add_wheel_package_to_sys_path("project_package")

    assert sys.path == [project_root, "/existing-path"]
    assert sys.path.count(project_root) == 1


def test_configure_databricks_wheel_environment_sets_source_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Tests that wheel environment setup stores the absolute package root."""
    _patch_distribution(monkeypatch, str(tmp_path))
    monkeypatch.setattr(sys, "path", [])
    monkeypatch.delenv(ENV_ZENML_DATABRICKS_WHEEL_PACKAGE, raising=False)
    monkeypatch.delenv(ENV_ZENML_CUSTOM_SOURCE_ROOT, raising=False)

    project_root = configure_databricks_wheel_environment("project_package")

    assert sys.path == [project_root]
    assert (
        databricks_utils.os.environ[ENV_ZENML_DATABRICKS_WHEEL_PACKAGE]
        == "project_package"
    )
    assert (
        databricks_utils.os.environ[ENV_ZENML_CUSTOM_SOURCE_ROOT]
        == project_root
    )


def test_collect_requirements_warns_about_unsupported_pip_options(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests that pip options are reported instead of being silently used."""

    def gather_requirements_files(*_: Any, **__: Any) -> list[Any]:
        return [
            (
                "requirements.txt",
                "--extra-index-url https://example.com/simple\n"
                "pandas==2.2.3\n"
                "-f https://example.com/wheels",
                ["--index-url=https://example.com/simple"],
            )
        ]

    monkeypatch.setattr(
        databricks_utils.PipelineDockerImageBuilder,
        "gather_requirements_files",
        gather_requirements_files,
    )

    requirements = collect_requirements(
        docker_settings=SimpleNamespace(),
        stack=SimpleNamespace(),
    )

    assert requirements == ["pandas==2.2.3"]
    assert "pip options" in caplog.text


def test_convert_step_to_task_forwards_retry_settings() -> None:
    """Tests Databricks task payload includes retry configuration."""
    task = convert_step_to_task(
        task_name="trainer",
        command="entrypoint.main",
        arguments=["--snapshot_id", "snapshot-id"],
        libraries=["pandas==2.2.3"],
        depends_on=["upstream"],
        zenml_project_wheel="/Workspace/Shared/.zenml/project.whl",
        job_cluster_key="job-cluster",
        timeout_seconds=3600,
        max_retries=2,
        min_retry_interval_millis=60000,
        retry_on_timeout=True,
    )
    task_dict = task.as_dict()

    assert task_dict["task_key"] == "trainer"
    assert task_dict["timeout_seconds"] == 3600
    assert task_dict["max_retries"] == 2
    assert task_dict["min_retry_interval_millis"] == 60000
    assert task_dict["retry_on_timeout"] is True
    assert task_dict["depends_on"] == [{"task_key": "upstream"}]
    assert task_dict["python_wheel_task"]["parameters"] == [
        "--snapshot_id",
        "snapshot-id",
    ]


def test_build_cluster_spec_allows_missing_default_policy() -> None:
    """Tests that no default Job Compute policy is required."""
    client = SimpleNamespace(
        cluster_policies=SimpleNamespace(list=lambda: []),
        config=SimpleNamespace(host="https://workspace.azuredatabricks.net"),
    )
    settings = _get_base_settings(
        availability_type="SPOT_WITH_FALLBACK",
        init_scripts=["dbfs:/scripts/init.sh"],
    )

    cluster_spec = build_databricks_cluster_spec(
        databricks_client=client,
        settings=settings,
        env_vars={"ENV_KEY": "ENV_VALUE"},
    )
    cluster_spec_dict = cluster_spec.as_dict()

    assert "policy_id" not in cluster_spec_dict
    assert (
        cluster_spec_dict["azure_attributes"]["availability"]
        == "SPOT_WITH_FALLBACK_AZURE"
    )
    assert (
        cluster_spec_dict["init_scripts"][0]["dbfs"]["destination"]
        == "dbfs:/scripts/init.sh"
    )


def test_build_cluster_spec_rejects_non_dbfs_init_scripts() -> None:
    """Tests that non-DBFS init scripts fail before job submission."""
    client = SimpleNamespace(
        cluster_policies=SimpleNamespace(list=lambda: []),
        config=SimpleNamespace(host="https://workspace.cloud.databricks.com"),
    )
    settings = _get_base_settings(init_scripts=["s3://bucket/init.sh"])

    with pytest.raises(ValueError, match="DBFS paths"):
        build_databricks_cluster_spec(
            databricks_client=client,
            settings=settings,
            env_vars={},
        )
