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

from typing import Any, List, Union

import pandas as pd
from feast import FeatureStore  # type: ignore[import]
from feast.feature_service import FeatureService  # type: ignore[import]

from zenml.steps.step_interfaces.base_datasource_step import (
    BaseDatasourceConfig,
    BaseDatasourceStep,
)


class FeastHistoricalDatasourceConfig(BaseDatasourceConfig):
    """Config class for the Feast datasource."""

    class Config:
        arbitrary_types_allowed = True

    repo_path: str


class FeastHistoricalDatasource(BaseDatasourceStep):
    """Simple step implementation to ingest batch or historical data from a
    Feast data source."""

    def __init__(
        self,
        *args: Any,
        entity_df: Union[pd.DataFrame, str],
        features: Union[List[str], FeatureService],
        full_feature_names: bool = False,
        **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.entity_df = entity_df
        self.features = features
        self.full_feature_names = full_feature_names

    def entrypoint(  # type: ignore[override]
        self,
        config: FeastHistoricalDatasourceConfig,
    ) -> pd.DataFrame:
        """Main entrypoint method for the FeastDatasource.

        Args:
            config: the configuration of the step
        Returns:
            the resulting dataframe
        """
        fs_interface = FeatureStore(repo_path=config.repo_path)

        return fs_interface.get_historical_features(
            entity_df=self.entity_df,
            features=self.features,
            full_feature_names=self.full_feature_names,
        ).to_df()


# class FeastOnlineDatasourceConfig(BaseDatasourceConfig):
#     """Config class for the Feast datasource."""

#     repo_path: str


# class FeastOnlineDatasource(BaseDatasourceStep):
#     """Simple step implementation to ingest batch or historical data from a
#     Feast data source."""

#     def entrypoint(
#         self, config=FeastOnlineDatasourceConfig
#     ) -> Optional[pd.DataFrame]:
#         """Main entrypoint method for the FeastDatasource.

#         Args:
#             config: the configuration of the step
#         Returns:
#             the resulting dataframe
#         """
#         return NotImplementedError
