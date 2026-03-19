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

"""Lightweight reference type for pointing to data in LakeFS.

A LakeFSRef is a small JSON-serializable pointer that flows through ZenML's
artifact store. The actual data (potentially TB-scale) stays in LakeFS —
only this ~200-byte reference moves between pipeline steps.
"""

from pydantic import BaseModel


class LakeFSRef(BaseModel):
    """Pointer to a dataset stored in LakeFS.

    Args:
        repo: LakeFS repository name (e.g. "robot-data").
        ref: Branch name or commit SHA. After validation, this should
            be an immutable commit SHA for reproducibility.
        path: Path within the repo (e.g. "validated/data.parquet").
        endpoint: LakeFS S3 gateway endpoint URL.
    """

    repo: str
    ref: str
    path: str
    endpoint: str

    @property
    def s3_uri(self) -> str:
        """S3-style URI for the LakeFS S3 gateway: s3://{repo}/{ref}/{path}."""
        return f"s3://{self.repo}/{self.ref}/{self.path}"
