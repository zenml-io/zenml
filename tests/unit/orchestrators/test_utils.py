#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from zenml.orchestrators.utils import is_setting_enabled


def test_is_setting_enabled():
    """Unit test for `is_setting_enabled()`.

    Tests that:
    - caching is enabled by default (when neither step nor pipeline set it),
    - caching is always enabled if explicitly enabled for the step,
    - caching is always disabled if explicitly disabled for the step,
    - caching is set to the pipeline cache if not configured for the step.
    """
    # Caching is enabled by default
    assert (
        is_setting_enabled(
            is_enabled_on_step=None, is_enabled_on_pipeline=None
        )
        is True
    )

    # Caching is always enabled if explicitly enabled for the step
    assert (
        is_setting_enabled(
            is_enabled_on_step=True,
            is_enabled_on_pipeline=True,
        )
        is True
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=True,
            is_enabled_on_pipeline=False,
        )
        is True
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=True,
            is_enabled_on_pipeline=None,
        )
        is True
    )

    # Caching is always disabled if explicitly disabled for the step
    assert (
        is_setting_enabled(
            is_enabled_on_step=False,
            is_enabled_on_pipeline=True,
        )
        is False
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=False,
            is_enabled_on_pipeline=False,
        )
        is False
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=False,
            is_enabled_on_pipeline=None,
        )
        is False
    )

    # Caching is set to the pipeline cache if not configured for the step
    assert (
        is_setting_enabled(
            is_enabled_on_step=None,
            is_enabled_on_pipeline=True,
        )
        is True
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=None,
            is_enabled_on_pipeline=False,
        )
        is False
    )
