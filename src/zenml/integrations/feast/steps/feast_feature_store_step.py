#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from typing import List, Optional, Type, Union

from feast.feature_service import FeatureService  # type: ignore[import]
from pandas import DataFrame

from zenml.steps import BaseStep, BaseStepConfig, StepContext, step


class FeastFeatureStoreConfig(BaseStepConfig):
    """Feast Feature Store step configuration."""

    class Config:
        arbitrary_types_allowed = True

    # entity_df: Union[DataFrame, str]
    # features: Union[List[str], FeatureService]
    # full_feature_names: bool = False


def feast_feature_store_step(
    entity_df: Union[DataFrame, str],
    features: Union[List[str], FeatureService],
    full_feature_names: bool = False,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
) -> Type[BaseStep]:
    """Feast Feature Store step"""

    # enable cache explicitly to compensate for the fact that this step
    # takes in a context object
    if enable_cache is None:
        enable_cache = True

    @step(enable_cache=enable_cache, name=name)
    def feast_feature_store(
        config: FeastFeatureStoreConfig,
        context: StepContext,
    ) -> DataFrame:
        """Feast Feature Store step"""
        feature_store_component = context.feature_store

        return feature_store_component.get_historical_features(  # type: ignore[union-attr]
            entity_df=entity_df,
            features=features,
            full_feature_names=full_feature_names,
        )

    return feast_feature_store
