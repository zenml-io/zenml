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

# ruff: noqa: D100,D102,D103

from types import SimpleNamespace

import pytest

pytest.importorskip("modal")

from zenml.config.resource_settings import ResourceSettings  # noqa: E402
from zenml.exceptions import StackComponentInterfaceError  # noqa: E402
from zenml.integrations.modal import (  # noqa: E402
    MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
    sandbox_utils,
)
from zenml.integrations.modal.flavors import (  # noqa: E402
    ModalStepOperatorSettings,
    ModalVolumeArtifactStoreConfig,
)
from zenml.integrations.modal.flavors.modal_volume_artifact_store_flavor import (  # noqa: E402
    ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX,
)


def _stack_with_artifact_store(config: object, flavor: str):
    return SimpleNamespace(
        artifact_store=SimpleNamespace(flavor=flavor, config=config)
    )


def test_modal_volume_mount_resolves_volume_and_builds_fast_path_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mount helper resolves the configured Volume and env vars."""
    recorded = []
    modal_client = SimpleNamespace(name="client")
    volume = SimpleNamespace(name="volume")

    class VolumeFactoryStub:
        @staticmethod
        def from_name(*args, **kwargs):
            recorded.append((args, kwargs))
            return volume

    monkeypatch.setattr(sandbox_utils.modal, "Volume", VolumeFactoryStub)

    mount = sandbox_utils.get_modal_volume_sandbox_mount(
        _stack_with_artifact_store(
            ModalVolumeArtifactStoreConfig(
                path="modal-volume://training-artifacts/runs",
                mount_path="/mnt/zenml",
                create_if_missing=True,
            ),
            MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
        ),
        modal_environment="prod",
        modal_client=modal_client,
    )

    assert mount is not None
    assert recorded == [
        (
            ("training-artifacts",),
            {
                "environment_name": "prod",
                "create_if_missing": True,
                "client": modal_client,
            },
        )
    ]
    assert mount.volumes == {"/mnt/zenml": volume}
    assert mount.environment == {
        ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH: "1",
        ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH: "/mnt/zenml",
        ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME: "training-artifacts",
        ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX: "runs",
    }


def test_modal_volume_mount_factory_reuses_matching_mounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated matching mount requests reuse the resolved Modal Volume."""
    recorded = []

    class VolumeFactoryStub:
        @staticmethod
        def from_name(*args, **kwargs):
            volume = SimpleNamespace(name=f"volume-{len(recorded) + 1}")
            recorded.append((args, kwargs, volume))
            return volume

    monkeypatch.setattr(sandbox_utils.modal, "Volume", VolumeFactoryStub)
    stack = _stack_with_artifact_store(
        ModalVolumeArtifactStoreConfig(
            path="modal-volume://training-artifacts/runs",
            mount_path="/mnt/zenml",
            create_if_missing=True,
        ),
        MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
    )
    factory = sandbox_utils.ModalVolumeMountFactory()

    first_mount = factory.get_mount(
        stack, modal_environment="prod", modal_client=None
    )
    second_mount = factory.get_mount(
        stack, modal_environment="prod", modal_client=None
    )

    assert first_mount is second_mount
    assert len(recorded) == 1


def test_modal_volume_mount_factory_uses_modal_environment_in_cache_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Different Modal environments resolve separate Volume handles."""
    recorded = []

    class VolumeFactoryStub:
        @staticmethod
        def from_name(*args, **kwargs):
            volume = SimpleNamespace(name=f"volume-{len(recorded) + 1}")
            recorded.append((args, kwargs, volume))
            return volume

    monkeypatch.setattr(sandbox_utils.modal, "Volume", VolumeFactoryStub)
    stack = _stack_with_artifact_store(
        ModalVolumeArtifactStoreConfig(
            path="modal-volume://training-artifacts/runs"
        ),
        MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
    )
    factory = sandbox_utils.ModalVolumeMountFactory()

    prod_mount = factory.get_mount(
        stack, modal_environment="prod", modal_client=None
    )
    dev_mount = factory.get_mount(
        stack, modal_environment="dev", modal_client=None
    )

    assert prod_mount is not dev_mount
    assert len(recorded) == 2


def test_modal_volume_mount_wraps_missing_volume_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing Volume errors include the Volume name and creation setting."""

    class VolumeFactoryStub:
        @staticmethod
        def from_name(*args, **kwargs):
            raise RuntimeError("not found")

    monkeypatch.setattr(sandbox_utils.modal, "Volume", VolumeFactoryStub)

    with pytest.raises(StackComponentInterfaceError) as exc_info:
        sandbox_utils.get_modal_volume_sandbox_mount(
            _stack_with_artifact_store(
                ModalVolumeArtifactStoreConfig(
                    path="modal-volume://missing-volume/runs",
                    create_if_missing=False,
                ),
                MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
            ),
            modal_environment="prod",
            modal_client=None,
        )

    error_message = str(exc_info.value)
    assert "missing-volume" in error_message
    assert "prod" in error_message
    assert "create_if_missing value is False" in error_message
    assert "RuntimeError" in error_message


def test_non_modal_volume_artifact_store_has_no_modal_volume_mount() -> None:
    """Non-Modal artifact stores keep the old sandbox behavior."""
    mount = sandbox_utils.get_modal_volume_sandbox_mount(
        _stack_with_artifact_store(SimpleNamespace(), "s3"),
        modal_environment="prod",
        modal_client=None,
    )

    assert mount is None


def test_modal_volume_environment_consistency_rejects_step_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modal Volume runs cannot mix Modal environments per step."""
    stack = _stack_with_artifact_store(
        ModalVolumeArtifactStoreConfig(
            path="modal-volume://training-artifacts/runs"
        ),
        MODAL_VOLUME_ARTIFACT_STORE_FLAVOR,
    )
    monkeypatch.setenv(
        sandbox_utils.ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME,
        "prod",
    )

    sandbox_utils.validate_modal_volume_environment_consistency(
        stack,
        modal_environment="prod",
    )
    with pytest.raises(StackComponentInterfaceError, match="same Modal"):
        sandbox_utils.validate_modal_volume_environment_consistency(
            stack,
            modal_environment="dev",
        )


def test_sandbox_create_kwargs_include_volumes_only_when_requested() -> None:
    """Volume mappings are passed through without changing default kwargs."""
    settings = ModalStepOperatorSettings(timeout=123)
    resource_settings = ResourceSettings(cpu_count=2, memory="2GB")
    volume = SimpleNamespace(name="volume")

    without_volumes = sandbox_utils.build_sandbox_create_kwargs(
        app="app",
        image="image",
        settings=settings,
        resource_settings=resource_settings,
        environment={"ZENML_ENV": "value"},
        modal_client=None,
    )
    assert "volumes" not in without_volumes

    with_volumes = sandbox_utils.build_sandbox_create_kwargs(
        app="app",
        image="image",
        settings=settings,
        resource_settings=resource_settings,
        environment={"ZENML_ENV": "value"},
        modal_client=None,
        volumes={"/mnt/zenml": volume},
    )
    assert with_volumes["volumes"] == {"/mnt/zenml": volume}


def test_create_modal_sandbox_passes_volumes_to_modal_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared sandbox helper forwards Volume mounts to Sandbox.create."""
    recorded = {}
    settings = ModalStepOperatorSettings(timeout=123)
    resource_settings = ResourceSettings(cpu_count=2, memory="2GB")
    volume = SimpleNamespace(name="volume")
    sandbox = SimpleNamespace(object_id="sandbox-id")

    class SandboxFactoryStub:
        @staticmethod
        def create(*args, **kwargs):
            recorded["create"] = (args, kwargs)
            return sandbox

    monkeypatch.setattr(sandbox_utils.modal, "Sandbox", SandboxFactoryStub)

    result = sandbox_utils.create_modal_sandbox(
        ["python", "-m", "entrypoint"],
        app="app",
        image="image",
        settings=settings,
        resource_settings=resource_settings,
        environment={"ZENML_ENV": "value"},
        modal_client=None,
        volumes={"/mnt/zenml": volume},
    )

    assert result is sandbox
    assert recorded["create"] == (
        ("python", "-m", "entrypoint"),
        {
            "app": "app",
            "image": "image",
            "gpu": None,
            "cpu": 2.0,
            "memory": 2000,
            "cloud": None,
            "region": None,
            "timeout": 123,
            "env": {"ZENML_ENV": "value"},
            "client": None,
            "volumes": {"/mnt/zenml": volume},
        },
    )
