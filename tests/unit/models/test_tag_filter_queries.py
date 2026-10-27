"""Validate resource-scoped tag queries and the combined relationship filter limit."""

from typing import Generator
from uuid import NAMESPACE_DNS, uuid5

import pytest
from pydantic import ValidationError
from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    and_,
    create_engine,
    or_,
    select,
)
from sqlalchemy.engine import Connection

from zenml.models import ArtifactFilter, PipelineRunFilter, StepRunFilter
from zenml.models.v2.base.scoped import TaggableFilter


@pytest.fixture
def tag_database() -> Generator[tuple[Connection, type], None, None]:
    """Provide overlapping tags, duplicate associations, and an untagged run.

    Yields:
        An isolated connection and a query target exposing the run ID.
    """
    metadata = MetaData()
    runs = Table("runs", metadata, Column("id", String, primary_key=True))
    tags = Table(
        "tag",
        metadata,
        Column("id", String, primary_key=True),
        Column("name", String),
    )
    links = Table(
        "tag_resource",
        metadata,
        Column("id", String, primary_key=True),
        Column("resource_id", String),
        Column("tag_id", String),
        Column("resource_type", String, default="pipeline_run"),
        Column("created", String),
        Column("updated", String),
    )

    class Run:
        __tablename__ = "pipeline_run"
        id = runs.c.id

    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(runs.insert(), [{"id": str(i)} for i in range(4)])
        connection.execute(
            tags.insert(),
            [
                {"id": uuid5(NAMESPACE_DNS, name).hex, "name": name}
                for name in ["red", "blue"]
            ],
        )
        connection.execute(
            links.insert(),
            [
                {
                    "id": "a",
                    "resource_id": "0",
                    "tag_id": uuid5(NAMESPACE_DNS, "red").hex,
                },
                {
                    "id": "b",
                    "resource_id": "0",
                    "tag_id": uuid5(NAMESPACE_DNS, "blue").hex,
                },
                {
                    "id": "c",
                    "resource_id": "1",
                    "tag_id": uuid5(NAMESPACE_DNS, "red").hex,
                },
                {
                    "id": "d",
                    "resource_id": "2",
                    "tag_id": uuid5(NAMESPACE_DNS, "blue").hex,
                },
                {
                    "id": "e",
                    "resource_id": "1",
                    "tag_id": uuid5(NAMESPACE_DNS, "red").hex,
                },
            ],
        )
        connection.execute(
            links.insert(),
            {
                "id": "wrong-type",
                "resource_id": "3",
                "tag_id": uuid5(NAMESPACE_DNS, "red").hex,
                "resource_type": "artifact",
            },
        )
        yield connection, Run
    engine.dispose()


@pytest.mark.parametrize(
    "values,operator,expected",
    [
        (["red", "blue", "contains:e", "startswith:r"], "and", {"0"}),
        (["red", "red", "contains:e", "startswith:r"], "and", {"0", "1"}),
        (["missing", "red", "blue", "startswith:r"], "and", set()),
        (["red", "blue", "missing", "startswith:r"], "or", {"0", "1", "2"}),
        (
            [
                'oneof:["red","blue"]',
                'notoneof:["blue"]',
                "contains:e",
                "startswith:r",
            ],
            "and",
            {"0", "1"},
        ),
        (["isnull:", "red", "red", "red"], "or", {"0", "1", "3"}),
        (
            ["isnotnull:", "red", "contains:e", "startswith:r"],
            "and",
            {"0", "1"},
        ),
    ],
)
def test_tag_strategy_results(
    tag_database: tuple[Connection, type],
    values: list[str],
    operator: str,
    expected: set[str],
) -> None:
    """Preserve tag predicates and ignore associations of other resource types."""
    connection, table = tag_database
    filters = TaggableFilter(tags=values, logical_operator=operator)
    combine = and_ if operator == "and" else or_
    query = select(table.id).where(combine(*filters.get_custom_filters(table)))
    assert set(connection.execute(query).scalars()) == expected


@pytest.mark.parametrize("count", [3, 4, 8])
@pytest.mark.parametrize("operator", ["and", "or"])
def test_separate_tag_lookups(count: int, operator: str) -> None:
    """Keep a separate EXISTS for each predicate for either logical operator."""
    from zenml.zen_stores.schemas import PipelineRunSchema

    conditions = TaggableFilter(
        tags=[f"tag-{i}" for i in range(count)], logical_operator=operator
    ).get_custom_filters(PipelineRunSchema)
    assert len(conditions) == count
    assert all("GROUP BY" not in str(condition) for condition in conditions)


@pytest.mark.parametrize(
    "schema_name,resource_type",
    [
        ("ArtifactSchema", "artifact"),
        ("ArtifactVersionSchema", "artifact_version"),
        ("ModelSchema", "model"),
        ("ModelVersionSchema", "model_version"),
        ("PipelineSchema", "pipeline"),
        ("PipelineRunSchema", "pipeline_run"),
        ("RunTemplateSchema", "run_template"),
        ("PipelineSnapshotSchema", "pipeline_snapshot"),
        ("DeploymentSchema", "deployment"),
    ],
)
@pytest.mark.parametrize(
    "tags", [["red"], ["red"] * 4, ["isnull:"], ["isnotnull:"]]
)
def test_tag_resource_types(
    schema_name: str, resource_type: str, tags: list[str]
) -> None:
    """Constrain association lookups to the resource type of every taggable table."""
    from zenml.zen_stores import schemas

    table = vars(schemas)[schema_name]
    filters = TaggableFilter(tags=tags).get_custom_filters(table)
    for condition in filters:
        compiled = condition.compile()
        assert "tag_resource.resource_type =" in str(compiled)
        assert resource_type in compiled.params.values()


@pytest.mark.parametrize(
    "tags,metadata",
    [
        (8, 0),
        (0, 8),
        (4, 4),
        (1, 7),
        (0, 0),
        (9, 0),
        (0, 9),
        (4, 5),
        (8, 1),
    ],
)
@pytest.mark.parametrize("operator", ["and", "or"])
def test_combined_limit(tags: int, metadata: int, operator: str) -> None:
    """Enforce the combined expression limit for both logical operators."""
    values = dict(
        tags=["red"] * tags,
        run_metadata=["color:red"] * metadata,
        logical_operator=operator,
    )
    if tags + metadata > 8:
        with pytest.raises(
            ValidationError, match="allowed combined; received 9"
        ):
            PipelineRunFilter.model_validate(values)
    else:
        PipelineRunFilter.model_validate(values)


@pytest.mark.parametrize(
    "model,field,value",
    [
        (ArtifactFilter, "tags", "red"),
        (StepRunFilter, "run_metadata", "color:red"),
    ],
)
def test_single_family_limit(model: type, field: str, value: str) -> None:
    """Enforce the limit after tuple normalization in single-family models."""
    model.model_validate({field: (value,) * 8})
    with pytest.raises(ValidationError, match="received 9"):
        model.model_validate({field: (value,) * 9})


def test_expression_count() -> None:
    """Count strings and oneof lists as one expression each."""
    PipelineRunFilter(
        tags='oneof:["a","b","c","d","e","f","g","h","i","j","k"]',
        run_metadata=["key:value"] * 7,
    )
    with pytest.raises(ValidationError, match="received 9"):
        PipelineRunFilter(tags="red", run_metadata=["key:value"] * 8)


@pytest.mark.parametrize("operator", ["and", "or"])
@pytest.mark.parametrize("expression", ["red", "contains:e", "isnull:"])
def test_duplicate_tag_expressions(
    tag_database: tuple[Connection, type], operator: str, expression: str
) -> None:
    """Deduplicate SQL predicates without mutating input or changing results."""
    connection, table = tag_database
    values = [expression, expression, "blue"]
    model = TaggableFilter(tags=values, logical_operator=operator)
    conditions = model.get_custom_filters(table)
    assert len(conditions) == 2
    assert model.tags == values
    combine = and_ if operator == "and" else or_
    original = TaggableFilter(
        tags=[expression, "blue"], logical_operator=operator
    )
    expected = select(table.id).where(
        combine(*original.get_custom_filters(table))
    )
    actual = select(table.id).where(combine(*conditions))
    assert set(connection.execute(actual).scalars()) == set(
        connection.execute(expected).scalars()
    )
