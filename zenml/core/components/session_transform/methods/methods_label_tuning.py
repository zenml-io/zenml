#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

import pandas as pd


def tune_leadup(event_value, duration):
    """
    Args:
        event_value:
        duration:
    """
    def apply(x):
        timings = x.loc[x == event_value].index
        result = pd.Series(0, index=x.index)
        for t in timings:
            start = t - pd.to_timedelta(duration, unit='s')
            result.loc[start:t] = 1
        return result

    return apply


def tune_followup(event_value, duration):
    """
    Args:
        event_value:
        duration:
    """
    def apply(x):
        timings = x.loc[x == event_value].index
        result = pd.Series(0, index=x.index)
        for t in timings:
            end = t + pd.to_timedelta(duration, unit='s')
            result.loc[t:end] = 1
        return result

    return apply


def tune_shift(shift_steps, fill_value):
    """
    Args:
        shift_steps:
        fill_value:
    """
    def apply(x):
        return x.shift(shift_steps, fill_value=fill_value)

    return apply


def tune_map(mapper):
    """Replaces values of column specified through the mapper dict

    mapper: dict where key is the value to be replaced and value is the value
    to used for replacement

    Args:
        mapper:
    """

    def apply(x):
        for orig_val, new_val in mapper.items():
            x = x.replace(orig_val, str(new_val))
        return x

    return apply


def no_tune():
    def apply(x):
        return x

    return apply
