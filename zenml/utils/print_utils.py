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

import enum
import pprint

import yaml
from dateutil import tz


class PrintStyles(enum.Enum):
    NATIVE = 0
    YAML = 1
    PPRINT = 2


def to_pretty_string(d, style=PrintStyles.YAML):
    """
    Args:
        d:
        style:
    """
    if style == PrintStyles.YAML:
        return yaml.dump(d, default_flow_style=False)
    elif style == PrintStyles.PPRINT:
        return pprint.pformat(d)
    else:
        return str(d)


def format_date(dt, format='%Y-%m-%d %H:%M:%S'):
    """
    Formatting a datetime object nicely.

    Args:
        dt: datetime object
        format: format
    """
    if dt is None:
        return ''
    local_zone = tz.tzlocal()
    # make sure this is UTC
    dt = dt.replace(tzinfo=tz.tzutc())
    local_time = dt.astimezone(local_zone)
    return local_time.strftime(format)


def format_timedelta(td):
    """
    Format timedelta object nicely.

    Args:
        td: timedelta object
    """
    if td is None:
        return ''
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
