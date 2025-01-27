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

from zenml import step

FULL_FEATURE_NAMES = [
    name.lower()
    for name in [
        "X_Minimum",
        "X_Maximum",
        "Y_Minimum",
        "Y_Maximum",
        "Pixels_Areas",
        "X_Perimeter",
        "Y_Perimeter",
        "Sum_of_Luminosity",
        "Minimum_of_Luminosity",
        "Maximum_of_Luminosity",
        "Length_of_Conveyer",
        "TypeOfSteel_A300",
        "TypeOfSteel_A400",
        "Steel_Plate_Thickness",
        "Edges_Index",
        "Empty_Index",
        "Square_Index",
        "Outside_X_Index",
        "Edges_X_Index",
        "Edges_Y_Index",
        "Outside_Global_Index",
        "LogOfAreas",
        "Log_X_Index",
        "Log_Y_Index",
        "Orientation_Index",
        "Luminosity_Index",
        "SigmoidOfAreas",
        "Pastry",
        "Z_Scratch",
        "K_Scatch",
        "Stains",
        "Dirtiness",
        "Bumps",
        "Other_Faults",
    ]
]


@step
def importer() -> pd.DataFrame:
    """Import the Steel Plates Fault Dataset from UCI.

    The Steel Plates Faults Data Set is provided by Semeion, Research Center of
    Sciences of Communication, Via Sersale 117, 00128, Rome, Italy.
    Source: UCI Machine Learning Repository
    (https://archive.ics.uci.edu/ml/datasets/Steel+Plates+Faults)

    Returns:
        pd.DataFrame: the steel plates fault dataset.
    """
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00198/Faults.NNA"
    df = pd.read_csv(url, header=None, sep="\t")

    # The last 7 columns are the fault types (target variables)
    target_cols = df.iloc[:, -7:].idxmax(axis=1)
    df = df.iloc[:, :-7]  # Remove the one-hot encoded target columns

    # Assign column names
    df.columns = FULL_FEATURE_NAMES[:-7]  # Exclude the fault type names
    df["target"] = target_cols

    return df
