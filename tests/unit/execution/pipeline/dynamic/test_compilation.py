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

from zenml.config.resource_settings import PoolResourceDemand, ResourceSettings
from zenml.config.step_configurations import Step, StepConfiguration
from zenml.enums import StepRuntime
from zenml.execution.pipeline.dynamic.compilation import get_step_runtime


def _step_config(resource_settings: ResourceSettings) -> StepConfiguration:
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
            },
        }
    ).config


def test_basic_resource_demands_force_isolated_runtime() -> None:
    """Basic resource pool kinds force dynamic isolation."""
    step_config = _step_config(
        ResourceSettings(
            resources=[
                PoolResourceDemand(
                    name="step-slot", quantity=1, kind="step_run"
                )
            ]
        )
    )

    assert (
        get_step_runtime(
            step_config=step_config,
            pipeline_docker_settings=step_config.docker_settings,
            orchestrator=SimpleNamespace(can_run_isolated_steps=True),
        )
        is StepRuntime.ISOLATED
    )


def test_custom_resource_demands_do_not_force_isolated_runtime() -> None:
    """Opaque pool resources keep the default inline runtime."""
    step_config = _step_config(ResourceSettings(resources={"license": 1}))

    assert (
        get_step_runtime(
            step_config=step_config,
            pipeline_docker_settings=step_config.docker_settings,
            orchestrator=SimpleNamespace(can_run_isolated_steps=True),
        )
        is StepRuntime.INLINE
    )
