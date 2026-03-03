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

"""Training pipeline: ingest sensor data from LakeFS, validate, and train."""

from typing import Optional

from steps import ingest_data, train_model, validate_data

from zenml import pipeline


@pipeline(tags=["lakefs", "data-versioning", "training"])
def training_pipeline(
    existing_commit: Optional[str] = None,
    n_rows: int = 10000,
    lakefs_repo: str = "",
) -> None:
    """End-to-end training pipeline with LakeFS data versioning.

    Data flow:
        ingest_data --> validate_data --> train_model

    Only lightweight LakeFSRef pointers flow between steps through
    ZenML's artifact store. The actual data (potentially TB-scale)
    stays in LakeFS and is read directly via the S3-compatible API.

    Args:
        existing_commit: If provided, skip ingestion and validation —
            train directly on data at this LakeFS commit SHA.
        n_rows: Number of synthetic sensor rows to generate.
        lakefs_repo: LakeFS repository name (overrides LAKEFS_REPO env var).
    """
    raw_ref = ingest_data(
        existing_commit=existing_commit,
        n_rows=n_rows,
        lakefs_repo=lakefs_repo,
    )
    validated_ref = validate_data(raw_ref)
    train_model(validated_ref)
