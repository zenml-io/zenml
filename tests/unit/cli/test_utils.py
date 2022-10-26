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


from zenml.cli.utils import parse_name_and_extra_arguments

SAMPLE_CUSTOM_ARGUMENTS = [
    '--custom_argument="value"',
    '--food="chicken biryani"',
    "axl",
    '--best_cat="aria"',
]


def test_parse_name_and_extra_arguments_returns_a_dict_of_known_options() -> None:
    """Check that parse_name_and_extra_arguments returns a dict of known options"""
    name, parsed_sample_args = parse_name_and_extra_arguments(
        SAMPLE_CUSTOM_ARGUMENTS
    )
    assert isinstance(parsed_sample_args, dict)
    assert len(parsed_sample_args.values()) == 3
    assert parsed_sample_args["best_cat"] == '"aria"'
    assert isinstance(name, str)
    assert name == "axl"
