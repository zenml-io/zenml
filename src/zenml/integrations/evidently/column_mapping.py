#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""ZenML representation of an Evidently column mapping."""

from collections.abc import Sequence

from evidently import ColumnMapping  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field


class EvidentlyColumnMapping(BaseModel):
    """Column mapping configuration for Evidently.

    This class is a 1-to-1 serializable analogue of Evidently's
    ColumnMapping data type that can be used as a step configuration field
    (see https://docs.evidentlyai.com/user-guide/input-data/column-mapping).

    Attributes:
        target: target column
        prediction: target column
        datetime: datetime column
        id: id column
        numerical_features: numerical features
        categorical_features: categorical features
        datetime_features: datetime features
        target_names: target column names
        task: model task
        pos_label: positive label
        text_features: text features
    """

    target: str | None = None
    prediction: str | Sequence[str] | None = Field(
        default="prediction", union_mode="left_to_right"
    )
    datetime: str | None = None
    id: str | None = None
    numerical_features: list[str] | None = None
    categorical_features: list[str] | None = None
    datetime_features: list[str] | None = None
    target_names: list[str] | None = None
    task: str | None = None
    pos_label: str | int | None = Field(
        default=1, union_mode="left_to_right"
    )
    text_features: list[str] | None = None

    model_config = ConfigDict(
        validate_assignment=True,
    )

    def to_evidently_column_mapping(self) -> ColumnMapping:
        """Convert this Pydantic object to an Evidently ColumnMapping object.

        Returns:
            An Evidently column mapping converted from this Pydantic object.
        """
        column_mapping = ColumnMapping()

        # preserve the Evidently defaults where possible
        column_mapping.target = self.target or column_mapping.target
        column_mapping.prediction = (
            self.prediction or column_mapping.prediction
        )
        column_mapping.datetime = self.datetime or column_mapping.datetime
        column_mapping.id = self.id or column_mapping.id
        column_mapping.numerical_features = (
            self.numerical_features or column_mapping.numerical_features
        )
        column_mapping.datetime_features = (
            self.datetime_features or column_mapping.datetime_features
        )
        column_mapping.target_names = (
            self.target_names or column_mapping.target_names
        )
        column_mapping.task = self.task or column_mapping.task
        column_mapping.pos_label = self.pos_label or column_mapping.pos_label
        column_mapping.text_features = (
            self.text_features or column_mapping.text_features
        )

        return column_mapping
