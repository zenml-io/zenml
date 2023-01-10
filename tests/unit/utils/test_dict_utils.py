#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import pytest

from zenml.utils import dict_utils


def test_recursive_update_works():
    """Tests recursive update."""
    original = {"a": {"b": 1}}
    update = {"a": {"c": 2}}
    expected = {"a": {"b": 1, "c": 2}}

    assert dict_utils.recursive_update(original, update) == expected


def test_recursive_update_works_three_levels_down():
    """Tests recursive update."""
    original = {"a": {"b": {"c": 1}}}
    update = {"a": {"b": {"d": 2}}}
    expected = {"a": {"b": {"c": 1, "d": 2}}}

    assert dict_utils.recursive_update(original, update) == expected


def test_recursive_update_works_when_update_is_empty():
    """Tests recursive update."""
    original = {"a": {"b": 1}}
    update = {}
    expected = {"a": {"b": 1}}

    assert dict_utils.recursive_update(original, update) == expected


def test_recursive_update_works_when_original_is_empty():
    """Tests recursive update."""
    original = {}
    update = {"a": {"b": 1}}
    expected = {"a": {"b": 1}}

    updated = dict_utils.recursive_update(original, update)
    assert updated == expected
    assert id(expected) != id(original)
    assert id(updated) == id(original)


def test_recursive_update_fails_when_update_is_not_a_dict():
    """Tests recursive update."""
    original = {"a": {"b": 1}}
    update = "aria_best_cat"
    # expected = {"a": {"b": 1}}

    with pytest.raises(AttributeError):
        dict_utils.recursive_update(original, update)


def test_recursive_update_fails_when_original_is_not_a_dict():
    """Tests recursive update."""
    original = "blupus_not_so_smart"
    update = {"a": {"b": 1}}
    # expected = {"a": {"b": 1}}

    with pytest.raises(AttributeError):
        dict_utils.recursive_update(original, update)


def test_remove_none_values_method_works():
    """Tests remove_none_values method."""
    original = {"a": None}
    expected = {}

    assert dict_utils.remove_none_values(original) == expected


def test_remove_none_values_method_fails_when_recursive_flag_not_used():
    """Tests remove_none_values method."""
    original = {"a": {"b": None}}
    expected = {}

    result = dict_utils.remove_none_values(original)
    assert result != expected
    assert result == original


def test_remove_none_values_method_works_when_recursive_flag_used():
    """Tests remove_none_values method."""
    original = {"a": {"b": None}}
    expected = {"a": {}}

    assert dict_utils.remove_none_values(original, recursive=True) == expected
