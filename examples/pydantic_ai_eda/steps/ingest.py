"""Data ingestion step for EDA pipeline.

Supports loading data from multiple sources including HuggingFace datasets,
local files, and data warehouse connections.
"""

import hashlib
import logging
from typing import Annotated, Any, Dict, Tuple

import pandas as pd
from models import DataSourceConfig

from zenml import step

logger = logging.getLogger(__name__)


@step
def ingest_data(
    source_config: DataSourceConfig,
) -> Tuple[
    Annotated[pd.DataFrame, "dataset"],
    Annotated[Dict[str, Any], "ingestion_metadata"],
]:
    """Ingest data from configured source.

    Loads data from HuggingFace, local files, or warehouse based on
    source configuration. Returns both the DataFrame and metadata.

    Args:
        source_config: Configuration specifying data source and parameters

    Returns:
        Tuple of (raw_df, metadata) where metadata contains schema info,
        row count, and content hash for traceability
    """
    logger.info(
        f"Ingesting data from {source_config.source_type}: {source_config.source_path}"
    )

    # Load data based on source type
    if source_config.source_type == "hf":
        df = _load_from_huggingface(source_config)
    elif source_config.source_type == "local":
        df = _load_from_local(source_config)
    elif source_config.source_type == "warehouse":
        df = _load_from_warehouse(source_config)
    else:
        raise ValueError(
            f"Unsupported source type: {source_config.source_type}"
        )

    # Apply sampling if configured
    if source_config.sample_size and len(df) > source_config.sample_size:
        if source_config.sampling_strategy == "random":
            df = df.sample(n=source_config.sample_size, random_state=42)
        elif source_config.sampling_strategy == "first_n":
            df = df.head(source_config.sample_size)
        elif (
            source_config.sampling_strategy == "stratified"
            and source_config.target_column
        ):
            df = _stratified_sample(
                df, source_config.target_column, source_config.sample_size
            )
        else:
            logger.warning(
                f"Unknown sampling strategy: {source_config.sampling_strategy}"
            )
            df = df.sample(n=source_config.sample_size, random_state=42)

    # Note: For basic datasets like iris, pandas DataFrames should work fine with ZenML
    # The dtype warnings come from ZenML's internal serialization of DataFrame metadata,
    # not the actual data. This is normal for pandas DataFrames in ZenML.

    # Generate metadata
    metadata = {
        "source_type": source_config.source_type,
        "source_path": source_config.source_path,
        "original_rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "dtypes": df.dtypes.to_dict(),
        "target_column": source_config.target_column,
        "content_hash": _compute_content_hash(df),
        "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
    }

    # Add target column statistics if specified
    if (
        source_config.target_column
        and source_config.target_column in df.columns
    ):
        metadata["target_value_counts"] = (
            df[source_config.target_column].value_counts().to_dict()
        )
        metadata["target_null_count"] = (
            df[source_config.target_column].isnull().sum()
        )

    logger.info(
        f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns"
    )

    return df, metadata


def _load_from_huggingface(config: DataSourceConfig) -> pd.DataFrame:
    """Load dataset from HuggingFace Hub."""
    try:
        from datasets import load_dataset

        # Parse dataset path (may include config/split)
        parts = config.source_path.split("/")
        if len(parts) >= 2:
            dataset_name = "/".join(parts[:2])
            subset = parts[2] if len(parts) > 2 else None
        else:
            dataset_name = config.source_path
            subset = None

        # Load dataset
        dataset = load_dataset(dataset_name, subset, split="train")
        df = dataset.to_pandas()

        logger.info(f"Loaded HuggingFace dataset: {dataset_name}")
        return df

    except ImportError:
        raise ImportError(
            "datasets library required for HuggingFace loading. Install with: pip install datasets"
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to load HuggingFace dataset {config.source_path}: {e}"
        )


def _load_from_local(config: DataSourceConfig) -> pd.DataFrame:
    """Load dataset from local file."""
    try:
        file_path = config.source_path

        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            # Try CSV as fallback
            df = pd.read_csv(file_path)

        logger.info(f"Loaded local file: {file_path}")
        return df

    except Exception as e:
        raise RuntimeError(
            f"Failed to load local file {config.source_path}: {e}"
        )


def _load_from_warehouse(config: DataSourceConfig) -> pd.DataFrame:
    """Load dataset from data warehouse connection."""
    try:
        warehouse_config = config.warehouse_config or {}

        if "connection_string" in warehouse_config:
            # Generic SQL connection
            import sqlalchemy

            engine = sqlalchemy.create_engine(
                warehouse_config["connection_string"]
            )
            df = pd.read_sql(config.source_path, engine)
        elif "type" in warehouse_config:
            # Specific warehouse type
            warehouse_type = warehouse_config["type"].lower()

            if warehouse_type == "bigquery":
                df = _load_from_bigquery(config.source_path, warehouse_config)
            elif warehouse_type == "snowflake":
                df = _load_from_snowflake(config.source_path, warehouse_config)
            elif warehouse_type == "redshift":
                df = _load_from_redshift(config.source_path, warehouse_config)
            else:
                raise ValueError(
                    f"Unsupported warehouse type: {warehouse_type}"
                )
        else:
            raise ValueError(
                "Warehouse config must specify connection_string or type"
            )

        logger.info(f"Loaded from warehouse: {config.source_path}")
        return df

    except Exception as e:
        raise RuntimeError(
            f"Failed to load from warehouse {config.source_path}: {e}"
        )


def _load_from_bigquery(
    table_path: str, config: Dict[str, Any]
) -> pd.DataFrame:
    """Load data from Google BigQuery."""
    try:
        import pandas_gbq

        project_id = config.get("project_id")
        credentials = config.get("credentials_path")

        if table_path.startswith("SELECT"):
            # It's a query
            df = pandas_gbq.read_gbq(
                table_path, project_id=project_id, credentials=credentials
            )
        else:
            # It's a table reference
            query = f"SELECT * FROM `{table_path}`"
            df = pandas_gbq.read_gbq(
                query, project_id=project_id, credentials=credentials
            )

        return df

    except ImportError:
        raise ImportError(
            "pandas-gbq required for BigQuery. Install with: pip install pandas-gbq"
        )


def _load_from_snowflake(
    table_path: str, config: Dict[str, Any]
) -> pd.DataFrame:
    """Load data from Snowflake."""
    try:
        import snowflake.connector
        from snowflake.connector.pandas_tools import pd_writer

        conn = snowflake.connector.connect(
            user=config["user"],
            password=config["password"],
            account=config["account"],
            warehouse=config.get("warehouse"),
            database=config.get("database"),
            schema=config.get("schema"),
        )

        if table_path.upper().startswith("SELECT"):
            query = table_path
        else:
            query = f"SELECT * FROM {table_path}"

        df = pd.read_sql(query, conn)
        conn.close()

        return df

    except ImportError:
        raise ImportError(
            "snowflake-connector-python required. Install with: pip install snowflake-connector-python"
        )


def _load_from_redshift(
    table_path: str, config: Dict[str, Any]
) -> pd.DataFrame:
    """Load data from Amazon Redshift."""
    try:
        import psycopg2
        import sqlalchemy

        connection_string = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config.get('port', 5439)}/{config['database']}"
        engine = sqlalchemy.create_engine(connection_string)

        if table_path.upper().startswith("SELECT"):
            query = table_path
        else:
            query = f"SELECT * FROM {table_path}"

        df = pd.read_sql(query, engine)

        return df

    except ImportError:
        raise ImportError(
            "psycopg2 required for Redshift. Install with: pip install psycopg2-binary"
        )


def _stratified_sample(
    df: pd.DataFrame, target_column: str, sample_size: int
) -> pd.DataFrame:
    """Perform stratified sampling based on target column."""
    try:
        # Calculate proportional sample sizes for each class
        value_counts = df[target_column].value_counts()
        proportions = value_counts / len(df)

        sampled_dfs = []
        remaining_samples = sample_size

        for value, proportion in proportions.items():
            if remaining_samples <= 0:
                break

            # Calculate sample size for this class
            class_sample_size = max(1, int(proportion * sample_size))
            class_sample_size = min(
                class_sample_size, remaining_samples, value_counts[value]
            )

            # Sample from this class
            class_df = df[df[target_column] == value].sample(
                n=class_sample_size, random_state=42
            )
            sampled_dfs.append(class_df)

            remaining_samples -= class_sample_size

        # Combine all samples
        result_df = pd.concat(sampled_dfs, ignore_index=True)

        # Shuffle the final result
        result_df = result_df.sample(frac=1, random_state=42).reset_index(
            drop=True
        )

        logger.info(
            f"Stratified sampling: {len(result_df)} samples across {len(sampled_dfs)} classes"
        )
        return result_df

    except Exception as e:
        logger.warning(f"Stratified sampling failed, using random: {e}")
        return df.sample(n=sample_size, random_state=42)


def _compute_content_hash(df: pd.DataFrame) -> str:
    """Compute hash of DataFrame content for change detection."""
    try:
        # Create a string representation of the dataframe structure and sample
        content_parts = [
            f"shape:{df.shape}",
            f"columns:{sorted(df.columns.tolist())}",
            f"dtypes:{sorted(df.dtypes.astype(str).tolist())}",
        ]

        # Add sample of data if not too large
        if len(df) <= 1000:
            content_parts.append(f"data:{df.to_string()}")
        else:
            # Use a sample and summary stats
            sample_df = (
                df.sample(n=100, random_state=42) if len(df) > 100 else df
            )
            content_parts.extend(
                [
                    f"sample:{sample_df.to_string()}",
                    f"describe:{df.describe().to_string()}",
                ]
            )

        content_str = "|".join(content_parts)
        return hashlib.md5(content_str.encode()).hexdigest()

    except Exception as e:
        logger.warning(f"Failed to compute content hash: {e}")
        return f"error_{hashlib.md5(str(df.shape).encode()).hexdigest()}"
