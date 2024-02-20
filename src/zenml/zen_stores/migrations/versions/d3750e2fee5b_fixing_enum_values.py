"""fixing enum values [d3750e2fee5b].

Revision ID: d3750e2fee5b
Revises: 0.55.3
Create Date: 2024-02-20 10:50:54.030377

"""
from enum import Enum
from typing import List

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d3750e2fee5b"
down_revision = "0.55.3"
branch_labels = None
depends_on = None


# Snapshot of the ZenML Enums at 0.55.3
class StrEnum(str, Enum):
    """Base enum type for string enum values."""

    def __str__(self) -> str:
        """Returns the enum string value.

        Returns:
            The enum string value.
        """
        return self.value  # type: ignore

    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names as a list of strings.

        Returns:
            A list of all enum names.
        """
        return [c.name for c in cls]

    @classmethod
    def values(cls) -> List[str]:
        """Get all enum values as a list of strings.

        Returns:
            A list of all enum values.
        """
        return [c.value for c in cls]


class ArtifactType(StrEnum):
    """All possible types an artifact can have."""

    DATA_ANALYSIS = "DataAnalysisArtifact"
    DATA = "DataArtifact"
    MODEL = "ModelArtifact"
    SCHEMA = "SchemaArtifact"  # deprecated
    SERVICE = "ServiceArtifact"
    STATISTICS = "StatisticsArtifact"  # deprecated in favor of `DATA_ANALYSIS`
    BASE = "BaseArtifact"


class StepRunInputArtifactType(StrEnum):
    """All possible types of a step run input artifact."""

    DEFAULT = "default"  # input argument that is the output of a previous step
    MANUAL = "manual"  # manually loaded via `zenml.load_artifact()`


class StepRunOutputArtifactType(StrEnum):
    """All possible types of a step run output artifact."""

    DEFAULT = "default"  # output of the current step
    MANUAL = "manual"  # manually saved via `zenml.save_artifact()`


class VisualizationType(StrEnum):
    """All currently available visualization types."""

    CSV = "csv"
    HTML = "html"
    IMAGE = "image"
    MARKDOWN = "markdown"


class ExecutionStatus(StrEnum):
    """Enum that represents the current status of a step or pipeline run."""

    INITIALIZING = "initializing"
    FAILED = "failed"
    COMPLETED = "completed"
    RUNNING = "running"
    CACHED = "cached"

    @property
    def is_finished(self) -> bool:
        """Whether the execution status refers to a finished execution.

        Returns:
            Whether the execution status refers to a finished execution.
        """
        return self in {
            ExecutionStatus.FAILED,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.CACHED,
        }


class StackComponentType(StrEnum):
    """All possible types a `StackComponent` can have."""

    ALERTER = "alerter"
    ANNOTATOR = "annotator"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"
    DATA_VALIDATOR = "data_validator"
    EXPERIMENT_TRACKER = "experiment_tracker"
    FEATURE_STORE = "feature_store"
    IMAGE_BUILDER = "image_builder"
    MODEL_DEPLOYER = "model_deployer"
    ORCHESTRATOR = "orchestrator"
    STEP_OPERATOR = "step_operator"
    MODEL_REGISTRY = "model_registry"

    @property
    def plural(self) -> str:
        """Returns the plural of the enum value.

        Returns:
            The plural of the enum value.
        """
        if self == StackComponentType.CONTAINER_REGISTRY:
            return "container_registries"
        elif self == StackComponentType.MODEL_REGISTRY:
            return "model_registries"

        return f"{self.value}s"


class SecretScope(StrEnum):
    """Enum for the scope of a secret."""

    WORKSPACE = "workspace"
    USER = "user"


class OAuthDeviceStatus(StrEnum):
    """The OAuth device status."""

    PENDING = "pending"
    VERIFIED = "verified"
    ACTIVE = "active"
    LOCKED = "locked"


class ColorVariants(StrEnum):
    """All possible color variants for frontend."""

    GREY = "grey"
    PURPLE = "purple"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    LIME = "lime"
    TEAL = "teal"
    TURQUOISE = "turquoise"
    MAGENTA = "magenta"
    BLUE = "blue"


class MetadataTypeEnum(StrEnum):
    """String Enum of all possible types that metadata can have."""

    STRING = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    TUPLE = "tuple"
    SET = "set"
    URI = "Uri"
    PATH = "Path"
    DTYPE = "DType"
    STORAGE_SIZE = "StorageSize"


ASSIGNMENTS = [
    ("artifact_version", "type", ArtifactType),
    ("artifact_visualization", "type", VisualizationType),
    ("auth_devices", "status", OAuthDeviceStatus),
    ("flavor", "type", StackComponentType),
    ("pipeline_run", "status", ExecutionStatus),
    ("run_metadata", "type", MetadataTypeEnum),
    ("secret", "scope", SecretScope),
    ("stack_component", "type", StackComponentType),
    ("step_run", "status", ExecutionStatus),
    ("step_run_input_artifact", "type", StepRunInputArtifactType),
    ("step_run_output_artifact", "type", StepRunOutputArtifactType),
]


def upgraded_value(old_value: str, enum: StrEnum) -> str:
    """Based on a given value and the corresponding enum, fetch the upgraded value.

    Args:
        old_value: the outdated value.
        enum: the enum that represents the column of this value.

    Returns:
        the value that it will be updated to.
    """
    return str(enum(old_value).name)


def downgraded_value(new_value, enum: StrEnum) -> str:
    """Based on a given value and the corresponding enum, fetch the downgraded value.

    Args:
        new_value: the updated value.
        enum: the enum that represents the column of this value.

    Returns:
        the value that it will be updated to.
    """
    return str(enum[new_value].value)


def upgrade():
    """Upgrade database schema and/or data, creating a new revision."""
    conn = op.get_bind()

    # Go through all the tables defined above
    for table_name, column_name, enum in ASSIGNMENTS:
        # Get all the existing unique values
        select_query = f"SELECT DISTINCT {column_name} FROM {table_name}"
        result = conn.execute(sa.text(select_query))

        # Create a set of replacements
        replacements = set()
        for old_value in result:
            replacements.add((old_value[0], upgraded_value(old_value[0], enum)))

        # Form and execute the update query
        if replacements:
            cases = " ".join(
                [
                    f'WHEN {column_name} = "{o}" THEN "{n}"'
                    for o, n in replacements
                ]
            )
            conn.execute(
                sa.text(
                    f"UPDATE {table_name} SET {column_name} = CASE {cases} END;"
                )
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    conn = op.get_bind()

    # Go through all the tables defined above
    for table_name, column_name, enum in ASSIGNMENTS:
        # Get all the existing unique values
        select_query = f"SELECT DISTINCT{column_name} FROM {table_name}"
        result = conn.execute(sa.text(select_query))

        # Create a set of replacements
        replacements = set()
        for old_value in result:
            replacements.add((old_value[0], downgraded_value(old_value[0], enum)))

        # Form and execute the update query
        if replacements:
            cases = " ".join(
                [
                    f'WHEN {column_name} = "{o}" THEN "{n}"'
                    for o, n in replacements
                ]
            )
            conn.execute(
                sa.text(
                    f"UPDATE {table_name} SET {column_name} = CASE {cases} END;"
                )
            )