#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

from datetime import datetime

from hypothesis import given
from hypothesis.strategies import datetimes

from zenml.cli.utils import format_date, parse_unknown_options
from zenml.repository import Repository

SAMPLE_CUSTOM_ARGUMENTS = [
    '--custom_argument="value"',
    '--food="chicken biryani"',
    '--best_cat="aria"',
]


@given(sample_datetime=datetimes(allow_imaginary=False))
def test_format_date_formats_a_string_properly(
    sample_datetime: datetime,
) -> None:
    """Check that format_date function formats a string properly"""
    assert isinstance(format_date(sample_datetime), str)
    assert format_date(datetime(2020, 1, 1), "%Y") == "2020"


def test_parse_unknown_options_returns_a_dict_of_known_options() -> None:
    """Check that parse_unknown_options returns a dict of known options"""
    parsed_sample_args = parse_unknown_options(SAMPLE_CUSTOM_ARGUMENTS)
    assert isinstance(parsed_sample_args, dict)
    assert len(parsed_sample_args.values()) == 3
    assert parsed_sample_args["best_cat"] == '"aria"'


def test_stack_config_has_right_contents_for_printing() -> None:
    """Check that the stack config has the right components for printing"""
    repo = Repository()
    active_stack_name = repo.active_stack_name
    stack_config = repo.stack_configurations[active_stack_name]
    items = [[typ.value, name] for typ, name in stack_config.items()]
    assert len(items) != 0
    assert items is not None
    for item in items:
        assert isinstance(item, list)
        for kv_pair in item:
            assert isinstance(kv_pair, str)
