"""Simple data ingestion step for prompt optimization example."""

from typing import Annotated, Any, Dict, Tuple

import pandas as pd
from models import DataSourceConfig

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def ingest_data(
    source_config: DataSourceConfig,
) -> Tuple[
    Annotated[pd.DataFrame, "dataset"],
    Annotated[Dict[str, Any], "ingestion_metadata"],
]:
    """Simple data ingestion from HuggingFace or local files.

    Args:
        source_config: Configuration specifying data source

    Returns:
        Tuple of (dataframe, metadata)
    """
    logger.info(
        f"Loading data from {source_config.source_type}:{source_config.source_path}"
    )

    # Load data based on source type
    if source_config.source_type == "hf":
        df = _load_from_huggingface(source_config)
    elif source_config.source_type == "local":
        df = _load_from_local(source_config)
    else:
        raise ValueError(
            f"Unsupported source type: {source_config.source_type}"
        )

    # Apply sampling if configured
    total = len(df)
    if source_config.sample_size and total > source_config.sample_size:
        df = df.sample(n=source_config.sample_size, random_state=42)
        logger.info(
            f"Sampled {source_config.sample_size} rows from {total} total"
        )

    # Generate simple metadata
    metadata = {
        "source_type": source_config.source_type,
        "source_path": source_config.source_path,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "target_column": source_config.target_column,
    }

    logger.info(f"Loaded dataset: {len(df)} rows × {len(df.columns)} columns")
    return df, metadata


def _load_from_huggingface(config: DataSourceConfig) -> pd.DataFrame:
    """Load dataset from HuggingFace Hub."""
    try:
        from datasets import load_dataset

        # Simple dataset loading
        dataset = load_dataset(config.source_path, split="train")
        df = dataset.to_pandas()

        logger.info(f"Loaded HuggingFace dataset: {config.source_path}")
        return df

    except ImportError:
        raise ImportError(
            "datasets library required. Install with: pip install datasets"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load dataset {config.source_path}: {e}")


def _load_from_local(config: DataSourceConfig) -> pd.DataFrame:
    """Load dataset from local file."""
    try:
        file_path = config.source_path

        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path)
        else:
            # Try CSV as fallback
            df = pd.read_csv(file_path)

        logger.info(f"Loaded local file: {file_path}")
        return df

    except Exception as e:
        raise RuntimeError(f"Failed to load file {config.source_path}: {e}")
