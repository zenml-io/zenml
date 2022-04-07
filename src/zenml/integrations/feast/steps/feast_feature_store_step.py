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

from typing import Any, Dict, List, Optional, Type, Union

from feast.feature_service import FeatureService  # type: ignore[import]
from pandas import DataFrame

from zenml.steps import BaseStep, BaseStepConfig, StepContext, step


class FeastHistoricalFeaturesConfig(BaseStepConfig):
    """Feast Feature Store historical data step configuration."""

    class Config:
        arbitrary_types_allowed = True


def feast_historical_features_step(
    entity_df: Union[DataFrame, str],
    features: Union[List[str], FeatureService],
    full_feature_names: bool = False,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
) -> Type[BaseStep]:
    """Feast Feature Store historical data step.

    Args:
        entity_df: The entity dataframe or entity name.
        features: The features to retrieve.
        full_feature_names: Whether to return the full feature names.
        name: The name of the step.
        enable_cache: Whether to enable caching.

    Returns:
        A historical features step.
    """

    # enable cache explicitly to compensate for the fact that this step
    # takes in a context object
    if enable_cache is None:
        enable_cache = True

    @step(enable_cache=enable_cache, name=name)
    def feast_historical_features(
        config: FeastHistoricalFeaturesConfig,
        context: StepContext,
    ) -> DataFrame:
        """Feast Feature Store historical data step

        Args:
            config: The step configuration.
            context: The step context.

        Returns:
            The historical features as a DataFrame.
        """
        feature_store_component = context.feature_store

        return feature_store_component.get_historical_features(  # type: ignore[union-attr]
            entity_df=entity_df,
            features=features,
            full_feature_names=full_feature_names,
        )

    return feast_historical_features


class FeastOnlineFeaturesConfig(BaseStepConfig):
    """Feast Feature Store online data step configuration."""

    class Config:
        arbitrary_types_allowed = True


def feast_online_features_step(
    entity_rows: List[Dict[str, Any]],
    features: Union[List[str], FeatureService],
    full_feature_names: bool = False,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
) -> Type[BaseStep]:
    """Feast Feature Store online data step

    Args:
        entity_rows: The entity rows to retrieve.
        features: The features to retrieve.
        full_feature_names: Whether to return the full feature names.
        name: The name of the step.
        enable_cache: Whether to enable caching.

    Returns:
        An online features step.
    """

    # enable cache explicitly to compensate for the fact that this step
    # takes in a context object
    if enable_cache is None:
        enable_cache = True

    @step(enable_cache=enable_cache, name=name)
    def feast_online_features(
        config: FeastHistoricalFeaturesConfig,
        context: StepContext,
    ) -> Dict[str, Any]:
        """Feast Feature Store historical data step

        Args:
            config: The step configuration.
            context: The step context.

        Returns:
            The online features as a dictionary.
        """
        feature_store_component = context.feature_store

        return feature_store_component.get_online_features(  # type: ignore[union-attr]
            entity_rows=entity_rows,
            features=features,
            full_feature_names=full_feature_names,
        )

    return feast_online_features
