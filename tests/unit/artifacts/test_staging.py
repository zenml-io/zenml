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
import os
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.artifacts.staging import (
    ArtifactStagingContext,
    StagedArtifactUpload,
    _build_staging_artifact_store,
    upload_staged_artifact,
)


def test_staging_context_is_inactive_by_default():
    """Test that no staging context is active by default."""
    assert ArtifactStagingContext.get() is None


def test_staging_context(tmp_path):
    """Test staging URI allocation, upload submission and lookup."""
    uploads = []
    context = ArtifactStagingContext(
        staging_dir=str(tmp_path), upload_callback=uploads.append
    )

    staging_uri = context.allocate_staging_uri()
    assert staging_uri.startswith(os.path.realpath(str(tmp_path)))

    artifact_version_id = uuid4()
    context.submit_upload(
        artifact_version_id=artifact_version_id,
        staging_uri=staging_uri,
        target_uri="/target",
    )

    assert context.get_staged_uri(artifact_version_id) == staging_uri
    assert context.get_staged_uri(uuid4()) is None
    assert uploads == [
        StagedArtifactUpload(
            artifact_version_id=artifact_version_id,
            staging_uri=staging_uri,
            target_uri="/target",
        )
    ]

    with context:
        assert ArtifactStagingContext.get() is context
    assert ArtifactStagingContext.get() is None


def test_staging_context_capacity_and_discard(tmp_path):
    """Test staging capacity accounting and discarding of staged data."""
    context = ArtifactStagingContext(
        staging_dir=str(tmp_path),
        upload_callback=lambda upload: None,
        max_size=10,
    )
    assert context.has_capacity

    staging_uri = context.allocate_staging_uri()
    os.makedirs(staging_uri)
    with open(os.path.join(staging_uri, "data.txt"), "w") as f:
        f.write("x" * 20)

    artifact_version_id = uuid4()
    context.submit_upload(
        artifact_version_id=artifact_version_id,
        staging_uri=staging_uri,
        target_uri="/target",
    )
    assert not context.has_capacity

    context.discard(artifact_version_id)
    assert context.has_capacity
    assert context.get_staged_uri(artifact_version_id) is None
    assert not os.path.exists(staging_uri)

    # Discarding an unknown artifact version is a no-op.
    context.discard(uuid4())


def test_upload_staged_artifact(tmp_path):
    """Test that uploading a staged artifact copies the directory tree."""
    staging_dir = os.path.realpath(str(tmp_path / "staging"))
    target_root = os.path.realpath(str(tmp_path / "target"))
    os.makedirs(os.path.join(staging_dir, "sub"))
    os.makedirs(target_root)

    with open(os.path.join(staging_dir, "data.txt"), "w") as f:
        f.write("hello")
    with open(os.path.join(staging_dir, "sub", "nested.txt"), "w") as f:
        f.write("nested")

    artifact_store = _build_staging_artifact_store(path=target_root)
    target_uri = os.path.join(target_root, "final")

    upload_staged_artifact(
        upload=StagedArtifactUpload(
            artifact_version_id=uuid4(),
            staging_uri=staging_dir,
            target_uri=target_uri,
        ),
        artifact_store=artifact_store,
    )

    with open(os.path.join(target_uri, "data.txt")) as f:
        assert f.read() == "hello"
    with open(os.path.join(target_uri, "sub", "nested.txt")) as f:
        assert f.read() == "nested"


def test_staged_artifact_uploader(tmp_path, mocker):
    """Test that the uploader uploads staged data, updates the availability
    and discards the staged files."""
    from zenml.artifacts.staging import StagedArtifactUploader
    from zenml.enums import ArtifactVersionAvailability

    mock_client = MagicMock()
    mocker.patch("zenml.client.Client", return_value=mock_client)

    target_root = os.path.realpath(str(tmp_path))
    artifact_store = _build_staging_artifact_store(path=target_root)
    uploader = StagedArtifactUploader(artifact_store=artifact_store)
    context = uploader.staging_context

    staging_uri = context.allocate_staging_uri()
    os.makedirs(staging_uri)
    with open(os.path.join(staging_uri, "data.txt"), "w") as f:
        f.write("hello")

    artifact_version_id = uuid4()
    target_uri = os.path.join(target_root, "final")
    context.submit_upload(
        artifact_version_id=artifact_version_id,
        staging_uri=staging_uri,
        target_uri=target_uri,
    )
    uploader.wait()

    with open(os.path.join(target_uri, "data.txt")) as f:
        assert f.read() == "hello"
    update = mock_client.zen_store.update_artifact_version.call_args.kwargs[
        "artifact_version_update"
    ]
    assert update.availability == ArtifactVersionAvailability.AVAILABLE
    assert context.get_staged_uri(artifact_version_id) is None
    assert not os.path.exists(staging_uri)

    uploader.shutdown()


def test_staged_artifact_uploader_failure(tmp_path, mocker):
    """Test that a failed upload raises and marks the artifact version."""
    from zenml.artifacts.staging import StagedArtifactUploader
    from zenml.enums import ArtifactVersionAvailability

    mock_client = MagicMock()
    mocker.patch("zenml.client.Client", return_value=mock_client)

    target_root = os.path.realpath(str(tmp_path))
    artifact_store = _build_staging_artifact_store(path=target_root)
    uploader = StagedArtifactUploader(artifact_store=artifact_store)
    context = uploader.staging_context

    staging_uri = context.allocate_staging_uri()
    os.makedirs(staging_uri)
    with open(os.path.join(staging_uri, "data.txt"), "w") as f:
        f.write("hello")

    context.submit_upload(
        artifact_version_id=uuid4(),
        staging_uri=staging_uri,
        target_uri="/outside/of/store/bounds",
    )
    with pytest.raises(Exception):
        uploader.wait()

    update = mock_client.zen_store.update_artifact_version.call_args.kwargs[
        "artifact_version_update"
    ]
    assert update.availability == ArtifactVersionAvailability.UPLOAD_FAILED

    uploader.shutdown()
