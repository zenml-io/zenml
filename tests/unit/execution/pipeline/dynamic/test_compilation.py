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
"""Tests for dynamic compilation helpers."""

from types import SimpleNamespace

from zenml.config import DockerSettings
from zenml.config.resource_settings import PoolResourceDemand, ResourceSettings
from zenml.config.step_configurations import Step, StepConfiguration
from zenml.enums import StepRuntime
from zenml.execution.pipeline.dynamic.compilation import get_step_runtime


def _step_config(
    resource_settings: ResourceSettings,
    runtime: StepRuntime | None = None,
    step_operator: bool | str | None = None,
) -> StepConfiguration:
    """Create a minimal step configuration for runtime classification tests."""
    return Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {},
            },
            "config": {
                "name": "step_name",
                "enable_cache": True,
                "settings": {"resources": resource_settings},
                "runtime": runtime,
                "step_operator": step_operator,
            },
        }
    ).config


def test_basic_resource_demands_force_isolated_runtime() -> None:
    """Basic resource pool kinds force dynamic isolation."""
    step_config = _step_config(
        ResourceSettings(
            resources=[
                PoolResourceDemand(name="gpu-slot", quantity=1, kind="gpu")
            ]
        )
    )

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=step_config.docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=True),
    ) == (StepRuntime.ISOLATED, None)


def test_explicit_inline_runtime_returns_resource_override_warning() -> None:
    """Resource isolation returns a warning for explicit inline steps."""
    step_config = _step_config(
        ResourceSettings(cpu_count=1),
        runtime=StepRuntime.INLINE,
    )

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=step_config.docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=True),
    ) == (
        StepRuntime.ISOLATED,
        "Resource settings for step `step_name` require an isolated runtime, "
        "but the step was configured to run inline. Running the step in "
        "isolated runtime instead.",
    )


def test_step_operator_isolation_does_not_return_resource_warning() -> None:
    """Step operators take precedence without resource override warnings."""
    step_config = _step_config(
        ResourceSettings(cpu_count=1),
        runtime=StepRuntime.INLINE,
        step_operator=True,
    )

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=step_config.docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=True),
    ) == (StepRuntime.ISOLATED, None)


def test_unsupported_isolation_returns_runtime_override_warning() -> None:
    """Unsupported explicit isolation returns the existing warning."""
    step_config = _step_config(
        ResourceSettings(), runtime=StepRuntime.ISOLATED
    )

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=step_config.docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=False),
    ) == (
        StepRuntime.INLINE,
        "The SimpleNamespace does not support running steps in isolated "
        "runtimes. Running step `step_name` in inline runtime instead.",
    )


def test_step_run_resource_demands_do_not_force_isolated_runtime() -> None:
    """step_run is no longer treated as a basic infrastructure resource."""
    step_config = _step_config(
        ResourceSettings(
            resources=[
                PoolResourceDemand(
                    name="step-slot", quantity=1, kind="step_run"
                )
            ]
        )
    )

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=step_config.docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=True),
    ) == (StepRuntime.INLINE, None)


def test_custom_resource_demands_do_not_force_isolated_runtime() -> None:
    """Opaque pool resources keep the default inline runtime."""
    step_config = _step_config(ResourceSettings(resources={"license": 1}))

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=step_config.docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=True),
    ) == (StepRuntime.INLINE, None)


def test_different_docker_settings_force_implicit_isolated_runtime() -> None:
    """Different Docker settings preserve implicit isolation."""
    step_config = _step_config(ResourceSettings())
    pipeline_docker_settings = DockerSettings(parent_image="pipeline-image")

    assert get_step_runtime(
        step_config=step_config,
        pipeline_docker_settings=pipeline_docker_settings,
        orchestrator=SimpleNamespace(can_run_isolated_steps=True),
    ) == (StepRuntime.ISOLATED, None)
