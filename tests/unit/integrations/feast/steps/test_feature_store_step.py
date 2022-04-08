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

from contextlib import ExitStack as does_not_raise
from typing import List

import pytest
from hypothesis import given
from hypothesis.extra.pandas import columns, data_frames
from hypothesis.strategies import characters, floats, lists, text, tuples
from pandas import DataFrame

from zenml.integrations.feast.steps.feast_feature_store_step import (
    feast_historical_features_step,
    feast_online_features_step,
)
from zenml.steps.base_step import BaseStepMeta


@given(
    stepname=text(characters(whitelist_categories=["L", "N", "P", "Zs"])),
    feature_list=lists(text(min_size=1)),
    entity_df=data_frames(
        columns=columns([text(min_size=1)], dtype=float),
        rows=tuples(floats(allow_nan=False)),
    ),
)
def test_historical_features_step_returns_a_step(
    stepname: str, feature_list: List[str], entity_df: DataFrame
):
    """Test that the feast_historical_features_step function returns a step"""
    historical_entity_df = entity_df
    assert isinstance(historical_entity_df, DataFrame)

    features = feature_list
    step_name = stepname

    historical_feature_data_importer = feast_historical_features_step(
        name=step_name,
        entity_df=historical_entity_df,
        features=features,
    )
    assert isinstance(historical_feature_data_importer, BaseStepMeta)
    assert (
        historical_feature_data_importer.OUTPUT_SIGNATURE["output"] == DataFrame
    )


def test_historical_features_step_raise_error_when_arguments_not_passed_in():
    """Test that the feast historical features step function raises an error
    when required arguments aren't passed in"""
    with pytest.raises(TypeError):
        feast_historical_features_step()
    with pytest.raises(TypeError):
        feast_historical_features_step(features=[])
    with pytest.raises(TypeError):
        feast_historical_features_step(entity_df=DataFrame.from_dict({}))


@given(entity_text=text(min_size=1))
def test_historical_features_step_takes_string_for_entity_df(entity_text):
    """Ensure entity_df can also be passed a string"""
    with does_not_raise():
        feast_historical_features_step(features=[], entity_df=entity_text)


@given(
    stepname=text(characters(whitelist_categories=["L", "N", "P", "Zs"])),
    feature_list=lists(text(min_size=1)),
)
def test_online_features_step_returns_a_step(
    stepname: str, feature_list: List[str]
):
    """Test that the feast_historical_features_step function returns a step"""
    entity_rows = [{}]
    assert isinstance(entity_rows, List)

    features = feature_list
    step_name = stepname

    online_feature_data_importer = feast_online_features_step(
        name=step_name,
        entity_rows=entity_rows,
        features=features,
    )
    assert isinstance(online_feature_data_importer, BaseStepMeta)
    assert online_feature_data_importer.OUTPUT_SIGNATURE["output"] == dict


def test_online_features_step_raise_error_when_arguments_not_passed_in():
    """Test that the feast online features step function raises an error
    when required arguments aren't passed in"""
    with pytest.raises(TypeError):
        feast_online_features_step()
    with pytest.raises(TypeError):
        feast_online_features_step(features=[])
    with pytest.raises(TypeError):
        feast_online_features_step(entity_rows=[])
