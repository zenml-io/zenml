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
"""Tests for the Modal Volume artifact store."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.modal import (
    MODAL_ORCHESTRATOR_FLAVOR,
    MODAL_STEP_OPERATOR_FLAVOR,
    MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
    ModalIntegration,
)
from zenml.integrations.modal.artifact_stores.modal_volume_artifact_store import (
    ModalVolumeArtifactStore,
)
from zenml.integrations.modal.flavors.modal_volume_artifact_store_flavor import (
    ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX,
    ModalVolumeArtifactStoreConfig,
    ModalVolumeArtifactStoreFlavor,
    parse_modal_volume_uri,
)
from zenml.io import fileio
from zenml.materializers.path_materializer import PathMaterializer
from zenml.utils import io_utils

MODAL_URI = "modal-volume://test-volume/root"


def _make_artifact_store(
    mount_path: Path,
    path: str = MODAL_URI,
) -> ModalVolumeArtifactStore:
    """Create a Modal Volume artifact store for tests."""
    return ModalVolumeArtifactStore(
        name="modal-volume-test",
        id=uuid4(),
        config=ModalVolumeArtifactStoreConfig(
            path=path,
            mount_path=str(mount_path),
        ),
        flavor=MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _enable_fast_path(
    monkeypatch: pytest.MonkeyPatch,
    artifact_store: ModalVolumeArtifactStore,
) -> None:
    """Set the Modal fast-path environment for one artifact store."""
    monkeypatch.setenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, "1")
    monkeypatch.setenv(
        ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH,
        artifact_store.config.mount_path,
    )
    monkeypatch.setenv(
        ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME,
        artifact_store.volume_name,
    )
    monkeypatch.setenv(
        ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX,
        artifact_store.volume_prefix,
    )


def test_modal_volume_path_parsing_derives_volume_fields() -> None:
    """Modal Volume config derives Volume details from path."""
    parsed = parse_modal_volume_uri("modal-volume://vol-a/some/prefix")
    assert parsed.volume_name == "vol-a"
    assert parsed.volume_prefix == "some/prefix"

    config = ModalVolumeArtifactStoreConfig(
        path="modal-volume://vol-a/some/prefix"
    )
    assert config.volume_name == "vol-a"
    assert config.volume_prefix == "some/prefix"
    assert config.create_if_missing is False

    normalized_config = ModalVolumeArtifactStoreConfig(
        path="modal-volume://vol-a/some/prefix",
        mount_path="/mnt//../mnt/zenml/./artifacts/..",
    )
    assert normalized_config.mount_path == "/mnt/zenml"

    config_fields = ModalVolumeArtifactStoreConfig.model_fields
    assert "volume_name" not in config_fields
    assert "volume_prefix" not in config_fields
    assert "use_sdk_fallback_for_control_plane" not in config_fields
    assert "allow_non_modal_execution_with_sdk" not in config_fields


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("modal-volume:///prefix", "volume name"),
        ("modal-volume://vol/prefix?x=1", "query string"),
        ("modal-volume://vol/prefix#fragment", "fragment"),
        ("modal-volume://user@vol/prefix", "URI authority"),
        ("modal-volume://user:pass@vol/prefix", "URI authority"),
        ("modal-volume://vol:123/prefix", "URI authority"),
        ("modal-volume://vol:not-a-port/prefix", "port"),
        ("modal-volume://vol/../outside", "path traversal"),
        ("modal-volume://vol/%2E%2E/outside", "path traversal"),
    ],
)
def test_modal_volume_config_rejects_invalid_paths(
    path: str, message: str
) -> None:
    """Invalid Modal Volume paths fail during config validation."""
    with pytest.raises(ValidationError, match=message):
        ModalVolumeArtifactStoreConfig(path=path)


@pytest.mark.parametrize("mount_path", ["relative/path", "/"])
def test_modal_volume_config_rejects_invalid_mount_paths(
    mount_path: str,
) -> None:
    """The mount path must be a non-root absolute path."""
    with pytest.raises(ValidationError, match="mount_path"):
        ModalVolumeArtifactStoreConfig(path=MODAL_URI, mount_path=mount_path)


def test_modal_volume_flavor_uses_lazy_implementation_import() -> None:
    """The flavor exposes config and implementation classes."""
    flavor = ModalVolumeArtifactStoreFlavor()
    assert flavor.name == MODAL_VOLUME_ARTIFACT_STORE_FLAVOR
    assert flavor.config_class is ModalVolumeArtifactStoreConfig
    assert flavor.implementation_class is ModalVolumeArtifactStore


def test_modal_integration_defers_modal_volume_flavor_registration() -> None:
    """Modal Volume flavor registration waits for lifecycle validation."""
    assert ModalVolumeArtifactStoreFlavor not in ModalIntegration.flavors()


def _validator_stack(
    *,
    orchestrator_flavor: str,
    step_operator_flavors: list[str] | None = None,
):
    """Create a minimal stack object for artifact-store validator tests."""
    orchestrator = SimpleNamespace(
        flavor=orchestrator_flavor,
        type=StackComponentType.ORCHESTRATOR,
    )
    step_operators = {
        f"step-operator-{index}": SimpleNamespace(
            name=f"step-operator-{index}",
            flavor=flavor,
            type=StackComponentType.STEP_OPERATOR,
        )
        for index, flavor in enumerate(step_operator_flavors or [])
    }
    return SimpleNamespace(
        name="validator-stack",
        orchestrator=orchestrator,
        step_operators=step_operators,
        all_components=[orchestrator, *step_operators.values()],
    )


def test_modal_volume_validator_accepts_modal_orchestrator(
    tmp_path: Path,
) -> None:
    """Modal orchestrator stacks can mount Modal Volume artifact stores."""
    validator = _make_artifact_store(tmp_path).validator

    validator.validate(
        _validator_stack(orchestrator_flavor=MODAL_ORCHESTRATOR_FLAVOR)
    )


def test_modal_volume_validator_accepts_modal_step_operator_with_modal_orchestrator(
    tmp_path: Path,
) -> None:
    """A Modal step operator is safe only when orchestration is also Modal."""
    validator = _make_artifact_store(tmp_path).validator

    validator.validate(
        _validator_stack(
            orchestrator_flavor=MODAL_ORCHESTRATOR_FLAVOR,
            step_operator_flavors=[MODAL_STEP_OPERATOR_FLAVOR],
        )
    )


def test_modal_volume_validator_rejects_non_modal_orchestrator(
    tmp_path: Path,
) -> None:
    """Local and other non-Modal orchestrators cannot mount Modal Volumes."""
    validator = _make_artifact_store(tmp_path).validator

    with pytest.raises(StackValidationError) as exc_info:
        validator.validate(_validator_stack(orchestrator_flavor="local"))

    error_message = str(exc_info.value)
    assert "Modal-native storage" in error_message
    assert "Modal orchestrator" in error_message
    assert "not S3-compatible" in error_message


def test_modal_volume_validator_rejects_non_modal_step_operator(
    tmp_path: Path,
) -> None:
    """Non-Modal step operators cannot mount the configured Modal Volume."""
    validator = _make_artifact_store(tmp_path).validator

    with pytest.raises(StackValidationError) as exc_info:
        validator.validate(
            _validator_stack(
                orchestrator_flavor=MODAL_ORCHESTRATOR_FLAVOR,
                step_operator_flavors=["vertex"],
            )
        )

    error_message = str(exc_info.value)
    assert "Non-Modal step operators" in error_message
    assert "cannot mount Modal Volumes" in error_message


def test_modal_volume_uri_is_remote() -> None:
    """Modal Volume paths are treated as remote by path sanitization."""
    assert io_utils.is_remote("modal-volume://vol/path")


def test_modal_volume_uses_sdk_fallback_without_fast_path_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local control-plane writes use Modal SDK fallback before mounting."""

    class BatchUploadStub:
        """Collect files uploaded through the Modal SDK batch API."""

        def __init__(self, volume: "VolumeStub") -> None:
            self.volume = volume

        def __enter__(self) -> "BatchUploadStub":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def put_file(self, local_path: str, remote_path: str) -> None:
            self.volume.files[remote_path] = Path(local_path).read_bytes()

    class VolumeStub:
        """Small Modal Volume stand-in for control-plane SDK operations."""

        def __init__(self) -> None:
            self.files: dict[str, bytes] = {}
            self.copy_calls: list[tuple[list[str], str, bool]] = []

        def batch_upload(self, force: bool = False) -> BatchUploadStub:
            return BatchUploadStub(self)

        def read_file(self, path: str):
            yield self.files[path][:2]
            yield self.files[path][2:]

        def copy_files(
            self,
            src_paths: list[str],
            dst_path: str,
            recursive: bool = False,
        ) -> None:
            self.copy_calls.append((src_paths, dst_path, recursive))
            self.files[dst_path] = self.files[src_paths[0]]

        def remove_file(self, path: str, recursive: bool = False) -> None:
            del self.files[path]

        def listdir(self, path: str, recursive: bool = False):
            prefix = path.strip("/")
            children: dict[str, SimpleNamespace] = {}
            for file_path in self.files:
                stripped_path = file_path.strip("/")
                if prefix:
                    if not stripped_path.startswith(f"{prefix}/"):
                        continue
                    remainder = stripped_path[len(prefix) + 1 :]
                else:
                    remainder = stripped_path
                child_name = remainder.split("/", 1)[0]
                child_path = f"{prefix}/{child_name}" if prefix else child_name
                entry_type = "DIRECTORY" if "/" in remainder else "FILE"
                children[child_path] = SimpleNamespace(
                    path=child_path,
                    type=SimpleNamespace(name=entry_type),
                )
            return list(children.values())

    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    volume = VolumeStub()
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)

    uri = f"{MODAL_URI}/control-plane/archive.tar.gz"
    artifact_store.makedirs(f"{MODAL_URI}/control-plane")

    assert not artifact_store.exists(uri)

    with artifact_store.open(uri, "wb") as file:
        file.write(b"archive")

    assert volume.files["/root/control-plane/archive.tar.gz"] == b"archive"
    assert artifact_store.exists(uri)
    with artifact_store.open(uri, "rb") as file:
        temp_download_path = file.name
        assert Path(temp_download_path).exists()
        assert file.read() == b"archive"
    assert not Path(temp_download_path).exists()

    with artifact_store.open(uri, "a") as file:
        file.write("-log")

    with artifact_store.open(uri, "rb") as file:
        assert file.read() == b"archive-log"
    assert artifact_store.listdir(f"{MODAL_URI}/control-plane") == [
        "archive.tar.gz"
    ]

    volume.files["/root/control-plane/source.txt"] = b"source"
    artifact_store.copyfile(
        f"{MODAL_URI}/control-plane/source.txt",
        f"{MODAL_URI}/control-plane/copy.txt",
    )
    assert volume.files["/root/control-plane/copy.txt"] == b"source"
    assert volume.copy_calls == [
        (
            ["/root/control-plane/source.txt"],
            "/root/control-plane/copy.txt",
            False,
        )
    ]

    volume.files["/root/control-plane/existing.txt"] = b"keep"
    with pytest.raises(NotImplementedError, match="overwriting"):
        artifact_store.copyfile(
            f"{MODAL_URI}/control-plane/source.txt",
            f"{MODAL_URI}/control-plane/existing.txt",
            overwrite=True,
        )
    assert volume.files["/root/control-plane/existing.txt"] == b"keep"


def test_modal_volume_sdk_lookup_prefers_sandbox_environment_and_caches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK fallback reuses the sandbox Volume environment marker."""
    import modal

    artifact_store = _make_artifact_store(tmp_path)
    volume = object()
    calls: list[dict[str, object]] = []

    def from_name(name: str, **kwargs: object) -> object:
        calls.append({"name": name, **kwargs})
        return volume

    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setenv("MODAL_ENVIRONMENT", "ambient-env")
    monkeypatch.setenv("ZENML_MODAL_VOLUME_ENVIRONMENT_NAME", "sandbox-env")
    monkeypatch.setattr(modal.Volume, "from_name", from_name)

    assert artifact_store._get_modal_volume() is volume
    assert artifact_store._get_modal_volume() is volume
    assert calls == [
        {
            "name": "test-volume",
            "environment_name": "sandbox-env",
            "create_if_missing": False,
        }
    ]

    fallback_artifact_store = _make_artifact_store(tmp_path)
    fallback_volume = object()
    monkeypatch.delenv("ZENML_MODAL_VOLUME_ENVIRONMENT_NAME", raising=False)

    def fallback_from_name(name: str, **kwargs: object) -> object:
        calls.append({"name": name, **kwargs})
        return fallback_volume

    monkeypatch.setattr(modal.Volume, "from_name", fallback_from_name)

    assert fallback_artifact_store._get_modal_volume() is fallback_volume
    assert calls[-1] == {
        "name": "test-volume",
        "environment_name": "ambient-env",
        "create_if_missing": False,
    }


def test_modal_volume_cleans_temp_file_when_sdk_read_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK read failures do not leak temp files."""
    temp_paths: list[Path] = []
    original_named_temporary_file = tempfile.NamedTemporaryFile

    def named_temporary_file_spy(*args: object, **kwargs: object):
        temp_file = original_named_temporary_file(*args, **kwargs)
        temp_paths.append(Path(temp_file.name))
        return temp_file

    def failing_chunks():
        yield b"partial"
        raise RuntimeError("stream failed")

    class FailingReadVolumeStub:
        def read_file(self, path: str):
            return failing_chunks()

    artifact_store = _make_artifact_store(tmp_path)
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(
        artifact_store, "_get_modal_volume", lambda: FailingReadVolumeStub()
    )
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", named_temporary_file_spy)

    with pytest.raises(RuntimeError, match="stream failed"):
        artifact_store.open(f"{MODAL_URI}/failed-read.txt", "rb")

    assert temp_paths
    assert all(not path.exists() for path in temp_paths)


def test_modal_volume_translates_sdk_read_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modal SDK missing-file errors become FileNotFoundError."""

    class NotFoundError(Exception):
        pass

    class MissingReadVolumeStub:
        def read_file(self, path: str):
            raise NotFoundError("missing")
            yield b""  # pragma: no cover

    artifact_store = _make_artifact_store(tmp_path)
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(
        artifact_store, "_get_modal_volume", lambda: MissingReadVolumeStub()
    )

    with pytest.raises(FileNotFoundError):
        artifact_store.open(f"{MODAL_URI}/missing.txt", "rb")


def test_modal_volume_cleans_upload_temp_file_when_append_preload_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Append preload failures do not leak the temp upload file."""
    temp_paths: list[Path] = []
    original_named_temporary_file = tempfile.NamedTemporaryFile

    def named_temporary_file_spy(*args: object, **kwargs: object):
        temp_file = original_named_temporary_file(*args, **kwargs)
        temp_paths.append(Path(temp_file.name))
        return temp_file

    class FailingPreloadVolumeStub:
        def listdir(self, path: str, recursive: bool = False):
            return [
                SimpleNamespace(
                    path="root/existing.txt",
                    type=SimpleNamespace(name="FILE"),
                )
            ]

        def read_file(self, path: str):
            raise RuntimeError("preload failed")
            yield b""  # pragma: no cover

    artifact_store = _make_artifact_store(tmp_path)
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(
        artifact_store,
        "_get_modal_volume",
        lambda: FailingPreloadVolumeStub(),
    )
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", named_temporary_file_spy)

    with pytest.raises(RuntimeError, match="preload failed"):
        artifact_store.open(f"{MODAL_URI}/existing.txt", "a")

    assert temp_paths
    assert all(not path.exists() for path in temp_paths)


def test_modal_volume_preserves_upload_temp_file_when_upload_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed SDK upload leaves the temporary source file for inspection."""

    class FailingBatchUploadStub:
        def __enter__(self) -> "FailingBatchUploadStub":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def put_file(self, local_path: str, remote_path: str) -> None:
            raise RuntimeError("upload failed")

    class FailingVolumeStub:
        def batch_upload(self, force: bool = False) -> FailingBatchUploadStub:
            return FailingBatchUploadStub()

    artifact_store = _make_artifact_store(tmp_path)
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(
        artifact_store, "_get_modal_volume", lambda: FailingVolumeStub()
    )

    file = artifact_store.open(f"{MODAL_URI}/failed-upload.txt", "wb")
    file.write(b"debug me")
    temp_upload_path = file.name

    with pytest.raises(RuntimeError, match="upload failed"):
        file.close()

    assert Path(temp_upload_path).exists()
    assert Path(temp_upload_path).read_bytes() == b"debug me"
    Path(temp_upload_path).unlink()


def test_modal_volume_fails_when_marked_mount_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A set marker with no mount path points to Modal runtime setup failure."""
    missing_mount_path = tmp_path / "missing"
    artifact_store = _make_artifact_store(missing_mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    with pytest.raises(
        FileNotFoundError, match="create_if_missing value is False"
    ):
        artifact_store.exists(MODAL_URI)


def test_modal_volume_rejects_mismatched_fast_path_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sandbox mounted for one Volume cannot serve another Volume."""
    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)
    monkeypatch.setenv(
        ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME,
        "different-volume",
    )

    with pytest.raises(RuntimeError, match="runtime mount metadata"):
        artifact_store.exists(MODAL_URI)


def test_modal_volume_rejects_symlink_escape_for_missing_write_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symlinked parent cannot redirect mounted writes outside the mount."""
    mount_path = tmp_path / "mount"
    outside_path = tmp_path / "outside"
    mount_path.mkdir()
    outside_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    artifact_store.makedirs(MODAL_URI)
    os.symlink(outside_path, mount_path / "root" / "link")

    with pytest.raises(FileNotFoundError, match="resolves outside"):
        with artifact_store.open(f"{MODAL_URI}/link/escape.txt", "w"):
            pass

    assert not (outside_path / "escape.txt").exists()


def test_modal_volume_rejects_symlink_escape_outside_mount(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An existing symlink target outside the mount is rejected."""
    mount_path = tmp_path / "mount"
    outside_path = tmp_path / "outside"
    mount_path.mkdir()
    outside_path.mkdir()
    outside_file = outside_path / "secret.txt"
    outside_file.write_text("secret")
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    artifact_store.makedirs(MODAL_URI)
    os.symlink(outside_file, mount_path / "root" / "secret-link.txt")

    with pytest.raises(FileNotFoundError, match="Modal Volume mount path"):
        artifact_store.exists(f"{MODAL_URI}/secret-link.txt")


def test_modal_volume_rejects_symlink_escape_outside_configured_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symlink cannot stay in the mount but leave the artifact-store root."""
    mount_path = tmp_path / "mount"
    other_prefix = mount_path / "other"
    mount_path.mkdir()
    other_prefix.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    artifact_store.makedirs(MODAL_URI)
    os.symlink("../other", mount_path / "root" / "link")

    with pytest.raises(FileNotFoundError, match="artifact-store root path"):
        with artifact_store.open(f"{MODAL_URI}/link/file.txt", "w"):
            pass

    assert not (other_prefix / "file.txt").exists()


def test_modal_volume_recursive_operations_reject_prefix_escape_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recursive reads reject symlinks that leave the configured prefix."""
    mount_path = tmp_path / "mount"
    other_prefix = mount_path / "other"
    mount_path.mkdir()
    other_prefix.mkdir()
    (other_prefix / "secret.txt").write_text("secret")
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    artifact_store.makedirs(MODAL_URI)
    with artifact_store.open(f"{MODAL_URI}/data.txt", "w") as file:
        file.write("data")
    os.symlink("../other/secret.txt", mount_path / "root" / "secret-link.txt")

    with pytest.raises(FileNotFoundError, match="artifact-store root path"):
        artifact_store.size(MODAL_URI)
    with pytest.raises(FileNotFoundError, match="artifact-store root path"):
        list(artifact_store.walk(MODAL_URI))
    with pytest.raises(FileNotFoundError, match="artifact-store root path"):
        artifact_store.glob(f"{MODAL_URI}/*")


def test_modal_volume_mounted_fast_path_methods(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The required BaseArtifactStore methods work on a mounted directory."""
    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    root_uri = MODAL_URI
    nested_uri = f"{root_uri}/nested"
    file_uri = f"{nested_uri}/file.txt"
    copied_uri = f"{nested_uri}/copied.txt"
    renamed_uri = f"{nested_uri}/renamed.txt"

    artifact_store.makedirs(nested_uri)
    with artifact_store.open(file_uri, "w") as file:
        file.write("hello")

    assert (mount_path / "root" / "nested" / "file.txt").read_text() == "hello"
    assert artifact_store.exists(file_uri)
    assert artifact_store.isdir(nested_uri)
    assert artifact_store.listdir(nested_uri) == ["file.txt"]
    assert artifact_store.size(file_uri) == len("hello")
    assert artifact_store.size(root_uri) == len("hello")
    assert artifact_store.stat(file_uri).st_size == len("hello")

    artifact_store.copyfile(file_uri, copied_uri)
    assert artifact_store.exists(copied_uri)
    assert set(artifact_store.glob(f"{nested_uri}/*.txt")) == {
        file_uri,
        copied_uri,
    }

    artifact_store.rename(copied_uri, renamed_uri)
    assert not artifact_store.exists(copied_uri)
    assert artifact_store.exists(renamed_uri)

    walked = list(artifact_store.walk(root_uri))
    assert walked[0][0] == root_uri
    assert "nested" in walked[0][1]
    assert any(root == nested_uri for root, _, _ in walked)

    artifact_store.remove(file_uri)
    assert not artifact_store.exists(file_uri)

    empty_dir_uri = f"{root_uri}/empty"
    artifact_store.mkdir(empty_dir_uri)
    assert artifact_store.isdir(empty_dir_uri)

    artifact_store.rmtree(root_uri)
    assert not artifact_store.exists(root_uri)


def test_modal_volume_rejects_operation_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translated paths cannot escape the configured Volume prefix."""
    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    with pytest.raises(ValueError, match="path traversal"):
        artifact_store.exists(f"{MODAL_URI}/../outside")

    with pytest.raises(FileNotFoundError, match="outside of artifact store"):
        artifact_store.exists("modal-volume://test-volume/root-other/file.txt")


def test_modal_volume_fileio_registration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Instantiating the artifact store registers modal-volume:// with fileio."""
    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    uri = f"{MODAL_URI}/fileio/file.txt"
    fileio.makedirs(os.path.dirname(uri))
    with fileio.open(uri, "w") as file:
        file.write("from fileio")

    assert fileio.exists(uri)
    assert (mount_path / "root" / "fileio" / "file.txt").read_text() == (
        "from fileio"
    )
    assert fileio.listdir(os.path.dirname(uri)) == ["file.txt"]
    assert fileio.size(uri) == len("from fileio")


def test_modal_volume_path_materializer_file_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PathMaterializer can save and load through fileio on modal-volume://."""
    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    _enable_fast_path(monkeypatch, artifact_store)

    source_path = tmp_path / "source.txt"
    source_path.write_text("materialized file")

    artifact_uri = f"{MODAL_URI}/path-materializer"
    artifact_store.makedirs(artifact_uri)
    materializer = PathMaterializer(
        uri=artifact_uri, artifact_store=artifact_store
    )

    materializer.save(source_path)
    loaded_path = materializer.load(Path)

    assert loaded_path.is_file()
    assert loaded_path.read_text() == "materialized file"
    assert (mount_path / "root" / "path-materializer" / "file_data").exists()
