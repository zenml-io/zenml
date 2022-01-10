#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import Dict

import pandas as pd
from sklearn.model_selection import train_test_split

from zenml.steps import Output
from zenml.steps.step_interfaces.base_split_step import (
    BaseSplitStep,
    BaseSplitStepConfig,
)


class SklearnSplitterConfig(BaseSplitStepConfig):
    """Config class for the sklearn splitter"""

    ratios: Dict[str, float]


class SklearnSplitter(BaseSplitStep):
    """A simple step implementation which utilizes sklearn to split a given
    dataset into train, test and validation splits"""

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        config: SklearnSplitterConfig,
    ) -> Output(  # type:ignore[valid-type]
        train=pd.DataFrame, test=pd.DataFrame, validation=pd.DataFrame
    ):
        """Method which is responsible for the splitting logic

        Args:
            dataset: a pandas Dataframe which entire dataset
            config: the configuration for the step
        Returns:
            three dataframes representing the splits
        """
        if (
            any(
                [
                    split not in config.ratios
                    for split in ["train", "test", "validation"]
                ]
            )
            or len(config.ratios) != 3
        ):
            raise KeyError(
                f"Make sure that you only use 'train', 'test' and "
                f"'validation' as keys in the ratios dict. Current keys: "
                f"{config.ratios.keys()}"
            )

        if sum(config.ratios.values()) != 1:
            raise ValueError(
                f"Make sure that the ratios sum up to 1. Current "
                f"ratios: {config.ratios}"
            )

        train_dataset, test_dataset = train_test_split(
            dataset, test_size=config.ratios["test"]
        )

        train_dataset, val_dataset = train_test_split(
            train_dataset,
            test_size=(
                config.ratios["validation"]
                / (config.ratios["validation"] + config.ratios["train"])
            ),
        )

        return train_dataset, test_dataset, val_dataset
