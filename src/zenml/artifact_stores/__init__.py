#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""
An artifact store is a place where artifacts are stored. These artifacts may
have been produced by the pipeline steps, or they may be the data first ingested
into a pipeline via an ingestion step.

Definitions of the ``BaseArtifactStore`` class and the ``LocalArtifactStore``
that builds on it are in this module.

Other artifact stores corresponding to specific integrations are to be found in
the ``integrations`` module. For example, the ``GCPArtifactStore``, used when
running ZenML on Google Cloud Platform, is defined in
``integrations.gcp.artifact_stores``.
"""

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.artifact_stores.local_artifact_store import LocalArtifactStore

__all__ = ["BaseArtifactStore", "LocalArtifactStore"]
