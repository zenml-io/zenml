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

import pandas as pd
import pytest
from pydantic import ValidationError

from zenml.integrations.evidently.steps.evidently_profile import (
    EvidentlyColumnMapping,
    EvidentlyProfileConfig,
    EvidentlyProfileStep,
)

ref = pd.DataFrame()
ref["target"] = ["A", "B", "B", "C", "A"]
ref["prediction"] = [0.12, -0.54, 0.08, 1.78, 0.03]
ref["ignored_col"] = [1, 5, 1, 89, 0]
ref["var_A"] = [1, 5, 3, 10, 25]
ref["var_B"] = [0.58, 0.23, 1.25, -0.14, 0]

comp = pd.DataFrame()
comp["target"] = ["B", "C", "A", "A", "C"]
comp["prediction"] = [0.12, -0.54, 0.08, 1.78, 0.03]
comp["ignored_col"] = [3, 1, 1, 120, 1]
comp["var_A"] = [0, 27, 3, 4, 8]
comp["var_B"] = [0.12, -0.54, 0.08, 1.78, 0.03]


def test_ignore_cols_succeeds() -> None:
    """Tests ignored_cols parameter with features ignore_col and var_C
    to be ignored"""

    column_map = EvidentlyColumnMapping(target_names=["target"])

    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"],
        column_mapping=column_map,
        ignored_cols=["ignored_col", "var_B"],
    )

    profile_step = EvidentlyProfileStep()

    drift_obj, dash_obj = profile_step.entrypoint(
        reference_dataset=ref,
        comparison_dataset=comp,
        config=profile_config,
    )

    target = [drift_obj["data_drift"]["data"]["utility_columns"]["target"]]
    prediction = [
        drift_obj["data_drift"]["data"]["utility_columns"]["prediction"]
    ]
    cat_feat_names = drift_obj["data_drift"]["data"]["cat_feature_names"]
    num_feat_names = drift_obj["data_drift"]["data"]["num_feature_names"]

    assert (
        "ignored_col"
        not in target + prediction + cat_feat_names + num_feat_names
    )
    assert "var_B" not in target + prediction + cat_feat_names + num_feat_names


def test_do_not_ignore_any_columns() -> None:
    """Tests ignored_cols parameter with nothing to ignore
    i.e pass all features"""

    column_map = EvidentlyColumnMapping(target_names=["target"])

    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"],
        column_mapping=column_map,
        ignored_cols=None,
    )

    profile_step = EvidentlyProfileStep()

    drift_obj, dash_obj = profile_step.entrypoint(
        reference_dataset=ref,
        comparison_dataset=comp,
        config=profile_config,
    )
    target = [drift_obj["data_drift"]["data"]["utility_columns"]["target"]]
    prediction = [
        drift_obj["data_drift"]["data"]["utility_columns"]["prediction"]
    ]
    cat_feat_names = drift_obj["data_drift"]["data"]["cat_feature_names"]
    num_feat_names = drift_obj["data_drift"]["data"]["num_feature_names"]

    all_cols = target + prediction + cat_feat_names + num_feat_names
    assert "target" in all_cols
    assert "prediction" in all_cols
    assert "ignored_col" in all_cols
    assert "var_A" in all_cols
    assert "var_B" in all_cols


def test_ignoring_non_existing_column() -> None:
    """Tests ignored_cols parameter for non existing
    features and raises Error"""

    column_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"],
        column_mapping=column_map,
        ignored_cols=["var_A", "test_1"],
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(ValueError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
        )


def test_ignoring_incorrect_datatype() -> None:
    """Tests ignored_cols parameter for incorrect datatype
    and raises Error"""

    column_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"],
        column_mapping=column_map,
        ignored_cols="var_A",
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(ValidationError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
        )


def test_ignored_cols_elements() -> None:
    """Tests ignored_cols parameter for type of its elements
    and raises Error"""

    column_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"],
        column_mapping=column_map,
        ignored_cols=["Housing", "Region", 25, True],
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(ValueError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
        )


def test_empty_ignored_cols() -> None:
    """Tests for empty ignored_cols parameter
    and raises Error"""

    column_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"],
        column_mapping=column_map,
        ignored_cols=[],
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(ValueError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
        )
