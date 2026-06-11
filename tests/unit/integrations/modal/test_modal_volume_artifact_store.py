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
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.constants import ENV_ZENML_SERVER
from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentInterfaceError, StackValidationError
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
from zenml.integrations.modal.sandbox_utils import (
    ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME,
)
from zenml.io import fileio
from zenml.log_stores.artifact.artifact_log_store import ArtifactLogStore
from zenml.materializers.path_materializer import PathMaterializer
from zenml.utils import io_utils

MODAL_URI = "modal-volume://test-volume/root"


def _make_artifact_store(
    mount_path: Path,
    path: str = MODAL_URI,
    **config_kwargs: object,
) -> ModalVolumeArtifactStore:
    """Create a Modal Volume artifact store for tests."""
    return ModalVolumeArtifactStore(
        name="modal-volume-test",
        id=uuid4(),
        config=ModalVolumeArtifactStoreConfig(
            path=path,
            mount_path=str(mount_path),
            **config_kwargs,
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


class ModalVolumeStub:
    """Small Modal Volume stand-in for SDK fallback tests."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        """Initialize the stub.

        Args:
            files: Mapping of absolute Modal Volume SDK paths to file bytes.
        """
        self.files = files or {}
        self.copy_calls: list[tuple[list[str], str, bool]] = []
        self.listdir_calls: list[tuple[str, bool]] = []
        self.read_file_calls: list[str] = []
        self.remove_file_calls: list[tuple[str, bool]] = []
        self.rename_calls: list[tuple[str, str]] = []
        self.upload_calls: list[tuple[str, str]] = []

    @staticmethod
    def _assert_sdk_path(path: str) -> None:
        """Fail when code passes absolute paths to Modal SDK file APIs."""
        if path != "/" and path.startswith("/"):
            raise AssertionError(f"SDK path must be relative, got {path!r}")

    def batch_upload(self, force: bool = False) -> "BatchUploadStub":
        """Return a batch uploader for this stub Volume."""
        return BatchUploadStub(self)

    def read_file(self, path: str):
        """Yield file contents in chunks like the Modal SDK."""
        self._assert_sdk_path(path)
        self.read_file_calls.append(path)
        yield self.files[path][:2]
        yield self.files[path][2:]

    def copy_files(
        self,
        src_paths: list[str],
        dst_path: str,
        recursive: bool = False,
    ) -> None:
        """Copy a file within the stub Volume."""
        for src_path in src_paths:
            self._assert_sdk_path(src_path)
        self._assert_sdk_path(dst_path)
        self.copy_calls.append((src_paths, dst_path, recursive))
        self.files[dst_path] = self.files[src_paths[0]]

    def remove_file(self, path: str, recursive: bool = False) -> None:
        """Remove a file from the stub Volume."""
        self._assert_sdk_path(path)
        self.remove_file_calls.append((path, recursive))
        del self.files[path]

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a file within the stub Volume."""
        self._assert_sdk_path(old_name)
        self._assert_sdk_path(new_name)
        self.rename_calls.append((old_name, new_name))
        self.files[new_name] = self.files.pop(old_name)

    def listdir(self, path: str, recursive: bool = False):
        """List child entries below a path."""
        self._assert_sdk_path(path)
        self.listdir_calls.append((path, recursive))
        prefix = path.strip("/")
        children: dict[str, SimpleNamespace] = {}
        for file_path, contents in self.files.items():
            stripped_path = file_path.strip("/")
            if prefix:
                if not stripped_path.startswith(f"{prefix}/"):
                    continue
                remainder = stripped_path[len(prefix) + 1 :]
            else:
                remainder = stripped_path

            current_prefix = prefix
            parts = (
                remainder.split("/")
                if recursive
                else [remainder.split("/", 1)[0]]
            )
            for index, part in enumerate(parts):
                child_path = (
                    f"{current_prefix}/{part}" if current_prefix else part
                )
                is_file = recursive and index == len(parts) - 1
                if not recursive:
                    is_file = "/" not in remainder
                children[child_path] = SimpleNamespace(
                    path=child_path,
                    type=SimpleNamespace(
                        name="FILE" if is_file else "DIRECTORY"
                    ),
                    size=len(contents) if is_file else 0,
                )
                current_prefix = child_path
        return list(children.values())


class BatchUploadStub:
    """Collect files uploaded through the Modal SDK batch API."""

    def __init__(self, volume: ModalVolumeStub) -> None:
        """Initialize the upload stub for one Volume."""
        self.volume = volume

    def __enter__(self) -> "BatchUploadStub":
        """Return the upload stub."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the upload context."""
        pass

    def put_file(self, local_path: str, remote_path: str) -> None:
        """Store local file bytes at the requested remote path."""
        self.volume._assert_sdk_path(remote_path)
        self.volume.upload_calls.append((local_path, remote_path))
        self.volume.files[remote_path] = Path(local_path).read_bytes()


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
    assert config.token_id is None
    assert config.token_secret is None
    assert config.modal_environment is None

    credential_config = ModalVolumeArtifactStoreConfig(
        path="modal-volume://vol-a/some/prefix",
        token_id="ak-test",
        token_secret="as-test",
        modal_environment="production",
    )
    assert credential_config.token_id == "ak-test"
    assert credential_config.token_secret == "as-test"
    assert credential_config.modal_environment == "production"

    normalized_config = ModalVolumeArtifactStoreConfig(
        path="modal-volume://vol-a/some/prefix",
        mount_path="/mnt//../mnt/zenml/./artifacts/..",
    )
    assert normalized_config.mount_path == "/mnt/zenml"

    config_fields = ModalVolumeArtifactStoreConfig.model_fields
    assert "volume_name" not in config_fields
    assert "volume_prefix" not in config_fields
    assert "token_id" in config_fields
    assert "token_secret" in config_fields
    assert "modal_environment" in config_fields
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


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"token_id": "ak-test"},
        {"token_secret": "as-test"},
    ],
)
def test_modal_volume_config_rejects_incomplete_token_pair(
    config_kwargs: dict[str, str],
) -> None:
    """Modal token_id and token_secret must be configured together."""
    with pytest.raises(ValidationError, match="configured together"):
        ModalVolumeArtifactStoreConfig(path=MODAL_URI, **config_kwargs)


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"token_id": "  ", "token_secret": "as-test"},
        {"token_id": "ak-test", "token_secret": "  "},
        {"token_id": "  ", "token_secret": "  "},
    ],
)
def test_modal_volume_config_rejects_empty_token_values(
    config_kwargs: dict[str, str],
) -> None:
    """Whitespace-only Modal token values are invalid, not unset."""
    with pytest.raises(ValidationError, match="must not be empty"):
        ModalVolumeArtifactStoreConfig(path=MODAL_URI, **config_kwargs)


def test_modal_volume_flavor_uses_lazy_implementation_import() -> None:
    """The flavor exposes config and implementation classes."""
    flavor = ModalVolumeArtifactStoreFlavor()
    assert flavor.name == MODAL_VOLUME_ARTIFACT_STORE_FLAVOR
    assert (
        flavor.config_class.__name__ == ModalVolumeArtifactStoreConfig.__name__
    )
    assert (
        flavor.implementation_class.__name__
        == ModalVolumeArtifactStore.__name__
    )


def test_modal_integration_registers_modal_volume_flavor() -> None:
    """The Modal integration exposes the Modal Volume artifact store."""
    flavor_names = {flavor.__name__ for flavor in ModalIntegration.flavors()}
    assert ModalVolumeArtifactStoreFlavor.__name__ in flavor_names


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
    mount_path = tmp_path / "mount"
    mount_path.mkdir()
    artifact_store = _make_artifact_store(mount_path)
    volume = ModalVolumeStub()
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)

    uri = f"{MODAL_URI}/control-plane/archive.tar.gz"
    artifact_store.makedirs(f"{MODAL_URI}/control-plane")

    assert not artifact_store.exists(uri)

    with artifact_store.open(uri, "wb") as file:
        file.write(b"archive")

    assert volume.files["root/control-plane/archive.tar.gz"] == b"archive"
    assert volume.upload_calls[0][1] == "root/control-plane/archive.tar.gz"
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
    assert "root/control-plane/archive.tar.gz" in volume.read_file_calls
    assert ("root/control-plane", False) in volume.listdir_calls

    source_uri = f"{MODAL_URI}/control-plane/source.txt"
    copy_uri = f"{MODAL_URI}/control-plane/copy.txt"
    nested_uri = f"{MODAL_URI}/control-plane/nested/file.txt"
    renamed_uri = f"{MODAL_URI}/control-plane/renamed.txt"
    overwrite_missing_uri = f"{MODAL_URI}/control-plane/overwrite-missing.txt"
    volume.files["root/control-plane/source.txt"] = b"source"
    volume.files["root/control-plane/nested/file.txt"] = b"nested"
    artifact_store.copyfile(source_uri, copy_uri)
    assert volume.files["root/control-plane/copy.txt"] == b"source"
    assert volume.copy_calls == [
        (
            ["root/control-plane/source.txt"],
            "root/control-plane/copy.txt",
            False,
        )
    ]
    assert set(artifact_store.glob(f"{MODAL_URI}/control-plane/*.txt")) == {
        source_uri,
        copy_uri,
    }
    assert artifact_store.glob(f"{MODAL_URI}/control-plane/*/*.txt") == [
        nested_uri
    ]
    assert artifact_store.glob(source_uri) == [source_uri]
    assert artifact_store.stat(source_uri) == {
        "name": "source.txt",
        "path": "root/control-plane/source.txt",
        "size": len(b"source"),
        "type": "FILE",
    }

    artifact_store.rename(copy_uri, renamed_uri)
    assert "root/control-plane/copy.txt" not in volume.files
    assert volume.files["root/control-plane/renamed.txt"] == b"source"

    artifact_store.rename(renamed_uri, overwrite_missing_uri, overwrite=True)
    assert "root/control-plane/renamed.txt" not in volume.files
    assert (
        volume.files["root/control-plane/overwrite-missing.txt"] == b"source"
    )
    assert volume.rename_calls == [
        ("root/control-plane/copy.txt", "root/control-plane/renamed.txt"),
        (
            "root/control-plane/renamed.txt",
            "root/control-plane/overwrite-missing.txt",
        ),
    ]

    volume.files["root/control-plane/existing.txt"] = b"keep"
    with pytest.raises(NotImplementedError, match="overwriting"):
        artifact_store.copyfile(
            source_uri,
            f"{MODAL_URI}/control-plane/existing.txt",
            overwrite=True,
        )
    assert volume.files["root/control-plane/existing.txt"] == b"keep"
    with pytest.raises(NotImplementedError, match="overwriting"):
        artifact_store.rename(
            overwrite_missing_uri,
            f"{MODAL_URI}/control-plane/existing.txt",
            overwrite=True,
        )
    assert volume.files["root/control-plane/existing.txt"] == b"keep"

    artifact_store.remove(overwrite_missing_uri)
    assert volume.remove_file_calls == [
        ("root/control-plane/overwrite-missing.txt", False)
    ]
    assert not artifact_store.exists(overwrite_missing_uri)


def test_modal_volume_sdk_fallback_sizes_files_and_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server downloads can size files and directories without a mount."""
    artifact_store = _make_artifact_store(tmp_path)
    volume = ModalVolumeStub(
        files={
            "root/control-plane/archive.tar.gz": b"archive",
            "root/control-plane/nested/data.bin": b"data",
            "root/control-plane/nested/second.bin": b"12",
        }
    )
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)

    assert artifact_store.size(
        f"{MODAL_URI}/control-plane/archive.tar.gz"
    ) == len(b"archive")
    assert artifact_store.size(f"{MODAL_URI}/control-plane/nested") == len(
        b"data12"
    )
    assert artifact_store.size(f"{MODAL_URI}/control-plane") == len(
        b"archivedata12"
    )


def test_modal_volume_sdk_fallback_walks_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server downloads can walk directories without a mount."""
    artifact_store = _make_artifact_store(tmp_path)
    volume = ModalVolumeStub(
        files={
            "root/control-plane/archive.tar.gz": b"archive",
            "root/control-plane/nested/data.bin": b"data",
        }
    )
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)

    walked = list(artifact_store.walk(f"{MODAL_URI}/control-plane"))

    assert walked == [
        (
            f"{MODAL_URI}/control-plane",
            ["nested"],
            ["archive.tar.gz"],
        ),
        (f"{MODAL_URI}/control-plane/nested", [], ["data.bin"]),
    ]


def test_modal_volume_loads_artifact_visualization_via_sdk_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server visualization loading can read Modal Volume files by SDK."""
    from zenml.artifacts import utils as artifact_utils
    from zenml.enums import VisualizationType

    artifact_store = _make_artifact_store(tmp_path)
    visualization_uri = f"{MODAL_URI}/dashboard/visualization.html"
    volume = ModalVolumeStub(
        files={"root/dashboard/visualization.html": b"<h1>Modal</h1>"}
    )
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)
    monkeypatch.setattr(
        artifact_utils,
        "load_artifact_store",
        lambda artifact_store_id, zen_store: artifact_store,
    )

    artifact = SimpleNamespace(
        id=uuid4(),
        artifact_store_id=artifact_store.id,
        visualizations=[
            SimpleNamespace(
                type=VisualizationType.HTML,
                uri=visualization_uri,
            )
        ],
    )

    visualization = artifact_utils.load_artifact_visualization(artifact)

    assert visualization.type == VisualizationType.HTML
    assert visualization.value == "<h1>Modal</h1>"


def test_modal_volume_fetches_artifact_logs_via_sdk_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artifact-backed logs can read Modal Volume log files by SDK."""
    artifact_store = _make_artifact_store(tmp_path)
    logs_uri = f"{MODAL_URI}/logs/{uuid4()}.log"
    volume = ModalVolumeStub(
        files={
            logs_uri.removeprefix("modal-volume://test-volume/"): (
                b"first Modal log line\nsecond Modal log line\n"
            )
        }
    )
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)

    with artifact_store.open(logs_uri, "r") as file:
        temp_download_path = file.name
        assert next(file) == "first Modal log line\n"
    assert not Path(temp_download_path).exists()

    log_store = ArtifactLogStore.from_artifact_store(artifact_store)
    logs_model = SimpleNamespace(
        uri=logs_uri,
        artifact_store_id=artifact_store.id,
    )

    log_entries = log_store.fetch(logs_model=logs_model, limit=10)

    assert [entry.message for entry in log_entries] == [
        "first Modal log line",
        "second Modal log line",
    ]


def test_modal_volume_server_download_archive_via_sdk_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server artifact archives can read Modal Volume files by SDK."""
    from zenml.zen_server import download_utils

    artifact_store = _make_artifact_store(tmp_path)
    artifact_uri = f"{MODAL_URI}/dashboard/archive"
    volume = ModalVolumeStub(
        files={
            "root/dashboard/archive/summary.txt": b"summary",
            "root/dashboard/archive/nested/data.txt": b"nested-data",
        }
    )
    cleanup_calls: list[bool] = []
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)
    monkeypatch.setattr(
        artifact_store, "cleanup", lambda: cleanup_calls.append(True)
    )
    monkeypatch.setattr(
        download_utils,
        "load_artifact_store",
        lambda artifact_store_id, zen_store: artifact_store,
    )
    monkeypatch.setattr(download_utils, "zen_store", lambda: object())
    monkeypatch.setattr(
        download_utils,
        "server_config",
        lambda: SimpleNamespace(file_download_size_limit=10_000),
    )

    artifact = SimpleNamespace(
        id=uuid4(),
        artifact_store_id=artifact_store.id,
        uri=artifact_uri,
    )

    archive_path = download_utils.create_artifact_archive(artifact)
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            assert set(archive.getnames()) == {
                ".",
                "nested",
                "nested/data.txt",
                "summary.txt",
            }
            summary_file = archive.extractfile("summary.txt")
            nested_file = archive.extractfile("nested/data.txt")
            assert summary_file is not None
            assert nested_file is not None
            assert summary_file.read() == b"summary"
            assert nested_file.read() == b"nested-data"
    finally:
        os.remove(archive_path)
    assert cleanup_calls == [True]


def test_modal_volume_server_download_verification_cleans_up_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download verification cleans reconstructed artifact stores on failure."""
    from zenml.zen_server import download_utils

    artifact_store = _make_artifact_store(tmp_path)
    cleanup_calls: list[bool] = []
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(
        artifact_store, "_get_modal_volume", lambda: ModalVolumeStub()
    )
    monkeypatch.setattr(
        artifact_store, "cleanup", lambda: cleanup_calls.append(True)
    )
    monkeypatch.setattr(
        download_utils,
        "load_artifact_store",
        lambda artifact_store_id, zen_store: artifact_store,
    )
    monkeypatch.setattr(download_utils, "zen_store", lambda: object())

    artifact = SimpleNamespace(
        id=uuid4(),
        artifact_store_id=artifact_store.id,
        uri=f"{MODAL_URI}/missing-artifact",
    )

    with pytest.raises(KeyError, match="does not exist"):
        download_utils.verify_artifact_is_downloadable(artifact)

    assert cleanup_calls == [True]


def test_modal_volume_server_fetch_logs_reconstructs_artifact_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server log fetching can reconstruct Modal Volume artifact log stores."""
    from zenml.stack import StackComponent
    from zenml.utils import logging_utils
    from zenml.zen_server.rbac import endpoint_utils

    artifact_store = _make_artifact_store(tmp_path)
    logs_uri = f"{MODAL_URI}/logs/{uuid4()}.log"
    volume = ModalVolumeStub(
        files={
            logs_uri.removeprefix("modal-volume://test-volume/"): (
                b"first Modal log line\nsecond Modal log line\n"
            )
        }
    )
    artifact_store_model = SimpleNamespace(
        id=artifact_store.id,
        name=artifact_store.name,
        type=StackComponentType.ARTIFACT_STORE,
    )
    logs_model = SimpleNamespace(
        log_store_id=None,
        artifact_store_id=artifact_store.id,
        uri=logs_uri,
    )
    zen_store = SimpleNamespace(
        get_stack_component=lambda component_id: artifact_store_model
    )

    monkeypatch.setenv(ENV_ZENML_SERVER, "true")
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(artifact_store, "_get_modal_volume", lambda: volume)
    monkeypatch.setattr(
        endpoint_utils,
        "verify_permissions_and_get_entity",
        lambda id, get_method: get_method(id),
    )
    monkeypatch.setattr(
        StackComponent,
        "from_model",
        staticmethod(lambda model: artifact_store),
    )

    log_entries = logging_utils.fetch_logs(logs_model, zen_store, limit=10)

    assert [entry.message for entry in log_entries] == [
        "first Modal log line",
        "second Modal log line",
    ]


def test_modal_volume_sdk_lookup_uses_artifact_store_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured artifact-store credentials create an explicit Modal client."""
    import modal

    class ClientStub:
        def __init__(self) -> None:
            self.closed = False

        def is_closed(self) -> bool:
            return self.closed

        def close(self) -> None:
            self.closed = True

    artifact_store = _make_artifact_store(
        tmp_path,
        token_id=" ak-test ",
        token_secret=" as-test ",
        modal_environment="artifact-env",
    )
    volume = object()
    client = ClientStub()
    client_calls: list[tuple[str, str]] = []
    volume_calls: list[dict[str, object]] = []

    def from_credentials(token_id: str, token_secret: str) -> ClientStub:
        client_calls.append((token_id, token_secret))
        return client

    def from_name(
        name: str,
        *,
        environment_name: str | None,
        create_if_missing: bool,
        client: ClientStub,
    ) -> object:
        volume_calls.append(
            {
                "name": name,
                "environment_name": environment_name,
                "create_if_missing": create_if_missing,
                "client": client,
            }
        )
        return volume

    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.delenv(ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME, raising=False)
    monkeypatch.setenv("MODAL_ENVIRONMENT", " ambient-env ")
    monkeypatch.setattr(
        modal.Client,
        "from_credentials",
        staticmethod(from_credentials),
    )
    monkeypatch.setattr(modal.Volume, "from_name", from_name)

    assert artifact_store._get_modal_volume() is volume
    assert artifact_store._get_modal_volume() is volume
    assert client_calls == [("ak-test", "as-test")]
    assert volume_calls == [
        {
            "name": "test-volume",
            "environment_name": "artifact-env",
            "create_if_missing": False,
            "client": client,
        }
    ]

    artifact_store.cleanup()
    assert client.closed


def test_modal_volume_sdk_lookup_prefers_sandbox_environment_and_caches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK fallback reuses the sandbox Volume environment marker."""
    import modal

    artifact_store = _make_artifact_store(
        tmp_path,
        modal_environment="artifact-env",
    )
    volume = object()
    calls: list[dict[str, object]] = []

    def from_name(
        name: str,
        *,
        environment_name: str | None,
        create_if_missing: bool,
    ) -> object:
        calls.append(
            {
                "name": name,
                "environment_name": environment_name,
                "create_if_missing": create_if_missing,
            }
        )
        return volume

    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setenv("MODAL_ENVIRONMENT", " ambient-env ")
    monkeypatch.setenv(ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME, "sandbox-env")
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

    config_artifact_store = _make_artifact_store(
        tmp_path,
        modal_environment="artifact-env",
    )
    config_volume = object()
    monkeypatch.delenv(ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME, raising=False)

    def config_from_name(
        name: str,
        *,
        environment_name: str | None,
        create_if_missing: bool,
    ) -> object:
        calls.append(
            {
                "name": name,
                "environment_name": environment_name,
                "create_if_missing": create_if_missing,
            }
        )
        return config_volume

    monkeypatch.setattr(modal.Volume, "from_name", config_from_name)

    assert config_artifact_store._get_modal_volume() is config_volume
    assert calls[-1] == {
        "name": "test-volume",
        "environment_name": "artifact-env",
        "create_if_missing": False,
    }

    ambient_artifact_store = _make_artifact_store(tmp_path)
    ambient_volume = object()

    def ambient_from_name(
        name: str,
        *,
        environment_name: str | None,
        create_if_missing: bool,
    ) -> object:
        calls.append(
            {
                "name": name,
                "environment_name": environment_name,
                "create_if_missing": create_if_missing,
            }
        )
        return ambient_volume

    monkeypatch.setattr(modal.Volume, "from_name", ambient_from_name)

    assert ambient_artifact_store._get_modal_volume() is ambient_volume
    assert calls[-1] == {
        "name": "test-volume",
        "environment_name": "ambient-env",
        "create_if_missing": False,
    }


def test_modal_volume_preserves_credential_errors_from_volume_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credential validation failures are not hidden as Volume lookup errors."""
    import modal

    class FailingClientFactory:
        def get_client(self) -> object:
            raise StackComponentInterfaceError("bad Modal credentials")

    def from_name(*args: object, **kwargs: object) -> object:
        raise AssertionError("Volume lookup should not run")

    artifact_store = _make_artifact_store(tmp_path)
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    object.__setattr__(
        artifact_store, "_modal_client_factory", FailingClientFactory()
    )
    monkeypatch.setattr(modal.Volume, "from_name", from_name)

    with pytest.raises(
        StackComponentInterfaceError, match="bad Modal credentials"
    ):
        artifact_store._get_modal_volume()


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
    monkeypatch.setattr(
        tempfile, "NamedTemporaryFile", named_temporary_file_spy
    )

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


def test_modal_volume_translates_immediate_sdk_read_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Immediate Modal SDK read_file errors become FileNotFoundError."""

    class NotFoundError(Exception):
        pass

    class ImmediateMissingReadVolumeStub:
        def read_file(self, path: str):
            raise NotFoundError("missing")

    artifact_store = _make_artifact_store(tmp_path)
    monkeypatch.delenv(ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, raising=False)
    monkeypatch.setattr(
        artifact_store,
        "_get_modal_volume",
        lambda: ImmediateMissingReadVolumeStub(),
    )

    with pytest.raises(FileNotFoundError):
        artifact_store.open(f"{MODAL_URI}/missing-immediate.txt", "rb")


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
    monkeypatch.setattr(
        tempfile, "NamedTemporaryFile", named_temporary_file_spy
    )

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
