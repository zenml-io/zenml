#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Run statistics models."""

from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

from zenml.models.v2.base.base import BaseZenModel
from zenml.models.v2.core.pipeline_run import PipelineRunFilter
from zenml.utils.enum_utils import StrEnum


class StatisticsTimeGranularity(StrEnum):
    """Time bucket granularity for run statistics."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class StatisticsGroupingType(StrEnum):
    """Grouping dimension for run statistics."""

    STATUS = "status"
    PIPELINE = "pipeline"
    SNAPSHOT = "snapshot"
    SOURCE_SNAPSHOT = "source_snapshot"
    STACK = "stack"
    TRIGGER = "trigger"
    USER = "user"
    TIME = "time"
    METADATA = "metadata"
    TAG = "tag"


class StatisticsAggregation(StrEnum):
    """Aggregation operator for run statistics."""

    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"


class StatisticsMetricSource(StrEnum):
    """Value source for a run statistics metric."""

    DURATION = "duration"
    STEP_COUNT = "step_count"
    CACHED_STEP_COUNT = "cached_step_count"
    OUTPUT_ARTIFACT_COUNT = "output_artifact_count"
    METADATA = "metadata"


class _GroupingBase(BaseModel):
    """Run statistics grouping base."""

    name: str = Field(
        description="Output key under `group_keys` in the response. Must be "
        "unique within the request.",
        min_length=1,
    )


class SimpleGrouping(_GroupingBase):
    """Run statistics grouping."""

    type: Literal[
        StatisticsGroupingType.STATUS,
        StatisticsGroupingType.PIPELINE,
        StatisticsGroupingType.SNAPSHOT,
        StatisticsGroupingType.SOURCE_SNAPSHOT,
        StatisticsGroupingType.STACK,
        StatisticsGroupingType.TRIGGER,
        StatisticsGroupingType.USER,
        StatisticsGroupingType.TAG,
    ] = Field(description="Dimension to group runs by.")


class TimeGrouping(_GroupingBase):
    """Run statistics time grouping."""

    type: Literal[StatisticsGroupingType.TIME] = Field(
        description="Dimension to group runs by.",
    )
    granularity: StatisticsTimeGranularity = Field(
        description="Time bucket granularity.",
    )


class MetadataGrouping(_GroupingBase):
    """Run statistics metadata grouping."""

    type: Literal[StatisticsGroupingType.METADATA] = Field(
        description="Dimension to group runs by.",
    )
    metadata_key: str = Field(
        description="Metadata key to group on.",
    )


StatisticsGrouping = Annotated[
    Union[SimpleGrouping, TimeGrouping, MetadataGrouping],
    Field(discriminator="type"),
]


class _MetricBase(BaseModel):
    """Run statistics metric base."""

    name: str = Field(
        description="Output key under `metrics` in the response. Must be "
        "unique within the request.",
        min_length=1,
    )
    aggregation: StatisticsAggregation = Field(
        description="Aggregation operator.",
    )


class SimpleMetric(_MetricBase):
    """Run statistics metric."""

    source: Literal[
        StatisticsMetricSource.DURATION,
        StatisticsMetricSource.STEP_COUNT,
        StatisticsMetricSource.CACHED_STEP_COUNT,
        StatisticsMetricSource.OUTPUT_ARTIFACT_COUNT,
    ] = Field(description="Value source.")


class MetadataMetric(_MetricBase):
    """Run statistics metadata metric."""

    source: Literal[StatisticsMetricSource.METADATA] = Field(
        description="Value source.",
    )
    metadata_key: str = Field(
        description="Metadata key to aggregate.",
    )


StatisticsMetric = Annotated[
    Union[SimpleMetric, MetadataMetric],
    Field(discriminator="source"),
]


class RunStatisticsRequest(BaseZenModel):
    """Run statistics request."""

    filter: PipelineRunFilter = Field(
        description="Pipeline run filter applied before aggregation.",
    )
    groupings: List[StatisticsGrouping] = Field(
        default_factory=list,
        description="Group-by dimensions. Empty list produces a single global "
        "aggregate row.",
    )
    metrics: List[StatisticsMetric] = Field(
        default_factory=list,
        description="Aggregate metrics to compute per group. May be empty if "
        "the caller only wants per-group run counts.",
    )
    max_groups: int = Field(
        default=1000,
        le=10_000,
        gt=0,
        description="Maximum number of groups to return.",
    )

    @model_validator(mode="after")
    def _validate_request(self) -> "RunStatisticsRequest":
        grouping_names = [g.name for g in self.groupings]
        if len(grouping_names) != len(set(grouping_names)):
            raise ValueError("Duplicate grouping names are not allowed.")

        metric_names = [m.name for m in self.metrics]
        if len(metric_names) != len(set(metric_names)):
            raise ValueError("Duplicate metric names are not allowed.")

        time_groupings = sum(
            1 for g in self.groupings if isinstance(g, TimeGrouping)
        )
        if time_groupings > 1:
            raise ValueError("At most one time grouping is allowed.")

        return self


class RunStatisticsGroup(BaseModel):
    """Run statistics group."""

    group_keys: Dict[str, Optional[Union[str, int, float, bool]]] = Field(
        default_factory=dict,
        description="Group key values keyed by grouping name. Empty when the "
        "request had no groupings.",
    )
    metrics: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Metric values keyed by metric name. Null when the group "
        "has no rows contributing to the aggregate.",
    )
    run_count: int = Field(
        description="Distinct pipeline runs in this group.",
    )


class RunStatisticsResponse(BaseZenModel):
    """Run statistics response."""

    groups: List[RunStatisticsGroup] = Field(
        default_factory=list,
        description="Resulting groups. Ordered by time bucket ascending when "
        "a time grouping is present, otherwise by run count descending.",
    )
    truncated: bool = Field(
        default=False,
        description="True when more groups existed than `max_groups` allowed.",
    )
