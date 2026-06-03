#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

from types import SimpleNamespace

import pytest

# Skip this entire module if the optional dependency isn't available, because
# the module under test imports `modal` at import time.
pytest.importorskip("modal")

from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.modal.flavors import (
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.integrations.modal.step_operators import (
    modal_step_operator as modal_step_operator_module,
)
from zenml.integrations.modal.step_operators.modal_step_operator import (
    ModalStepOperator,
    get_gpu_values,
)


class ResourceSettingsStub:
    """Minimal stub to simulate ZenML ResourceSettings for GPU tests.

    We only model the `gpu_count` attribute because that's the only part the
    helper uses in the small targeted Modal tests. This keeps tests lightweight
    and avoids wider dependencies.
    """

    def __init__(self, gpu_count, cpu_count=None, memory_mb=None):
        self.gpu_count = gpu_count
        self.cpu_count = cpu_count
        self.memory_mb = memory_mb

    def get_memory(self, _unit):
        return self.memory_mb


def test_gpu_arg_none_when_no_type_and_no_count() -> None:
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=None)
    assert get_gpu_values(settings, rs) is None


def test_gpu_arg_raises_when_count_without_type() -> None:
    settings = ModalStepOperatorSettings(gpu=None)
    rs = ResourceSettingsStub(gpu_count=1)
    with pytest.raises(StackComponentInterfaceError) as e:
        get_gpu_values(settings, rs)
    assert (
        "GPU resources requested (gpu_count > 0) but no GPU type was specified"
        in str(e.value)
    )


def test_gpu_arg_type_with_no_count_returns_type() -> None:
    settings = ModalStepOperatorSettings(gpu="A100")
    rs = ResourceSettingsStub(gpu_count=None)
    assert get_gpu_values(settings, rs) == "A100"


def test_gpu_arg_type_with_count_returns_type_colon_count() -> None:
    settings = ModalStepOperatorSettings(gpu="A100")

    rs_two = ResourceSettingsStub(gpu_count=2)
    assert get_gpu_values(settings, rs_two) == "A100:2"

    rs_one = ResourceSettingsStub(gpu_count=1)
    assert get_gpu_values(settings, rs_one) == "A100:1"


def test_gpu_arg_type_with_zero_count_warns_and_returns_cpu_only(
    caplog,
) -> None:
    settings = ModalStepOperatorSettings(gpu="A100")
    rs = ResourceSettingsStub(gpu_count=0)

    with caplog.at_level("WARNING"):
        result = get_gpu_values(settings, rs)

    assert result is None
    assert "running on CPU only" in caplog.text


def test_modal_submit_preserves_argv_config_and_runtime_env_boundary(
    monkeypatch,
) -> None:
    settings = ModalStepOperatorSettings(
        modal_environment="staging",
        timeout=1234,
    )
    modal_sdk_env_vars = (
        modal_step_operator_module.MODAL_TOKEN_ID_ENV_VAR,
        modal_step_operator_module.MODAL_TOKEN_SECRET_ENV_VAR,
        modal_step_operator_module.MODAL_WORKSPACE_ENV_VAR,
        modal_step_operator_module.MODAL_ENVIRONMENT_ENV_VAR,
    )
    config = ModalStepOperatorConfig(
        token_id="ak-test",
        token_secret="as-test",
        workspace="workspace-test",
    )
    resource_settings = ResourceSettingsStub(
        gpu_count=0,
        cpu_count=2,
        memory_mb=1.2,
    )
    run_metadata = {}

    class InfoStub:
        step_run_id = "step-run-id"
        pipeline_step_name = "train"
        config = SimpleNamespace(resource_settings=resource_settings)
        step_run = SimpleNamespace(run_metadata=run_metadata)

        def get_image(self, key):
            assert key == "modal_step_operator"
            return "registry.example.com/zenml:latest"

    class ContainerRegistryStub:
        credentials = None

    class StackStub:
        container_registry = ContainerRegistryStub()

    class ClientStub:
        active_stack = StackStub()

    class ImageStub:
        def env(self, environment):
            raise AssertionError(
                "ZenML runtime env must be passed to "
                "Sandbox.create(env=...), not Image.env(...)."
            )

    class ImageFactoryStub:
        @staticmethod
        def from_registry(image_name, **kwargs):
            recorded["image_name"] = image_name
            recorded["image_kwargs"] = kwargs
            image = ImageStub()
            recorded["image"] = image
            return image

    class AppFactoryStub:
        @staticmethod
        def lookup(*args, **kwargs):
            recorded["app_lookup"] = (args, kwargs)
            recorded["env_during_lookup"] = {
                key: modal_step_operator_module.os.environ.get(key)
                for key in modal_sdk_env_vars
            }
            return "app"

    class SandboxStub:
        object_id = "sandbox-id"

    class SandboxFactoryStub:
        @staticmethod
        def create(*args, **kwargs):
            recorded["sandbox_create"] = (args, kwargs)
            recorded["env_during_create"] = {
                key: modal_step_operator_module.os.environ.get(key)
                for key in modal_sdk_env_vars
            }
            return SandboxStub()

    recorded = {}
    operator = object.__new__(ModalStepOperator)
    operator.id = "component-id"
    operator._config = config
    operator.get_settings = lambda _info: settings

    monkeypatch.setattr(modal_step_operator_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Image", ImageFactoryStub
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "App", AppFactoryStub
    )
    monkeypatch.setattr(
        modal_step_operator_module.modal, "Sandbox", SandboxFactoryStub
    )
    monkeypatch.setattr(
        modal_step_operator_module,
        "publish_step_run_metadata",
        lambda *args, **kwargs: recorded.setdefault(
            "published_metadata", (args, kwargs)
        ),
    )
    monkeypatch.setenv(
        modal_step_operator_module.MODAL_ENVIRONMENT_ENV_VAR,
        "previous-local-environment",
    )

    entrypoint_command = [
        "python",
        "-m",
        "zenml.entrypoints.entrypoint",
        "--step_name",
        "train model",
    ]
    environment = {
        "ZENML_ENV": "value",
        "ZENML_STORE_API_TOKEN": "sensitive-token",
    }

    operator.submit(InfoStub(), entrypoint_command, environment)

    assert recorded["image_name"] == "registry.example.com/zenml:latest"
    assert recorded["image_kwargs"] == {}
    assert recorded["app_lookup"] == (
        ("zenml-step-run-id-train",),
        {"create_if_missing": True, "environment_name": "staging"},
    )
    expected_modal_sdk_env = {
        modal_step_operator_module.MODAL_TOKEN_ID_ENV_VAR: "ak-test",
        modal_step_operator_module.MODAL_TOKEN_SECRET_ENV_VAR: "as-test",
        modal_step_operator_module.MODAL_WORKSPACE_ENV_VAR: "workspace-test",
        modal_step_operator_module.MODAL_ENVIRONMENT_ENV_VAR: "staging",
    }
    assert recorded["env_during_lookup"] == expected_modal_sdk_env
    assert recorded["env_during_create"] == expected_modal_sdk_env
    assert recorded["sandbox_create"] == (
        tuple(entrypoint_command),
        {
            "app": "app",
            "image": recorded["image"],
            "gpu": None,
            "cpu": 2,
            "memory": 2,
            "cloud": None,
            "region": None,
            "timeout": 1234,
            "env": environment,
        },
    )
    sandbox_env = recorded["sandbox_create"][1]["env"]
    assert sandbox_env == environment
    for env_var in modal_sdk_env_vars:
        assert env_var not in sandbox_env
    assert "environment_name" not in recorded["sandbox_create"][1]
    assert (
        modal_step_operator_module.os.environ[
            modal_step_operator_module.MODAL_ENVIRONMENT_ENV_VAR
        ]
        == "previous-local-environment"
    )
    assert run_metadata["sandbox_id"] == "sandbox-id"


def test_status_and_cancel_use_configured_modal_auth_context(
    monkeypatch,
) -> None:
    config = ModalStepOperatorConfig(
        token_id="ak-test",
        token_secret="as-test",
        workspace="workspace-test",
    )
    recorded = {"from_id_calls": []}

    class SandboxStub:
        def poll(self):
            recorded["poll_env"] = {
                key: modal_step_operator_module.os.environ.get(key)
                for key in (
                    "MODAL_TOKEN_ID",
                    "MODAL_TOKEN_SECRET",
                    "MODAL_WORKSPACE",
                )
            }
            return 0

        def terminate(self):
            recorded["terminate_env"] = {
                key: modal_step_operator_module.os.environ.get(key)
                for key in (
                    "MODAL_TOKEN_ID",
                    "MODAL_TOKEN_SECRET",
                    "MODAL_WORKSPACE",
                )
            }

    class SandboxFactoryStub:
        @staticmethod
        def from_id(sandbox_id):
            recorded["from_id_calls"].append(sandbox_id)
            return SandboxStub()

    operator = object.__new__(ModalStepOperator)
    operator._config = config
    step_run = SimpleNamespace(run_metadata={"sandbox_id": "sandbox-id"})

    monkeypatch.setattr(
        modal_step_operator_module.modal, "Sandbox", SandboxFactoryStub
    )

    assert operator.get_status(step_run).value == "completed"
    operator.cancel(step_run)

    expected_env = {
        "MODAL_TOKEN_ID": "ak-test",
        "MODAL_TOKEN_SECRET": "as-test",
        "MODAL_WORKSPACE": "workspace-test",
    }
    assert recorded["from_id_calls"] == ["sandbox-id", "sandbox-id"]
    assert recorded["poll_env"] == expected_env
    assert recorded["terminate_env"] == expected_env


def test_gpu_arg_invalid_negative_count_raises() -> None:
    settings = ModalStepOperatorSettings(gpu="T4")
    rs = ResourceSettingsStub(gpu_count=-1)
    with pytest.raises(StackComponentInterfaceError) as e:
        get_gpu_values(settings, rs)
    assert "Invalid GPU count" in str(e.value)


def test_gpu_arg_non_integer_count_raises() -> None:
    settings = ModalStepOperatorSettings(gpu="T4")
    rs = ResourceSettingsStub(gpu_count="two")
    with pytest.raises(StackComponentInterfaceError) as e:
        get_gpu_values(settings, rs)
    assert "Invalid GPU count" in str(e.value)


def test_gpu_arg_whitespace_type_treated_as_none_behavior() -> None:
    settings = ModalStepOperatorSettings(gpu="   ")

    # With positive GPU count this should raise since type is treated as None.
    rs_positive = ResourceSettingsStub(gpu_count=2)
    with pytest.raises(StackComponentInterfaceError):
        get_gpu_values(settings, rs_positive)

    # With zero or None count, this should be CPU-only (None).
    rs_zero = ResourceSettingsStub(gpu_count=0)
    assert get_gpu_values(settings, rs_zero) is None

    rs_none = ResourceSettingsStub(gpu_count=None)
    assert get_gpu_values(settings, rs_none) is None
