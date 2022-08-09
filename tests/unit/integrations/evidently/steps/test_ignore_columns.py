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

from zenml.integrations.evidently.steps.evidently_profile import (
    EvidentlyColumnMapping,
    EvidentlyProfileConfig,
    EvidentlyProfileStep,
)

ref = pd.DataFrame()
ref["target"] = ["A", "B", "B", "C", "A"]
ref["prediction"] = [0.12, -0.54, 0.08, 1.78, 0.03]
ref["ignore_col"] = [1, 5, 1, 89, 0]
ref["var_A"] = [1, 5, 3, 10, 25]
ref["var_B"] = [0.58, 0.23, 1.25, -0.14, 0]

comp = pd.DataFrame()
comp["target"] = ["B", "C", "A", "A", "C"]
comp["prediction"] = [0.12, -0.54, 0.08, 1.78, 0.03]
comp["ignore_col"] = [3, 1, 1, 120, 1]
comp["var_A"] = [0, 27, 3, 4, 8]
comp["var_B"] = [0.12, -0.54, 0.08, 1.78, 0.03]


def test_ignore_feat() -> None:
    """Tests ignore cols parameter with features ignore_col and var_C
    to be ignored"""

    clmn_map = EvidentlyColumnMapping(target_names=["target"])

    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"], column_mapping=clmn_map
    )

    print("config created sucessfully")
    profile_step = EvidentlyProfileStep()

    print(" step created sucessfully")
    drift_obj, dash_obj = profile_step.entrypoint(
        reference_dataset=ref,
        comparison_dataset=comp,
        config=profile_config,
        ignored_columns=("ignore_col", "var_B"),
    )

    target = [drift_obj["data_drift"]["data"]["utility_columns"]["target"]]
    prediction = [
        drift_obj["data_drift"]["data"]["utility_columns"]["prediction"]
    ]
    cat_feat_names = drift_obj["data_drift"]["data"]["cat_feature_names"]
    num_feat_names = drift_obj["data_drift"]["data"]["num_feature_names"]

    assert (
        "ignore_col"
        not in target + prediction + cat_feat_names + num_feat_names
    )
    assert "var_B" not in target + prediction + cat_feat_names + num_feat_names


def test_default_ignore_cols() -> None:
    """Tests ignore cols parameter with nothing to ignore
    i.e pass all features"""

    clmn_map = EvidentlyColumnMapping(target_names=["target"])

    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"], column_mapping=clmn_map
    )

    profile_step = EvidentlyProfileStep()

    drift_obj, dash_obj = profile_step.entrypoint(
        reference_dataset=ref,
        comparison_dataset=comp,
        config=profile_config,
        ignored_columns=(),
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
    assert "ignore_col" in all_cols
    assert "var_A" in all_cols
    assert "var_B" in all_cols


def test_non_existing_col() -> None:
    """Tests ignore cols parameter for non existing
    features and raises Error"""

    clmn_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"], column_mapping=clmn_map
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(ValueError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
            ignored_columns=("var_A", "test_1"),
        )


def test_incorrect_datatype() -> None:
    """Tests ignore cols parameter for incorrect datatype
    and raises Error"""

    clmn_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"], column_mapping=clmn_map
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(TypeError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
            ignored_columns="var_A",
        )


def test_ignored_cols_elements() -> None:
    """Tests ignore cols parameter for type of its elements
    and raises Error"""

    clmn_map = EvidentlyColumnMapping(target_names=["target"])
    profile_config = EvidentlyProfileConfig(
        profile_sections=["datadrift"], column_mapping=clmn_map
    )

    profile_step = EvidentlyProfileStep()

    with pytest.raises(TypeError):
        drift_obj, dash_obj = profile_step.entrypoint(
            reference_dataset=ref,
            comparison_dataset=comp,
            config=profile_config,
            ignored_columns=("Housing", "Region", 25, True),
        )
