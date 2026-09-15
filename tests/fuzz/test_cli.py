#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Property tests for CLI parsing and filter construction."""

import string
from typing import Any, List, Tuple

import click
import pytest
from click.testing import CliRunner
from hypothesis import example, given
from hypothesis import strategies as st

from zenml.cli.utils import list_options, parse_name_and_extra_arguments
from zenml.models import ProjectFilter

_VALUE_ALPHABET = st.characters(
    blacklist_categories=("Cc", "Cs"), blacklist_characters=":"
)
_PLAIN_VALUES = st.text(alphabet=_VALUE_ALPHABET, max_size=64)
_FILTER_VALUES = st.one_of(
    _PLAIN_VALUES,
    _PLAIN_VALUES.map(lambda value: f"contains:{value}"),
    st.sampled_from(
        [
            "",
            "a=b",
            "contains:a:b",
            '{"quoted":"value"}',
            "café=値",
        ]
    ),
)
_ARGUMENT_VALUES = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    max_size=64,
)
_IDENTIFIERS = st.text(
    alphabet=string.ascii_lowercase,
    min_size=1,
    max_size=12,
)


@click.command()
@list_options(ProjectFilter)
def _filter_command(
    columns: str, output_format: str, **filter_values: Any
) -> ProjectFilter:
    """Construct a project filter through the real list-option decorator."""
    del columns, output_format
    return ProjectFilter(**filter_values)


def _normalized_repeated_value(values: List[str]) -> Any:
    """Return the value shape produced by ``list_options``."""
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return values


@given(values=st.lists(_FILTER_VALUES, max_size=3))
@example(values=[])
@example(values=[""])
@example(values=["a=b", "contains:a:b", '{"quoted":"値"}'])
def test_list_options_matches_direct_filter_construction(
    values: List[str],
) -> None:
    """CLI parsing preserves values and repeated-option normalization."""
    arguments = [f"--name={value}" for value in values]

    result = CliRunner().invoke(
        _filter_command, arguments, standalone_mode=False
    )

    assert result.exit_code == 0, result.output
    cli_filter = result.return_value
    direct_filter = ProjectFilter(
        name=_normalized_repeated_value(values), sort_by="desc:created"
    )
    assert cli_filter.model_dump() == direct_filter.model_dump()


@given(
    name=st.text(
        alphabet=string.ascii_letters + string.digits + "-_ =:値",
        min_size=1,
        max_size=32,
    ).map(lambda value: f"name-{value}"),
    arguments=st.lists(st.tuples(_IDENTIFIERS, _ARGUMENT_VALUES), max_size=5),
    name_position=st.integers(min_value=0, max_value=5),
)
@example(
    name="unicode-名前",
    arguments=[
        ("payload", "a=b:c"),
        ("payload", '{"quoted":"値"}'),
        ("empty", ""),
        ("literal_file", "@does-not-exist"),
    ],
    name_position=2,
)
@example(
    name="duplicate",
    arguments=[("key", "first"), ("key", "last")],
    name_position=1,
)
def test_extra_arguments_preserve_values_and_input(
    name: str,
    arguments: List[Tuple[str, str]],
    name_position: int,
) -> None:
    """Extra arguments retain values, input order, and last-key semantics."""
    cli_arguments = [f"--{key}={value}" for key, value in arguments]
    cli_arguments.insert(min(name_position, len(cli_arguments)), name)
    original_arguments = list(cli_arguments)

    parsed_name, parsed_arguments = parse_name_and_extra_arguments(
        list(cli_arguments), expand_args=False
    )

    assert cli_arguments == original_arguments
    assert parsed_name == name
    assert parsed_arguments == dict(arguments)


@given(option_name=_IDENTIFIERS)
def test_unknown_list_option_is_a_usage_error(option_name: str) -> None:
    """Unknown generated options fail through Click's usage-error path."""
    result = CliRunner().invoke(
        _filter_command,
        [f"--unknown-{option_name}=value"],
    )

    assert result.exit_code == 2
    assert "No such option" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["name", "--missing_equals"],
        ["name", "--not-valid=value"],
        ["name", "unexpected=value"],
    ],
)
def test_malformed_extra_arguments_are_click_errors(
    arguments: List[str],
) -> None:
    """Malformed free-form arguments produce controlled Click errors."""
    original_arguments = list(arguments)

    with pytest.raises(click.ClickException):
        parse_name_and_extra_arguments(
            list(arguments), expand_args=False, name_mandatory=True
        )

    assert arguments == original_arguments
