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

"""Ingest step: generate synthetic sensor data and upload to LakeFS."""

import os
import uuid
from typing import Annotated, Optional

import numpy as np
import pandas as pd
from utils import LakeFSRef
from utils.lakefs_utils import (
    LAKEFS_ENDPOINT,
    create_branch,
    write_parquet_to_lakefs,
)

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


def _generate_sensor_data(n_rows: int = 10000) -> pd.DataFrame:
    """Generate synthetic sensor data with ~5% bad rows."""
    rng = np.random.default_rng(42)

    timestamps = pd.date_range("2026-01-01", periods=n_rows, freq="1min")
    sensor_ids = rng.choice(
        ["sensor_A", "sensor_B", "sensor_C", "sensor_D"], size=n_rows
    )
    temperature = rng.normal(25.0, 5.0, size=n_rows)
    humidity = rng.normal(50.0, 10.0, size=n_rows)
    pressure = rng.normal(1013.0, 10.0, size=n_rows)
    status = rng.choice(
        ["OK", "WARN", "ERROR"], size=n_rows, p=[0.90, 0.07, 0.03]
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "sensor_id": sensor_ids,
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "status": status,
        }
    )

    # Inject ~5% bad rows for the validation step to catch
    n_bad = int(n_rows * 0.05)
    bad_idx = rng.choice(n_rows, size=n_bad, replace=False)

    null_idx = bad_idx[: n_bad // 2]
    df.loc[null_idx, "temperature"] = np.nan

    oor_idx = bad_idx[n_bad // 2 :]
    df.loc[oor_idx, "temperature"] = rng.choice(
        [-100.0, 200.0], size=len(oor_idx)
    )

    return df


@step
def ingest_data(
    existing_commit: Optional[str] = None,
    n_rows: int = 10000,
    lakefs_repo: str = "",
) -> Annotated[LakeFSRef, "raw_data_ref"]:
    """Generate synthetic sensor data and upload to a new LakeFS branch.

    If ``existing_commit`` is provided, skip data generation and return
    a reference pointing to the validated data at that commit (for
    retraining on a known data snapshot).

    Args:
        existing_commit: Commit SHA to reuse instead of generating data.
        n_rows: Number of synthetic rows to generate.
        lakefs_repo: LakeFS repository name.

    Returns:
        A LakeFSRef pointing to the raw data on a new branch, or to
        validated data at the given commit.
    """
    repo = lakefs_repo or os.environ.get("LAKEFS_REPO", "robot-data")

    if existing_commit:
        logger.info("Reusing existing LakeFS commit: %s", existing_commit)
        return LakeFSRef(
            repo=repo,
            ref=existing_commit,
            path="validated/data.parquet",
            endpoint=LAKEFS_ENDPOINT,
        )

    run_id = uuid.uuid4().hex[:8]
    branch_name = f"ingest-{run_id}"
    data_path = "raw/data.parquet"

    logger.info("Generating %d rows of synthetic sensor data", n_rows)
    df = _generate_sensor_data(n_rows=n_rows)

    create_branch(repo, branch_name)
    write_parquet_to_lakefs(df, repo, branch_name, data_path)

    logger.info(
        "Ingested data to branch '%s' at path '%s'",
        branch_name,
        data_path,
    )

    return LakeFSRef(
        repo=repo,
        ref=branch_name,
        path=data_path,
        endpoint=LAKEFS_ENDPOINT,
    )
