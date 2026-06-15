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
"""SQL aggregation query for pipeline run statistics."""

import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from sqlalchemy import Numeric, case, distinct, func, text
from sqlalchemy import cast as sql_cast
from sqlalchemy.engine import Row
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Subquery
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select

from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    TaggableResourceTypes,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    MetadataGrouping,
    MetadataMetric,
    RunStatisticsGroup,
    RunStatisticsRequest,
    RunStatisticsResponse,
    SimpleGrouping,
    SimpleMetric,
    StatisticsAggregation,
    StatisticsGroupingType,
    StatisticsMetricSource,
    StatisticsTimeGranularity,
    TimeGrouping,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    StepRunOutputArtifactSchema,
    StepRunSchema,
    TagResourceSchema,
    TagSchema,
    TriggerExecutionSchema,
)
from zenml.zen_stores.sql_zen_store import SQLDatabaseDriver

JsonScalar = Optional[Union[str, int, float, bool]]
GroupingDecoder = Callable[[Any], JsonScalar]
Grouping = Union[SimpleGrouping, TimeGrouping, MetadataGrouping]
Metric = Union[SimpleMetric, MetadataMetric]

_SIMPLE_GROUPING_COLUMNS: Dict[StatisticsGroupingType, str] = {
    StatisticsGroupingType.STATUS: "status",
    StatisticsGroupingType.PIPELINE: "pipeline_id",
    StatisticsGroupingType.SNAPSHOT: "snapshot_id",
    StatisticsGroupingType.SOURCE_SNAPSHOT: "source_snapshot_id",
    StatisticsGroupingType.STACK: "stack_id",
    StatisticsGroupingType.TRIGGER: "trigger_id",
    StatisticsGroupingType.USER: "user_id",
}

_SIMPLE_METRIC_COLUMNS: Dict[StatisticsMetricSource, str] = {
    StatisticsMetricSource.DURATION: "duration_seconds",
    StatisticsMetricSource.STEP_COUNT: "step_count",
    StatisticsMetricSource.CACHED_STEP_COUNT: "cached_step_count",
    StatisticsMetricSource.OUTPUT_ARTIFACT_COUNT: "output_artifact_count",
}

_AGGREGATE_FUNCTIONS: Dict[StatisticsAggregation, Any] = {
    StatisticsAggregation.AVG: func.avg,
    StatisticsAggregation.SUM: func.sum,
    StatisticsAggregation.MIN: func.min,
    StatisticsAggregation.MAX: func.max,
}


def compute_run_statistics(
    session: Session,
    request: RunStatisticsRequest,
    driver: Optional[SQLDatabaseDriver],
) -> RunStatisticsResponse:
    """Aggregate pipeline run statistics for the request.

    Args:
        session: Open SQL session, scoped to the request's project.
        request: Statistics request.
        driver: SQL dialect.

    Returns:
        Grouped statistics.
    """
    runs_subquery = _filtered_runs_subquery(request=request, driver=driver)
    query, decoders, reverse_for_display = _aggregation_query(
        request=request, runs_subquery=runs_subquery, driver=driver
    )

    rows = session.execute(query).all()
    truncated = len(rows) > request.max_groups
    if truncated:
        rows = rows[: request.max_groups]

    if reverse_for_display:
        rows = list(reversed(rows))

    return RunStatisticsResponse(
        groups=[
            _row_to_group(row=row, request=request, decoders=decoders)
            for row in rows
        ],
        truncated=truncated,
    )


def _filtered_runs_subquery(
    request: RunStatisticsRequest,
    driver: Optional[SQLDatabaseDriver],
) -> Subquery:
    """One row per filtered pipeline run with grouping and metric values.

    Args:
        request: Statistics request.
        driver: SQL dialect.

    Returns:
        Subquery.
    """
    grouping_types = {g.type for g in request.groupings}
    metric_sources = {m.source for m in request.metrics}

    columns: List[ColumnElement[Any]] = [
        col(PipelineRunSchema.id).label("run_id"),
        col(PipelineRunSchema.status).label("status"),
        col(PipelineRunSchema.pipeline_id).label("pipeline_id"),
        col(PipelineRunSchema.snapshot_id).label("snapshot_id"),
        col(PipelineRunSchema.user_id).label("user_id"),
        col(PipelineRunSchema.start_time).label("start_time"),
        _duration_seconds_expression(driver).label("duration_seconds"),
    ]
    needs_snapshot_join = False
    if StatisticsGroupingType.SOURCE_SNAPSHOT in grouping_types:
        needs_snapshot_join = True
        columns.append(
            col(PipelineSnapshotSchema.source_snapshot_id).label(
                "source_snapshot_id"
            )
        )

    if StatisticsGroupingType.STACK in grouping_types:
        needs_snapshot_join = True
        columns.append(col(PipelineSnapshotSchema.stack_id).label("stack_id"))

    needs_trigger_join = False
    if StatisticsGroupingType.TRIGGER in grouping_types:
        needs_trigger_join = True
        columns.append(
            col(TriggerExecutionSchema.trigger_id).label("trigger_id")
        )

    step_aggregates_subquery = _step_aggregates_subquery(metric_sources)
    if step_aggregates_subquery is not None:
        if StatisticsMetricSource.STEP_COUNT in metric_sources:
            columns.append(
                func.coalesce(step_aggregates_subquery.c.step_count, 0).label(
                    "step_count"
                )
            )

        if StatisticsMetricSource.CACHED_STEP_COUNT in metric_sources:
            columns.append(
                func.coalesce(
                    step_aggregates_subquery.c.cached_step_count, 0
                ).label("cached_step_count")
            )

        if StatisticsMetricSource.OUTPUT_ARTIFACT_COUNT in metric_sources:
            columns.append(
                func.coalesce(
                    step_aggregates_subquery.c.output_artifact_count, 0
                ).label("output_artifact_count")
            )

    metadata_subqueries: Dict[str, Subquery] = {
        key: _metadata_subquery(key)
        for key in dict.fromkeys(
            [
                g.metadata_key
                for g in request.groupings
                if isinstance(g, MetadataGrouping)
            ]
            + [
                m.metadata_key
                for m in request.metrics
                if isinstance(m, MetadataMetric)
            ]
        )
    }
    for key, metadata_subquery in metadata_subqueries.items():
        columns.append(metadata_subquery.c.value.label(f"md_value_{key}"))
        columns.append(
            _metadata_value_as_float(
                metadata_subquery=metadata_subquery
            ).label(f"md_numeric_{key}")
        )

    # PipelineRunFilter.tags fans rows out per matching tag. Resolve filters
    # on a distinct id query first so the result stays one row per run.
    filtered_ids = (
        request.filter.apply_filter(
            query=select(col(PipelineRunSchema.id)),
            table=PipelineRunSchema,
        )
        .distinct()
        .subquery("filtered_run_ids")
    )

    query = (
        select(*columns)
        .select_from(PipelineRunSchema)
        .where(col(PipelineRunSchema.id).in_(select(filtered_ids.c.id)))
    )
    if needs_snapshot_join:
        query = query.outerjoin(
            PipelineSnapshotSchema,
            col(PipelineSnapshotSchema.id)
            == col(PipelineRunSchema.snapshot_id),
        )

    if needs_trigger_join:
        # PK (trigger_id, pipeline_run_id) ensures at most one row per run.
        query = query.outerjoin(
            TriggerExecutionSchema,
            col(TriggerExecutionSchema.pipeline_run_id)
            == col(PipelineRunSchema.id),
        )

    if step_aggregates_subquery is not None:
        query = query.outerjoin(
            step_aggregates_subquery,
            step_aggregates_subquery.c.run_id == col(PipelineRunSchema.id),
        )

    for metadata_subquery in metadata_subqueries.values():
        query = query.outerjoin(
            metadata_subquery,
            metadata_subquery.c.run_id == col(PipelineRunSchema.id),
        )

    return query.subquery("runs")


def _aggregation_query(
    request: RunStatisticsRequest,
    runs_subquery: Subquery,
    driver: Optional[SQLDatabaseDriver],
) -> Tuple[Any, List[GroupingDecoder], bool]:
    """Aggregating SELECT over the runs subquery.

    Args:
        request: Statistics request.
        runs_subquery: Filtered runs subquery.
        driver: SQL dialect.

    Returns:
        Query, one decoder per request grouping, and a flag set when the
        fetched rows should be reversed for the response.
    """
    tag_subquery = (
        _tag_subquery()
        if any(g.type == StatisticsGroupingType.TAG for g in request.groupings)
        else None
    )

    group_columns: List[ColumnElement[Any]] = []
    decoders: List[GroupingDecoder] = []
    for grouping in request.groupings:
        expression, decoder = _grouping_expression(
            grouping=grouping,
            runs=runs_subquery,
            tag_subquery=tag_subquery,
            driver=driver,
        )
        group_columns.append(expression.label(f"group_{grouping.name}"))
        decoders.append(decoder)

    metric_columns: List[ColumnElement[Any]] = []
    for metric in request.metrics:
        value = _metric_value_expression(metric=metric, runs=runs_subquery)
        metric_columns.append(
            _AGGREGATE_FUNCTIONS[metric.aggregation](value).label(
                f"metric_{metric.name}"
            )
        )

    run_count = func.count(distinct(runs_subquery.c.run_id)).label("run_count")
    select_columns: List[ColumnElement[Any]] = [
        *group_columns,
        *metric_columns,
        run_count,
    ]

    query = select(*select_columns).select_from(runs_subquery)
    if tag_subquery is not None:
        query = query.outerjoin(
            tag_subquery, tag_subquery.c.run_id == runs_subquery.c.run_id
        )

    if group_columns:
        query = query.group_by(*group_columns)

    # Time-grouped queries order everything DESC so the LIMIT keeps the
    # latest buckets when truncation kicks in. The kept slice is then
    # reversed by the caller so the response is ascending by time. Non-time
    # queries order by run count DESC with groupings ASC as tiebreakers.
    # Request validation guarantees at most one time grouping.
    time_index = next(
        (
            i
            for i, g in enumerate(request.groupings)
            if isinstance(g, TimeGrouping)
        ),
        None,
    )
    if time_index is not None:
        primary_order: Any = group_columns[time_index].desc()
        tiebreakers = [
            c.desc() for i, c in enumerate(group_columns) if i != time_index
        ]
        reverse_for_display = True
    else:
        primary_order = run_count.desc()
        tiebreakers = [c.asc() for c in group_columns]
        reverse_for_display = False

    query = query.order_by(primary_order, *tiebreakers)
    query = query.limit(request.max_groups + 1)

    return query, decoders, reverse_for_display


def _grouping_expression(
    grouping: Grouping,
    runs: Subquery,
    tag_subquery: Optional[Subquery],
    driver: Optional[SQLDatabaseDriver],
) -> Tuple[ColumnElement[Any], GroupingDecoder]:
    """GROUP BY expression and row decoder for one grouping.

    Args:
        grouping: Request grouping.
        runs: Filtered runs subquery.
        tag_subquery: Tag join subquery, present when any grouping is TAG.
        driver: SQL dialect.

    Returns:
        GROUP BY expression and decoder for the row value.
    """
    if isinstance(grouping, TimeGrouping):
        return (
            _time_bucket_expression(
                column=runs.c.start_time,
                granularity=grouping.granularity,
                driver=driver,
            ),
            _to_json_scalar,
        )

    if isinstance(grouping, MetadataGrouping):
        return (
            runs.c[f"md_value_{grouping.metadata_key}"],
            _decode_metadata_value,
        )

    if grouping.type == StatisticsGroupingType.TAG:
        assert tag_subquery is not None
        return tag_subquery.c.name, _to_json_scalar

    return runs.c[_SIMPLE_GROUPING_COLUMNS[grouping.type]], _to_json_scalar


def _metric_value_expression(
    metric: Metric, runs: Subquery
) -> ColumnElement[Any]:
    """Per-run scalar the metric aggregates over.

    Args:
        metric: Request metric.
        runs: Filtered runs subquery.

    Returns:
        Column expression.
    """
    if isinstance(metric, MetadataMetric):
        return runs.c[f"md_numeric_{metric.metadata_key}"]

    return runs.c[_SIMPLE_METRIC_COLUMNS[metric.source]]


def _row_to_group(
    row: Row[Any],
    request: RunStatisticsRequest,
    decoders: List[GroupingDecoder],
) -> RunStatisticsGroup:
    """Convert a result row into a typed response group.

    Args:
        row: Aggregation result row.
        request: Statistics request.
        decoders: One decoder per request grouping.

    Returns:
        Response group.
    """
    mapping = row._mapping
    group_keys: Dict[str, JsonScalar] = {
        grouping.name: decoder(mapping[f"group_{grouping.name}"])
        for grouping, decoder in zip(request.groupings, decoders)
    }
    metrics: Dict[str, Optional[float]] = {}
    for metric in request.metrics:
        raw = mapping[f"metric_{metric.name}"]
        metrics[metric.name] = float(raw) if raw is not None else None

    return RunStatisticsGroup(
        group_keys=group_keys,
        metrics=metrics,
        run_count=int(mapping["run_count"] or 0),
    )


def _to_json_scalar(raw: Any) -> JsonScalar:
    """Coerce a raw DB value to a JSON scalar, stringifying non-scalars.

    Args:
        raw: Raw DB value.

    Returns:
        JSON scalar.
    """
    if raw is None:
        return None

    if isinstance(raw, (str, int, float, bool)):
        return raw

    return str(raw)


def _decode_metadata_value(raw: Any) -> JsonScalar:
    """Decode a JSON-encoded metadata value, returning None if not a scalar.

    Args:
        raw: Raw DB value.

    Returns:
        JSON scalar.
    """
    if raw is None:
        return None

    try:
        decoded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    if decoded is None or isinstance(decoded, (str, int, float, bool)):
        return decoded

    return None


def _duration_seconds_expression(
    driver: Optional[SQLDatabaseDriver],
) -> ColumnElement[float]:
    """Dialect-appropriate `end_time - start_time` in seconds.

    Args:
        driver: SQL dialect.

    Returns:
        Column expression.
    """
    start = col(PipelineRunSchema.start_time)
    end = col(PipelineRunSchema.end_time)
    if driver == SQLDatabaseDriver.MYSQL:
        return func.timestampdiff(text("SECOND"), start, end)

    return (func.julianday(end) - func.julianday(start)) * 86400.0


def _time_bucket_expression(
    column: ColumnElement[Any],
    granularity: StatisticsTimeGranularity,
    driver: Optional[SQLDatabaseDriver],
) -> ColumnElement[str]:
    """Expression for a sortable bucket label for a datetime column.

    WEEK buckets use the Monday of the week as a `YYYY-MM-DD` date.

    Args:
        column: Datetime column.
        granularity: Bucket size.
        driver: SQL dialect.

    Returns:
        String column expression.
    """
    if driver == SQLDatabaseDriver.MYSQL:
        if granularity == StatisticsTimeGranularity.WEEK:
            return func.date_format(
                func.subdate(column, func.weekday(column)), "%Y-%m-%d"
            )

        mysql_formats = {
            StatisticsTimeGranularity.HOUR: "%Y-%m-%d %H:00:00",
            StatisticsTimeGranularity.DAY: "%Y-%m-%d",
            StatisticsTimeGranularity.MONTH: "%Y-%m-01",
        }
        return func.date_format(column, mysql_formats[granularity])

    if granularity == StatisticsTimeGranularity.WEEK:
        return func.date(column, "-6 days", "weekday 1")

    sqlite_formats = {
        StatisticsTimeGranularity.HOUR: "%Y-%m-%d %H:00:00",
        StatisticsTimeGranularity.DAY: "%Y-%m-%d",
        StatisticsTimeGranularity.MONTH: "%Y-%m-01",
    }
    return func.strftime(sqlite_formats[granularity], column)


def _metadata_subquery(key: str) -> Subquery:
    """Subquery that returns metadata entries for a given key.

    If multiple entries exist for the same run, the latest by `created` is
    returned. This mirrors the behavior of metadata overwriting, which only
    keeps the latest entry for scalar metadata values.
    -> See `RunMetadataInterface.fetch_metadata` for more details.

    Args:
        key: Metadata key.

    Returns:
        Subquery with `run_id`, `value`, `type` columns.
    """
    metadata = aliased(RunMetadataSchema)
    metadata_resource = aliased(RunMetadataResourceSchema)
    ranked = (
        select(
            col(metadata_resource.resource_id).label("run_id"),
            col(metadata.value).label("value"),
            col(metadata.type).label("type"),
            func.row_number()
            .over(
                partition_by=col(metadata_resource.resource_id),
                order_by=col(metadata.created).desc(),
            )
            .label("rn"),
        )
        .select_from(metadata)
        .join(
            metadata_resource,
            col(metadata_resource.run_metadata_id) == col(metadata.id),
        )
        .where(
            col(metadata_resource.resource_type)
            == MetadataResourceTypes.PIPELINE_RUN.value,
            col(metadata.key) == key,
        )
        .subquery()
    )

    return (
        select(ranked.c.run_id, ranked.c.value, ranked.c.type)
        .where(ranked.c.rn == 1)
        .subquery()
    )


def _metadata_value_as_float(
    metadata_subquery: Subquery,
) -> ColumnElement[Any]:
    """Metadata value cast to FLOAT when stored type is numeric, else NULL.

    Args:
        metadata_subquery: Subquery with `value` and `type` columns.

    Returns:
        Column expression.
    """
    return case(
        (
            metadata_subquery.c.type.in_(
                (MetadataTypeEnum.INT.value, MetadataTypeEnum.FLOAT.value)
            ),
            sql_cast(metadata_subquery.c.value, Numeric),
        ),
        else_=None,
    )


def _tag_subquery() -> Subquery:
    """Tag subquery that joins pipeline runs with their tags.

    Returns:
        Subquery with `run_id` and `name` columns.
    """
    tag_resource = aliased(TagResourceSchema)
    tag = aliased(TagSchema)

    return (
        select(
            col(tag_resource.resource_id).label("run_id"),
            col(tag.name).label("name"),
        )
        .select_from(tag_resource)
        .join(tag, col(tag.id) == col(tag_resource.tag_id))
        .where(
            col(tag_resource.resource_type)
            == TaggableResourceTypes.PIPELINE_RUN.value
        )
        .subquery()
    )


def _step_aggregates_subquery(
    metric_sources: Set[StatisticsMetricSource],
) -> Optional[Subquery]:
    """Step-run aggregates needed by step-derived metrics.

    Args:
        metric_sources: Metric sources requested.

    Returns:
        Subquery with `run_id` and the requested aggregate columns, or
        `None` if no step-derived metric was requested.
    """
    need_step_count = StatisticsMetricSource.STEP_COUNT in metric_sources
    need_cached_step_count = (
        StatisticsMetricSource.CACHED_STEP_COUNT in metric_sources
    )
    need_output_artifact_count = (
        StatisticsMetricSource.OUTPUT_ARTIFACT_COUNT in metric_sources
    )
    if not (
        need_step_count or need_cached_step_count or need_output_artifact_count
    ):
        return None

    columns: List[ColumnElement[Any]] = [
        col(StepRunSchema.pipeline_run_id).label("run_id"),
    ]
    if need_step_count:
        columns.append(
            func.count(distinct(col(StepRunSchema.name))).label("step_count")
        )

    if need_cached_step_count:
        columns.append(
            func.count(
                distinct(
                    case(
                        (
                            col(StepRunSchema.status)
                            == ExecutionStatus.CACHED.value,
                            col(StepRunSchema.name),
                        ),
                        else_=None,
                    )
                )
            ).label("cached_step_count")
        )

    if need_output_artifact_count:
        columns.append(
            func.count(
                distinct(col(StepRunOutputArtifactSchema.artifact_id))
            ).label("output_artifact_count")
        )

    query = select(*columns).select_from(StepRunSchema)
    if need_output_artifact_count:
        query = query.outerjoin(
            StepRunOutputArtifactSchema,
            col(StepRunOutputArtifactSchema.step_id) == col(StepRunSchema.id),
        )

    return query.group_by(col(StepRunSchema.pipeline_run_id)).subquery()
