#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from contextlib import ExitStack as does_not_raise

from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    get_segment_key,
    track_event,
)


def test_get_segment_key():
    """Checks the get_segment_key method returns a value"""
    with does_not_raise():
        get_segment_key()


def test_track_event_conditions():
    """It should return true for the analytics events but false for everything
    else."""
    assert track_event(AnalyticsEvent.OPT_IN_ANALYTICS)
    assert track_event(AnalyticsEvent.OPT_OUT_ANALYTICS)
    assert not track_event(AnalyticsEvent.EVENT_TEST)
