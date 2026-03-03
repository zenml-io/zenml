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

"""Validate step: read raw data from LakeFS, clean it, commit the result."""

import re
from typing import Annotated

from utils import LakeFSRef
from utils.lakefs_utils import (
    commit_branch,
    read_parquet_from_lakefs,
    write_parquet_to_lakefs,
)

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@step
def validate_data(
    raw_ref: LakeFSRef,
) -> Annotated[LakeFSRef, "validated_data_ref"]:
    """Read raw data from LakeFS, apply quality checks, and commit.

    Validation rules:
    - Drop rows with null values.
    - Filter temperature to the sensor operating range [-40, 85] C.

    After cleaning, the validated data is written to a ``validated/``
    path on the same branch and committed. The returned LakeFSRef uses
    the immutable commit SHA so downstream steps always read the exact
    same data snapshot.

    If the incoming ref is already a commit SHA (e.g. from the
    ``--lakefs-commit`` reuse flow), validation is skipped.

    Args:
        raw_ref: Reference to the raw data in LakeFS.

    Returns:
        A LakeFSRef with the commit SHA and validated data path.
    """
    # When reusing an existing commit, pass through unchanged
    if _COMMIT_SHA_PATTERN.match(raw_ref.ref):
        logger.info(
            "Ref is already a commit SHA (%s), skipping validation.",
            raw_ref.ref[:12],
        )
        log_metadata(
            {"validation_skipped": True, "reused_commit": raw_ref.ref}
        )
        return raw_ref

    logger.info(
        "Reading raw data from LakeFS: repo=%s ref=%s path=%s",
        raw_ref.repo,
        raw_ref.ref,
        raw_ref.path,
    )
    df = read_parquet_from_lakefs(raw_ref.repo, raw_ref.ref, raw_ref.path)
    n_total = len(df)

    # Drop nulls
    df_clean = df.dropna()
    n_after_nulls = len(df_clean)

    # Filter out-of-range temperature (sensor operating range)
    df_clean = df_clean[
        (df_clean["temperature"] >= -40) & (df_clean["temperature"] <= 85)
    ]
    n_valid = len(df_clean)

    stats = {
        "total_rows": n_total,
        "rows_after_null_removal": n_after_nulls,
        "valid_rows": n_valid,
        "rows_removed": n_total - n_valid,
        "removal_rate_pct": round((n_total - n_valid) / n_total * 100, 2),
    }
    logger.info("Validation stats: %s", stats)
    log_metadata(stats)

    # Write validated data back to LakeFS on the same branch
    validated_path = "validated/data.parquet"
    write_parquet_to_lakefs(
        df_clean, raw_ref.repo, raw_ref.ref, validated_path
    )

    # Commit the branch to get an immutable snapshot
    commit_message = (
        f"Validated: {n_valid}/{n_total} rows passed "
        f"({stats['removal_rate_pct']}% removed)"
    )
    commit_sha = commit_branch(raw_ref.repo, raw_ref.ref, commit_message)

    return LakeFSRef(
        repo=raw_ref.repo,
        ref=commit_sha,
        path=validated_path,
        endpoint=raw_ref.endpoint,
    )
