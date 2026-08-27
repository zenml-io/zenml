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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Regression test for implicit inline reclaim tolerance."""

from zenml.config.resource_settings import ResourceSettings
from zenml.config.step_configurations import StepConfiguration
from zenml.enums import ResourceRequestReclaimTolerance, StepRuntime
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_implicit_inline_reclaim_tolerance_survives_config_access() -> None:
    """Reading step settings must not turn an implicit default explicit."""
    step_config = StepConfiguration(
        name="inline-step",
        settings={"resources": ResourceSettings()},
    )

    resource_settings = step_config.resource_settings

    assert resource_settings.reclaim_tolerance_explicitly_set is False
    assert (
        resource_settings.effective_reclaim_tolerance(StepRuntime.INLINE)
        is ResourceRequestReclaimTolerance.NONE
    )

    # Inline steps are not reclaimable. With the implicit default preserved,
    # validation must accept the step rather than trying to reclaim it or
    # rejecting it as explicitly reclaimable.
    SqlZenStore._validate_reclaim_tolerance_for_resource_request(
        resource_settings=resource_settings,
        runtime=StepRuntime.INLINE,
        heartbeat_enabled=False,
        step_name=step_config.name,
    )
