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
"""Tests for sandbox config merge precedence."""

import sys
from contextlib import nullcontext
from datetime import datetime
from types import ModuleType, SimpleNamespace
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.integrations.modal.flavors import (
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox
from zenml.sandboxes import NetworkPolicy


class _FakeModalRunContext:
    """Minimal context manager returned by fake Modal app runs."""

    def __enter__(self) -> "_FakeModalRunContext":
        return self

    def __exit__(self, *args) -> None:
        return None


class _FakeModalApp:
    """Minimal fake Modal app implementation."""

    def __init__(self, name: str, recorder):
        recorder["app_name"] = name

    def run(self) -> _FakeModalRunContext:
        """Returns a fake app run context."""
        return _FakeModalRunContext()


class _FakeModalSandbox:
    """Minimal fake Modal sandbox object."""

    object_id = "fake-object-id"


def _build_fake_modal_module(recorder) -> ModuleType:
    """Builds a tiny fake `modal` module for unit tests."""
    fake_modal = ModuleType("modal")

    class _App(_FakeModalApp):
        def __init__(self, name: str):
            super().__init__(name, recorder)

    def _sandbox_create(*args, **kwargs):  # type: ignore[no-untyped-def]
        recorder["create_args"] = args
        recorder["create_kwargs"] = kwargs
        return _FakeModalSandbox()

    fake_modal.App = _App
    fake_modal.Sandbox = SimpleNamespace(create=_sandbox_create)
    fake_modal.enable_output = nullcontext
    return fake_modal


def _create_modal_sandbox(config: ModalSandboxConfig) -> ModalSandbox:
    """Creates a Modal sandbox instance for unit tests."""
    return ModalSandbox(
        name="modal-sandbox",
        id=uuid4(),
        config=config,
        flavor="modal",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )


def test_modal_session_merge_precedence_with_step_settings_and_config(
    monkeypatch,
) -> None:
    """Tests merge precedence: session args > step settings > config defaults."""
    recorder = {}
    fake_modal = _build_fake_modal_module(recorder)
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    config = ModalSandboxConfig(
        app_name="unit-test-app",
        default_image="config-img",
        default_cpu=1.0,
        default_memory_mb=512,
        default_timeout_seconds=111,
    )
    sandbox = _create_modal_sandbox(config)

    step_settings = ModalSandboxSettings(
        image="step-img",
        cpu=2.0,
        memory_mb=1024,
        timeout_seconds=222,
        env={"A": "step", "B": "step"},
        secret_refs=["my-secret"],
        tags={"t1": "step", "t2": "step"},
        block_network=True,
        cidr_allowlist=["10.0.0.0/8"],
    )
    monkeypatch.setattr(
        sandbox, "_resolve_step_settings", lambda: step_settings
    )

    captured_secret_refs = {}

    def _fake_secret_env(secret_refs):  # type: ignore[no-untyped-def]
        captured_secret_refs["refs"] = list(secret_refs)
        return {"A": "secret", "S": "secret-only"}

    monkeypatch.setattr(sandbox, "_resolve_secret_env", _fake_secret_env)

    monkeypatch.setattr(
        "zenml.integrations.modal.sandboxes.modal_sandbox.build_modal_image",
        lambda base_image: f"image::{base_image}",
    )

    with sandbox.session(
        image="arg-img",
        cpu=3.0,
        memory_mb=2048,
        gpu="A10G",
        timeout_seconds=333,
        env={"A": "arg"},
        tags={"t2": "arg"},
        network_policy=NetworkPolicy(block_network=False, cidr_allowlist=None),
    ) as session:
        assert recorder["app_name"] == "unit-test-app"
        assert recorder["create_args"][0] == "sleep"

        create_kwargs = recorder["create_kwargs"]
        assert create_kwargs["image"] == "image::arg-img"
        assert create_kwargs["timeout"] == 333
        assert create_kwargs["cpu"] == 3.0
        assert create_kwargs["memory"] == 2048
        assert create_kwargs["block_network"] is False
        assert "cidr_allowlist" not in create_kwargs

        assert captured_secret_refs["refs"] == ["my-secret"]

        assert session._default_env == {
            "A": "arg",
            "B": "step",
            "S": "secret-only",
        }
        assert session._metadata.tags == {"t1": "step", "t2": "arg"}
        assert session._metadata.network_policy is not None
        assert session._metadata.network_policy.block_network is False
        assert session._metadata.extra["image"] == "arg-img"
        assert session._metadata.extra["cpu"] == 3.0
        assert session._metadata.extra["memory_mb"] == 2048
